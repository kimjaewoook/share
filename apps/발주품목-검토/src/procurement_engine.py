import pandas as pd
import math
from datetime import datetime, timedelta


def clean_number(val):
    if pd.isna(val) or val is None or str(val).strip() == "":
        return 0.0
    try:
        return float(str(val).replace(",", "").strip())
    except:
        return 0.0


def _compute_request_averages(full_req_df, today):
    """자재요청서 전체 이력에서 자재코드별 30/60/90일 일평균 산출"""
    result = {}
    if full_req_df.empty or '요청일자' not in full_req_df.columns:
        return result
    df = full_req_df.copy()
    df['_dt'] = pd.to_datetime(df['요청일자'], errors='coerce')
    df['_qty'] = df['수량(낱개)'].apply(clean_number)
    df['_code'] = df['자재코드'].astype(str).str.strip()
    valid = df.dropna(subset=['_dt'])
    for days in [30, 60, 90]:
        cutoff = pd.Timestamp(today - timedelta(days=days))
        period = valid[valid['_dt'] >= cutoff]
        grouped = period.groupby('_code')['_qty'].sum()
        for code, total in grouped.items():
            result.setdefault(code, {})
            result[code][f'avg_{days}d'] = total / days
    return result


def _compute_seasonal_averages(forecast_df):
    """재고소진예상시점에서 자재코드별 성수기/비수기 일 소요량 평균 산출"""
    result = {}
    if forecast_df.empty:
        return result
    valid_months = ['2025.05','2025.06','2025.07','2025.08','2025.09',
                    '2025.10','2025.11','2025.12','2026.01','2026.02','2026.03']
    peak_cols, off_cols = [], []
    for m in valid_months:
        month_num = int(m.split('.')[1])
        daily_col = f"{m}_1"
        if daily_col not in forecast_df.columns:
            continue
        if month_num in [3, 4, 5, 9, 10, 11]:
            peak_cols.append(daily_col)
        else:
            off_cols.append(daily_col)
    mat_col = '자재코드(물류)'
    if mat_col not in forecast_df.columns:
        return result
    for _, row in forecast_df.iterrows():
        code = str(row.get(mat_col, '')).strip()
        if not code or code == 'nan':
            continue
        peak_vals = [clean_number(row.get(c, 0)) for c in peak_cols if clean_number(row.get(c, 0)) > 0]
        off_vals = [clean_number(row.get(c, 0)) for c in off_cols if clean_number(row.get(c, 0)) > 0]
        result[code] = {
            'peak': sum(peak_vals) / len(peak_vals) if peak_vals else 0.0,
            'off': sum(off_vals) / len(off_vals) if off_vals else 0.0,
        }
    return result


def _compute_pending_po(po_df):
    """PO List에서 미입고 건의 자재코드, 팩토리별 수량 합산"""
    result = {}
    if po_df.empty or '실제입고일' not in po_df.columns:
        return result
    po = po_df.copy()
    po['실제입고일'] = po['실제입고일'].astype(str).str.strip().replace(['nan','None',''], '')
    pending = po[(po['실제입고일'] == '') | (po['실제입고일'].str.startswith('('))]
    mat_col = '자재코드(물류)'
    if mat_col not in pending.columns:
        return result

    def _norm_fac(f):
        f = str(f).strip()
        if "성수" in f: return "성수팩토리"
        if "군포" in f or "자재창고" in f: return "군포팩토리"
        if "부산" in f: return "부산팩토리"
        return f

    pending = pending.copy()
    pending['_qty'] = pending['수량'].apply(clean_number)
    
    if '팩토리' in pending.columns:
        pending['_fac'] = pending['팩토리'].apply(_norm_fac)
        for (code, fac), total in pending.groupby([mat_col, '_fac'])['_qty'].sum().items():
            result[(str(code).strip(), fac)] = total
    else:
        for code, total in pending.groupby(mat_col)['_qty'].sum().items():
            result[(str(code).strip(), "ALL")] = total
    return result


def _calc_expected_date(now, lt_days):
    """입고 요청일 산출: 오늘 + L/T일, 주말이면 다음 월요일로 이월"""
    expected_dt = now + timedelta(days=lt_days)
    if expected_dt.weekday() >= 5:
        rollover = 7 - expected_dt.weekday()
        expected_dt += timedelta(days=rollover)
    return expected_dt.strftime("%Y-%m-%d"), expected_dt


def _calc_next_weekday(now, target_weekday):
    """다음 특정 요일 산출 (0=월, 1=화, 2=수, 3=목, 4=금)"""
    d = (target_weekday - now.weekday()) % 7
    if d == 0:
        d = 7  # 오늘이 해당 요일이면 다음 주
    dt = now + timedelta(days=d)
    return dt.strftime("%Y-%m-%d"), dt


def _round_to_unit(po_qty, box_qty, plt_total, is_everone=False):
    """H2: 박스 단위 올림 → 파렛트의 50% 이상이면 파렛트 단위로 올림"""
    if po_qty <= 0:
        return 0

    if is_everone and plt_total > 0:
        po_qty = math.ceil(po_qty / plt_total) * plt_total
        if (po_qty / plt_total) % 2 != 0:
            po_qty += plt_total
        return po_qty

    # 1차: 박스 단위 올림
    if box_qty > 0:
        po_qty = math.ceil(po_qty / box_qty) * box_qty
    else:
        po_qty = math.ceil(po_qty)
    # 2차: 파렛트 50% 이상이면 파렛트 올림
    if plt_total > 0:
        remainder = po_qty % plt_total
        if remainder >= plt_total * 0.5:
            po_qty = math.ceil(po_qty / plt_total) * plt_total
    return po_qty


def generate_procurement_plan(data_dict):
    trigger_a_df = data_dict.get("trigger_a_df", pd.DataFrame())
    trigger_b_df = data_dict.get("trigger_b_df", pd.DataFrame())
    inv_df = data_dict.get("inv_df", pd.DataFrame())
    price_df = data_dict.get("price_df", pd.DataFrame())
    full_req_df = data_dict.get("full_req_df", pd.DataFrame())
    forecast_df = data_dict.get("forecast_df", pd.DataFrame())
    po_df = data_dict.get("po_df", pd.DataFrame())

    now = datetime.now()
    today = now.date()

    # Pre-compute
    req_avgs = _compute_request_averages(full_req_df, today)
    seasonal_avgs = _compute_seasonal_averages(forecast_df)
    pending_po = _compute_pending_po(po_df)

    grouped_plans = []
    PLAN_TEMPLATE = {
        "trigger_type":"","factory":"","department":"","requestor":"",
        "date_requested":"","mat_code":"","mat_code_buy":"","mat_name":"","qty":0.0,
        "vendor_po_qty":0.0,"box_count":0.0,"box_qty":"-","pallet_count":0.0,"plt_total_qty":"-",
        "expected_date":"","vendor":"","action":"",
        "remaining_stock":0.0,
        "avg_30d":0.0,"avg_60d":0.0,"avg_90d":0.0,"avg_8w":0.0,
        "avg_peak":0.0,"avg_off":0.0,"adopted_usage":0.0,
        "cover_days":0.0,"cover_weeks":0.0,
    }

    # Pre-calculate lookups for routing
    monitored_codes = set()
    if not trigger_b_df.empty:
        for _, row in trigger_b_df.iterrows():
            mc = str(row.get("자재코드","")).strip()
            if mc: monitored_codes.add(mc)
            
    direct_codes = set()
    if not price_df.empty:
        for _, row in price_df.iterrows():
            if "O" in str(row.get("직납여부","")).upper():
                mc = str(row.get("자재코드(물류)","")).strip()
                if mc: direct_codes.add(mc)

    # --- 1. Trigger A (현장요청) ---
    if not trigger_a_df.empty:
        for _, row in trigger_a_df.iterrows():
            mc = str(row.get("자재코드","")).strip()
            if not mc: continue
            
            is_monitored = mc in monitored_codes
            is_direct = mc in direct_codes
            
            fac = str(row.get("팩토리","")).strip()
            dept = str(row.get("팀명","")).strip()
            req = str(row.get("신청인","")).strip()
            
            # Hub & Spoke: 재고관리 품목은 자재창고(군포)로 통합 (직납 예외)
            if is_monitored and not is_direct:
                fac = "자재창고(군포)"
                dept = "통합요청"
                req = "-"
                
            is_sb = "성수" in fac or "부산" in fac
                
            qty = clean_number(row.get("수량(낱개)", 0))
            found = False
            for p in grouped_plans:
                if p["mat_code"]==mc and p["factory"]==fac and p["trigger_type"]=="현장요청":
                    if is_sb or fac == "자재창고(군포)" or p["department"]==dept:
                        p["qty"] += qty
                        if is_sb:
                            if "sb_details" not in p:
                                p["sb_details"] = {}
                            p["sb_details"][(dept, req)] = p["sb_details"].get((dept, req), 0) + qty
                        found = True
                        break
            if not found:
                plan = dict(PLAN_TEMPLATE)
                plan.update({
                    "trigger_type":"현장요청","factory":fac,
                    "department":dept,
                    "requestor":req,
                    "date_requested":str(row.get("요청일자","")).strip(),
                    "mat_code":mc,"mat_name":str(row.get("자재명","")).strip(),
                    "qty":qty,
                })
                if is_sb:
                    plan["sb_details"] = {(dept, req): qty}
                grouped_plans.append(plan)

    # 성수/부산 부서/요청자 최대 수량 대표값 산출 (동점자 전부 나열)
    for p in grouped_plans:
        if "sb_details" in p and p["sb_details"]:
            max_qty = max(p["sb_details"].values())
            best_pairs = [k for k, v in p["sb_details"].items() if v == max_qty]
            depts = []
            reqs = []
            for d, r in best_pairs:
                if d and d not in depts: depts.append(d)
                if r and r not in reqs: reqs.append(r)
            p["department"] = ", ".join(depts) if depts else "-"
            p["requestor"] = ", ".join(reqs) if reqs else "-"

    # --- 2. Trigger B (자동보충) ---
    ta_codes = set(p["mat_code"] for p in grouped_plans if p["trigger_type"]=="현장요청")
    if not trigger_b_df.empty:
        for _, row in trigger_b_df.iterrows():
            mc = str(row.get("자재코드","")).strip()
            if not mc or mc in ta_codes: continue
            
            is_direct = mc in direct_codes
            fac = "군포팩토리" if is_direct else "자재창고(군포)"
            
            plan = dict(PLAN_TEMPLATE)
            plan.update({
                "trigger_type":"자동보충","factory":fac,
                "department":"-","requestor":"시스템(AI)",
                "date_requested":now.strftime("%Y-%m-%d"),
                "mat_code":mc,"mat_name":str(row.get("자재명","")).strip(),
            })
            grouped_plans.append(plan)

    # --- 3. Calculation loop ---
    for plan in grouped_plans:
        mc = plan["mat_code"]
        factory = plan["factory"]

        # Lookup: 물류코드로 검색 → 유효여부 O 필터
        pr = price_df[price_df["자재코드(물류)"]==mc]
        if "유효여부" in price_df.columns:
            pr_valid = pr[pr["유효여부"].astype(str).str.strip().str.upper()=="O"]
            if not pr_valid.empty:
                pr = pr_valid

        # 자재코드(구매) 결정
        mat_code_buy = ""
        ir = inv_df[inv_df["자재코드(물류)"]==mc]

        is_direct=False; vendor_name="알 수 없음"; lt_days=0; moq=0; box_qty=0; plt_boxes=0

        if not pr.empty:
            if len(pr) > 1:
                # 복수 유효 행: 진주크린텍/경동라인 팩토리 라우팅
                vendors = pr["공급업체명(약식)"].astype(str).str.strip().unique().tolist()
                vendor_set = set(v for v in vendors)
                if {"진주크린텍","경동라인"} & vendor_set:
                    if "부산" in factory:
                        pr_pick = pr[pr["공급업체명(약식)"].astype(str).str.strip()=="경동라인"]
                    else:
                        pr_pick = pr[pr["공급업체명(약식)"].astype(str).str.strip()=="진주크린텍"]
                    if not pr_pick.empty:
                        pr = pr_pick
                    # else: keep all, will use first
                else:
                    # 기타 복수 유효: 공급업체명 A / B 표기
                    vendor_name = " / ".join(vendors)

            pi = pr.index[0]
            is_direct = str(pr.at[pi,"직납여부"]).strip().upper()=="O"
            if vendor_name == "알 수 없음" or len(pr) == 1:
                vendor_name = str(pr.at[pi,"공급업체명(약식)"]).strip()
            lt_days = clean_number(pr.at[pi,"L/T"])
            moq = clean_number(pr.at[pi,"MOQ"])
            box_qty = clean_number(pr.at[pi,"박스입수량"])
            plt_boxes = clean_number(pr.at[pi,"PLT당 적재 박스수"])
            mat_code_buy = str(pr.at[pi,"자재코드(구매)"]).strip()
            if box_qty > 0:
                plan["box_qty"] = box_qty
            if "PLT당 총 수량" in pr.columns:
                p_val = pr.at[pi, "PLT당 총 수량"]
                if pd.isna(p_val) or str(p_val).strip() == "":
                    plan["plt_total_qty"] = "-"
                else:
                    plan["plt_total_qty"] = clean_number(p_val)

        plan["vendor"] = vendor_name
        plan["mat_code_buy"] = mat_code_buy
        plt_total = box_qty * plt_boxes if box_qty>0 and plt_boxes>0 else 0

        # --- 입고요청일 산출: 업체별 고정 요일 우선 → L/T 기반 ---
        if "메이네티" in vendor_name:
            if mc.startswith("3CVR"):
                # 3CVR: 팩토리 무관 자재창고(군포) 입고, 매주 수요일
                plan["factory"] = "자재창고(군포)"
                exp_str, exp_dt = _calc_next_weekday(now, 2)
            else:
                if "군포" in plan["factory"]:
                    plan["factory"] = "자재창고(군포)"
                if "성수" in plan["factory"]:
                    # 성수: 매주 화요일 직납
                    is_direct = True
                    exp_str, exp_dt = _calc_next_weekday(now, 1)
                else:
                    # 부산 등: 직납이나 요일 미지정, L/T 기반
                    is_direct = True
                    exp_str, exp_dt = _calc_expected_date(now, lt_days)
        elif "진주크린텍" in vendor_name:
            # 진주크린텍: 무조건 매주 목요일
            exp_str, exp_dt = _calc_next_weekday(now, 3)
        else:
            # 기본: L/T + 주말→월요일 이월
            exp_str, exp_dt = _calc_expected_date(now, lt_days)
        plan["expected_date"] = exp_str

        # Season
        dm = exp_dt.month
        is_peak = dm in [3,4,5,9,10,11]

        # H5: 5 averages
        ra = req_avgs.get(mc, {})
        a30 = ra.get('avg_30d', 0.0)
        a60 = ra.get('avg_60d', 0.0)
        a90 = ra.get('avg_90d', 0.0)
        a8w = 0.0; remaining = 0.0
        if not ir.empty:
            a8w = clean_number(ir.at[ir.index[0],"1일 평균\n(최근 8주)"])
            for ii in ir.index:
                rem_val = clean_number(ir.at[ii,"잔여재고 수량"]) if "잔여재고 수량" in inv_df.columns else clean_number(ir.at[ii,"가용재고(낱개)"])
                remaining += rem_val
        sa_data = seasonal_avgs.get(mc, {})
        a_peak = sa_data.get('peak', 0.0)
        a_off = sa_data.get('off', 0.0)

        plan["remaining_stock"] = round(remaining, 2)
        plan["avg_30d"]=round(a30,2); plan["avg_60d"]=round(a60,2)
        plan["avg_90d"]=round(a90,2); plan["avg_8w"]=round(a8w,2)
        plan["avg_peak"]=round(a_peak,2); plan["avg_off"]=round(a_off,2)
        adopted = max(a30, a60, a90, a8w, a_peak, a_off)
        plan["adopted_usage"] = round(adopted, 2)

        # H4: Cross-validation ±10%
        anomaly = ""
        if a8w > 0 and (a_peak > 0 or a_off > 0):
            a_season_ref = a_peak if is_peak else a_off
            if a_season_ref > 0:
                mx = max(a8w, a_season_ref)
                pct = abs(a8w - a_season_ref) / mx
                if pct > 0.10:
                    label = "성수기" if is_peak else "비수기"
                    anomaly = f"⚠️교차검증 이상: 8주({a8w:.1f}) vs {label}({a_season_ref:.1f}) 편차 {pct:.0%}>10%"

        req_qty = plan["qty"]
        actions = []

        # H3: PO List 미입고 대조 (직납/비직납 공통)
        def _norm_fac_for_plan(f):
            f = str(f).strip()
            if "성수" in f: return "성수팩토리"
            if "군포" in f or "자재창고" in f: return "군포팩토리"
            if "부산" in f: return "부산팩토리"
            return f
            
        norm_fac = _norm_fac_for_plan(plan["factory"])
        pend = pending_po.get((mc, norm_fac), 0)
        if pend == 0:
            pend = pending_po.get((mc, "ALL"), 0)
            
        if pend > 0:
            actions.append(f"ℹ️ 기존 미입고 발주 {pend:,.0f}개 존재 → 차감 적용")

        if is_direct:
            adjusted_qty = req_qty - pend
            if adjusted_qty <= 0:
                plan["vendor_po_qty"] = 0
                actions.append("[직납] 기존 발주로 커버 가능 (신규 발주 불필요)")
            else:
                plan["vendor_po_qty"] = adjusted_qty
                actions.append(f"[직납] {adjusted_qty:,.0f}개 발주 요망")
        else:
            lt_demand = adopted * lt_days
            safety = lt_demand * 0.2
            
            effective_remaining = remaining
            if "에버원" in vendor_name and mc in ["3HGR0003", "3HGR0004"]:
                effective_remaining -= (13 * plt_total)
                
            po_qty = (req_qty + lt_demand + safety) - effective_remaining - pend

            if po_qty <= 0:
                plan["vendor_po_qty"] = 0
                if plan["trigger_type"]=="Trigger A":
                    actions.append("재고 충분 (창고 불출 가능)")
                else:
                    actions.append("재고 충분 (안전재고 유지 중)")
            else:
                if moq > 0 and po_qty < moq:
                    po_qty = moq
                # H2: 단위 올림
                po_qty = _round_to_unit(po_qty, box_qty, plt_total, is_everone=("에버원" in vendor_name))
                plan["vendor_po_qty"] = po_qty
                prefix = "[선제보충]" if plan["trigger_type"]=="Trigger B" else ""
                actions.append(f"{prefix} 업체에 {po_qty:,.0f}개 발주 요망".strip())

        if anomaly: actions.append(anomaly)
        plan["action"] = "\n".join([f"- {a}" for a in actions])

        final_po_qty = plan["vendor_po_qty"]
        plan["box_count"] = round(final_po_qty / box_qty, 1) if box_qty > 0 else 0.0
        plan["pallet_count"] = round(final_po_qty / plt_total, 1) if plt_total > 0 else 0.0

        # 가용재고 기준 소진 일수/주수
        stock_qty = plan["remaining_stock"]
        if adopted > 0 and stock_qty >= 0:
            days = stock_qty / adopted
            plan["cover_days"] = round(days, 1)
            plan["cover_weeks"] = round(days / 7, 1)

        if plan["factory"] == "자재창고(군포)":
            plan["department"] = "P&C실"
            plan["requestor"] = "김재욱"

    df = pd.DataFrame(grouped_plans)
    return df

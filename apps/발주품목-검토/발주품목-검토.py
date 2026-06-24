import sys
import os
import warnings

# 앱 루트를 PATH에 추가 (명령어 실행 위치 무관)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.data_mapper import process_procurement_data
from src.procurement_engine import generate_procurement_plan
from src.report_generator import generate_excel_report

def main():
    warnings.filterwarnings("ignore")
    print("🚀 발주 품목 검토 파이프라인 시작...")
    
    try:
        # Step 1. 구글 시트 데이터 로드
        print("\n[1/3] 구글 시트 데이터 취합 및 정제 중...")
        data_dict = process_procurement_data()
        
        ta = len(data_dict["trigger_a_df"])
        tb = len(data_dict["trigger_b_df"])
        fr = len(data_dict["full_req_df"])
        po = len(data_dict["po_df"])
        fc = len(data_dict["forecast_df"])
        
        if ta == 0 and tb == 0:
            print("⚠️ 발주 검토 대상이 없습니다. 파이프라인을 종료합니다.")
            return
            
        # [NEW] 상세 출력 로직 (1번+2번 결합 뷰)
        def print_detailed_step1_tree(data_dict):
            import pandas as pd
            ta_df = data_dict.get("trigger_a_df", pd.DataFrame())
            tb_df = data_dict.get("trigger_b_df", pd.DataFrame())
            price_df = data_dict.get("price_df", pd.DataFrame())
            
            # 단가테이블에서 공급업체 매핑 (자재코드 -> 업체명)
            vendor_map = {}
            if not price_df.empty and '자재코드(물류)' in price_df.columns and '공급업체명(약식)' in price_df.columns:
                for _, r in price_df.iterrows():
                    mc = str(r.get("자재코드(물류)", "")).strip()
                    v = str(r.get("공급업체명(약식)", "")).strip()
                    if mc and v and mc not in vendor_map:
                        vendor_map[mc] = v
                        
            print(f"\n✅ 데이터 로드 완료 (검토 대상 총 {len(ta_df) + len(tb_df)}건)")
            
            # 1. 현장요청 트리
            print(f"\n📂 [현장요청] 총 {len(ta_df)}건")
            if not ta_df.empty:
                ta_grouped = {}
                for _, row in ta_df.iterrows():
                    fac = str(row.get("팩토리", "미상")).strip()
                    mc = str(row.get("자재코드", "")).strip()
                    mat_name = str(row.get("자재명", "")).strip()
                    vendor = vendor_map.get(mc, "미상업체")
                    
                    if fac not in ta_grouped:
                        ta_grouped[fac] = {}
                    if vendor not in ta_grouped[fac]:
                        ta_grouped[fac][vendor] = {"count": 0, "sample": mat_name}
                    ta_grouped[fac][vendor]["count"] += 1
                    
                fac_items = list(ta_grouped.items())
                for i, (fac, v_dict) in enumerate(fac_items):
                    is_last_fac = (i == len(fac_items) - 1)
                    fac_prefix = " └─" if is_last_fac else " ├─"
                    total_fac = sum(d["count"] for d in v_dict.values())
                    print(f"{fac_prefix} 🏭 {fac} ({total_fac}건)")
                    
                    v_items = list(v_dict.items())
                    for j, (vendor, info) in enumerate(v_items):
                        is_last_v = (j == len(v_items) - 1)
                        v_prefix = "     └─" if is_last_fac else " │   └─"
                        if not is_last_v:
                            v_prefix = "     ├─" if is_last_fac else " │   ├─"
                        
                        sample_str = info["sample"].split()[0] if info["sample"] else ""
                        sample_disp = f" ({sample_str} 외)" if info["count"] > 1 else f" ({sample_str})" if sample_str else ""
                        print(f"{v_prefix} {vendor}: {info['count']}건{sample_disp}")

            # 2. 자동보충 트리
            print(f"\n📂 [자동보충] 총 {len(tb_df)}건")
            if not tb_df.empty:
                tb_grouped = {}
                for _, row in tb_df.iterrows():
                    mc = str(row.get("자재코드", "")).strip()
                    vendor = vendor_map.get(mc, "미상업체")
                    if vendor not in tb_grouped:
                        tb_grouped[vendor] = 0
                    tb_grouped[vendor] += 1
                    
                print(f" └─ 🤖 재고 모니터링 품목 ({len(tb_df)}건)")
                v_items = sorted(list(tb_grouped.items()), key=lambda x: x[1], reverse=True)
                for j, (vendor, count) in enumerate(v_items):
                    is_last_v = (j == len(v_items) - 1)
                    v_prefix = "     └─" if is_last_v else "     ├─"
                    print(f"{v_prefix} {vendor}: {count}건")

        print_detailed_step1_tree(data_dict)
        print(f"\n(참고: 자재요청 이력 {fr}건, PO {po}건, 예측 {fc}건 로드됨)")
        
        # Step 2. 비즈니스 룰 기반 발주 로직 적용
        print("\n[2/3] 비즈니스 로직(발주 제안) 처리 중...")
        plan_df = generate_procurement_plan(data_dict)
        print(f"✅ Step 2 완료: 총 {len(plan_df)}건의 발주 제안 품목 도출")
        
        # Step 3. 엑셀 리포트 생성
        print("\n[3/3] 엑셀 리포트 생성 중...")
        filepath = generate_excel_report(plan_df)
        print(f"\n🎉 완료! 결과물 엑셀이 생성되었습니다.")
        
        while True:
            choice = input("\n작업이 완료되었습니다. [1] output 폴더 열기 / [2] 종료 : ")
            if choice == '1':
                import os
                out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
                if os.path.exists(out_dir):
                    os.system(f"open '{out_dir}'")
                else:
                    print(f"⚠️ output 폴더를 찾을 수 없습니다: {out_dir}")
                break
            elif choice == '2':
                break
            else:
                print("1 또는 2를 입력해주세요.")
        
    except Exception as e:
        print(f"\n❌ 파이프라인 실행 중 에러: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

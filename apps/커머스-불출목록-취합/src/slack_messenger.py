#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
커머스 통합자동화 — 슬랙 공유 메시지 자동 생성 (slack_messenger.py)

최종 엑셀('정리' 시트)에서 미불출 품목을 분석하고,
호텔 타월 데이터를 결합하여 슬랙 공유용 텍스트 파일을 생성.
"""

import subprocess
from pathlib import Path

import pandas as pd

from config import TODAY_STR, DAY_KR, OUTPUT_DIR

# ──────────────────────────── 고정 상수 ────────────────────────────

DRIVE_LINK = "https://drive.google.com/drive/folders/1WxQcbGbvdwyxQ8a70sPEpj6xgFkGyBAX?usp=share_link"


# ──────────────────────────── 미불출 분석 ────────────────────────────

def _analyze_shortages(excel_path: Path) -> dict[str, list[dict]]:
    """최종 엑셀의 '정리' 시트에서 팩토리별 미불출(재고 부족) 품목을 추출.

    미불출 조건: 불출수량 > 재고량 (재고가 요청보다 적어 전량 불출 불가)

    Returns
    -------
    {"군포": [{"상품명": ..., "옵션": ..., ...}, ...], "성수": [...]}
    """
    shortages: dict[str, list[dict]] = {"군포": [], "성수": []}

    try:
        df = pd.read_excel(
            excel_path, sheet_name='정리', engine='openpyxl',
            dtype={'상품 바코드': str, 'ERP 번호': str, '회원카드번호': str},
        )
    except Exception as e:
        print(f"  ⚠️ 정리 시트 읽기 실패: {e}")
        return shortages

    for _, row in df.iterrows():
        inv = pd.to_numeric(row.get("재고량", 0), errors="coerce") or 0
        req = pd.to_numeric(row.get("불출수량", 0), errors="coerce") or 0

        if req <= 0 or inv >= req:
            continue

        factory = str(row.get("팩토리", "")).strip()
        key = "군포" if "군포" in factory else ("성수" if "성수" in factory else None)
        if key is None:
            continue

        # 실제 출고 가능 수량 계산
        actual = int(inv) if inv > 0 else 0
        reason = "재고없음" if actual == 0 else f"재고부족({actual}개)"

        shortages[key].append({
            "상품명": str(row.get("상품명", "")),
            "옵션": str(row.get("옵션", "")),
            "바코드": str(row.get("상품 바코드", "")),
            "ERP번호": str(row.get("ERP 번호", "")),
            "회원카드": str(row.get("회원카드번호", "")),
            "요청": int(req),
            "실제": actual,
            "사유": reason,
        })

    return shortages


# ──────────────────────────── 메시지 포매팅 ────────────────────────────

def _format_shortage_block(factory: str, items: list[dict]) -> str:
    """팩토리별 미불출 품목 블록 포매팅."""
    if not items:
        return f"ㄴ `{factory}` : 미불출 건 없음"

    lines = [f"ㄴ `{factory}` : {len(items)}품목"]
    for item in items:
        name = item["상품명"]
        option = item["옵션"]
        label = f"{name} {option}".strip() if option and option != "nan" else name

        lines.append(f"   📦 [{label}]")
        lines.append(f"      - 바코드: {item['바코드']} (ERP: {item['ERP번호']})")
        lines.append(
            f"      - 회원카드: {item['회원카드']} | "
            f"요청: {item['요청']}개 → 실제: {item['실제']}개 ({item['사유']})"
        )

    return "\n".join(lines)


def _generate_message(
    excel_path: Path,
    towel_results: dict[str, int],
) -> str:
    """슬랙 공유용 텍스트 메시지 전문 생성."""

    shortages = _analyze_shortages(excel_path)

    # 특이사항 요약
    total_shortage = sum(len(v) for v in shortages.values())
    if total_shortage == 0:
        remark = "특이사항 없음"
    else:
        parts = []
        for fac in ["군포", "성수"]:
            if shortages[fac]:
                parts.append(f"{fac} 미불출 {len(shortages[fac])}품목 발생")
        remark = ", ".join(parts)

    # 팩토리별 미불출 블록
    gunpo_block = _format_shortage_block("군포", shortages["군포"])
    seongsu_block = _format_shortage_block("성수", shortages["성수"])

    # 호텔 타월
    gp_towel = towel_results.get("군포", 0)
    ss_towel = towel_results.get("성수", 0)

    message = f"""{TODAY_STR}({DAY_KR}) 커머스 상품 및 호텔타월 불출 내역 공유드립니다.

1️⃣ 커머스 상품
- 불출 리스트 : {DRIVE_LINK}
- 특이사항 : {remark}
{gunpo_block}
{seongsu_block}

2️⃣ 호텔 타월
- `군포`: {gp_towel} set
- `성수`: {ss_towel} set (Only 증정품)"""

    return message


# ──────────────────────────── 공개 API ────────────────────────────

def generate_slack_file(
    excel_path: Path,
    towel_results: dict[str, int],
) -> Path | None:
    """슬랙 메시지 txt 파일 생성 + 터미널 출력 + 클립보드 복사.

    Parameters
    ----------
    excel_path : Task 4에서 생성된 최종 엑셀 파일 경로
    towel_results : Task 1에서 반환된 {"성수": int, "군포": int}

    Returns
    -------
    생성된 txt 파일 경로 또는 None
    """
    print("\n" + "=" * 60)
    print("📨 Task 5: 슬랙 공유 메시지 생성")
    print("=" * 60)

    msg = _generate_message(excel_path, towel_results)

    # txt 파일 저장
    txt_path = OUTPUT_DIR / f"{TODAY_STR}_슬랙공유메세지.txt"
    txt_path.write_text(msg, encoding="utf-8")
    print(f"  💾 텍스트 파일 → {txt_path.name}")

    # 터미널 출력
    print()
    print("─" * 50)
    print(msg)
    print("─" * 50)

    # macOS 클립보드 복사
    try:
        process = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
        process.communicate(msg.encode("utf-8"))
        print("\n  ✅ 클립보드에 복사 완료 — Cmd+V로 슬랙에 붙여넣기하세요!")
    except Exception as e:
        print(f"\n  ⚠️ 클립보드 복사 실패: {e}")

    return txt_path

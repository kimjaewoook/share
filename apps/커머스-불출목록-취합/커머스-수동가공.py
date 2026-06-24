#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
커머스 데이터 수동 가공 스크립트

사용 방법:
1. input/ 폴더에 'product_release_*' (출고대상 엑셀) 및 'wms_inventory_*' (재고 엑셀) 파일을 수동으로 넣습니다.
2. 이 스크립트를 실행합니다.
3. 브라우저 자동화 과정 없이 곧바로 데이터 가공만 수행하여 output/ 폴더에 최종 파일을 생성합니다.
"""

import sys
import traceback
from pathlib import Path

# src/ 폴더의 모듈을 참조할 수 있도록 시스템 경로 추가
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from task_processor import run_processing

def main():
    print("=" * 60)
    print("🚀 수동 가공 모드 시작 (input/ 폴더 파일 기반)")
    print("=" * 60)

    try:
        # 데이터 가공(Task 4)만 단독 실행
        success, output_path = run_processing()
        
        if success and output_path:
            print(f"\n✅ 가공 성공! 최종 결과물 파일이 정상적으로 생성되었습니다.")
            print(f"   경로: {output_path}")
        else:
            print("\n⚠️ 가공에 실패했거나 대상 파일이 없습니다.")
            print("   input/ 폴더 내에 출고 엑셀과 재고 엑셀 파일이 올바르게 들어있는지 확인해 주세요.")

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
        print(f"\n❌ 데이터 가공 중 치명적 오류 발생: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()

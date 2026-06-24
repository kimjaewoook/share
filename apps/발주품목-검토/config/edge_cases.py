# config/edge_cases.py

import math
from datetime import timedelta

# ---------------------------------------------------------
# 1. 직납 라우팅 (Direct Delivery Routing)
# 특정 팩토리에서 특정 품목 발주 시 벤더사를 강제로 맵핑합니다.
# ---------------------------------------------------------
ROUTING_RULES = {
    # 팩토리명: { "키워드": "벤더사명" }
    "부산팩토리": {
        "용제": "경동라인",
        "필터": "경동라인",
        "잡자재": "경동라인"
    },
    "성수팩토리": {
        "용제": "진주크린텍",
        "필터": "진주크린텍"
    },
    "군포팩토리": {
        "용제": "진주크린텍",
        "필터": "진주크린텍"
    }
}

# ---------------------------------------------------------
# 2. 직납 품목 고정 납품 요일 (Delivery Days for Direct PO)
# 요일 매핑: 0=월, 1=화, 2=수, 3=목, 4=금, 5=토, 6=일
# ---------------------------------------------------------
DELIVERY_DAYS = {
    "진주크린텍": 4,  # 금요일
    # 메이네티, 라이트백 등 직납 고정 요일이 있다면 이곳에 추가합니다.
}

# 팩토리별 정기 발주/입고 리듬 (참고용)
FACTORY_DELIVERY_DAYS = {
    "성수팩토리": 1, # 화 입고
    "군포팩토리": 2, # 수 입고
    "부산팩토리": 4, # 금 입고
}

# ---------------------------------------------------------
# 3. 벤더별 예외 및 보정 로직 (Vendor Specific Exception Handlers)
# ---------------------------------------------------------

def adjust_quantity_everone(quantity, pallet_qty):
    """
    에버원: 짝수 파렛트 강제 올림 로직
    - 산출된 수량을 파렛트 입수량 단위로 환산 후, 홀수 파렛트면 1파렛트를 더해 짝수로 만듦.
    """
    if not pallet_qty or pallet_qty <= 0:
        return quantity
    pallets = math.ceil(quantity / pallet_qty)
    if pallets % 2 != 0:
        pallets += 1
    return pallets * pallet_qty

def adjust_quantity_kyungdong(quantity, moq):
    """
    경동라인: MOQ 보정
    - 수량이 MOQ 미달이거나 단위가 안 맞을 경우 MOQ의 배수로 강제 올림.
    """
    if not moq or moq <= 0:
        return quantity
    return math.ceil(quantity / moq) * moq

def adjust_quantity_seoheung(quantity):
    """
    서흥하이텍: 800개 단위 강제 올림
    """
    return math.ceil(quantity / 800) * 800

def get_lead_time_iruda(quantity):
    """
    이루다테크: 수량별 동적 리드타임 반환
    """
    if quantity >= 600_000:
        return 28 # 4주
    elif quantity >= 400_000:
        return 21 # 3주
    else:
        return 14 # 최소 2주

def normalize_price_like_new_clothes(price_vat_inclusive):
    """
    새옷처럼: 단가 정규화 (VAT 제외 단가로 변환)
    """
    return round(price_vat_inclusive / 1.1)

def block_jisoo_tech_molds(item_name):
    """
    지수테크: 금형 품목 발주 차단 (대체 벤더로 이관 필요시 True 반환)
    """
    blocked_keywords = ["하의 옷걸이", "와이셔츠 옷걸이", "금형"]
    for kw in blocked_keywords:
        if kw in item_name:
            return True
    return False


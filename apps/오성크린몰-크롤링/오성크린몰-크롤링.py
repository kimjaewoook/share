import os
import time
import random
import requests
import shutil
import datetime
from bs4 import BeautifulSoup
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv, find_dotenv

# 환경변수 탐색 및 로드 (표준 규칙)
load_dotenv(find_dotenv())

# 표준 경로 지정 (앱 단위 최상단에 스크립트 위치)
BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"
ARCHIVE_DIR = BASE_DIR / "archive"

OUTPUT_FILE = OUTPUT_DIR / "ohseongmall_products.xlsx"

BASE_URL = "https://www.ohseongmall.co.kr"

def rotate_data():
    now = datetime.datetime.now()
    days = ['월', '화', '수', '목', '금', '토', '일']
    day_str = days[now.weekday()]
    archive_folder_name = f"{now.strftime('%Y-%m-%d')}({day_str})"
    archive_target = ARCHIVE_DIR / archive_folder_name
    
    if archive_target.exists():
        archive_target = ARCHIVE_DIR / f"{archive_folder_name}_{now.strftime('%H%M%S')}"
        
    moved_any = False
    
    # input, output 폴더 확인 및 생성
    INPUT_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    for d in [INPUT_DIR, OUTPUT_DIR]:
        for item in d.iterdir():
            if item.is_file() and not item.name.startswith('.'):
                if not moved_any:
                    archive_target.mkdir(parents=True, exist_ok=True)
                    moved_any = True
                shutil.move(str(item), str(archive_target / item.name))

def get_categories():
    res = requests.get(BASE_URL)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, 'html.parser')
    
    categories = []
    for a in soup.find_all('a', href=True):
        if 'list.php?ca_id=' in a['href']:
            ca_id = a['href'].split('ca_id=')[-1].split('&')[0]
            cat_name = a.get_text(strip=True)
            if cat_name and cat_name[0].isdigit() and '. ' in cat_name:
                cat_num = int(cat_name.split('.')[0])
                if 1 <= cat_num <= 28:
                    if ca_id not in [c['ca_id'] for c in categories]:
                        categories.append({'ca_id': ca_id, 'name': cat_name})
    return categories

def crawl():
    print("데이터 로테이션 진행 중...")
    rotate_data()
    
    print("크롤링을 시작합니다. 대상 카테고리 추출 중...")
    categories = get_categories()
    print(f"총 {len(categories)}개의 카테고리(1~28)를 찾았습니다.")

    all_data = []

    for cat in categories:
        ca_id = cat['ca_id']
        cat_name = cat['name']
        page = 1
        
        while True:
            list_url = f"{BASE_URL}/shop/list.php?ca_id={ca_id}&page={page}"
            print(f"[{cat_name}] {page}페이지 탐색 중: {list_url}")
            
            try:
                res = requests.get(list_url)
                if res.status_code != 200:
                    break
            except Exception as e:
                print(f"목록 페이지 접근 에러: {e}")
                break
                
            soup = BeautifulSoup(res.text, 'html.parser')
            items = soup.find_all('div', class_='item-list')
            
            if not items:
                break
                
            for item in items:
                a_tag = item.find('a', href=True)
                if not a_tag:
                    continue
                    
                detail_href = a_tag['href']
                if detail_href.startswith('./'):
                    detail_href = '/shop/' + detail_href[2:]
                elif detail_href.startswith('item.php'):
                    detail_href = '/shop/' + detail_href
                    
                detail_url = BASE_URL + detail_href
                
                img_tag = item.find('img')
                thumb_url = img_tag['src'] if img_tag else ""
                if thumb_url.startswith('/'):
                    thumb_url = BASE_URL + thumb_url
                
                # 안전제일 1~2초 대기
                time.sleep(random.uniform(1.0, 2.0))
                
                try:
                    detail_res = requests.get(detail_url)
                    detail_soup = BeautifulSoup(detail_res.text, 'html.parser')
                    
                    title_elem = detail_soup.find('h1')
                    product_name = title_elem.get_text(strip=True) if title_elem else ""
                    
                    desc_elem = detail_soup.find('div', class_='item-explan')
                    desc_text = desc_elem.get_text(separator='\n', strip=True) if desc_elem else ""
                    
                    price_input = detail_soup.find('input', id='it_price')
                    base_price = int(price_input['value']) if price_input else 0
                    
                    select_elem = detail_soup.find('select', class_='it_option')
                    has_valid_options = False
                    
                    if select_elem:
                        options = select_elem.find_all('option')
                        for opt in options:
                            val = opt.get('value', '')
                            text = opt.get_text(strip=True)
                            
                            if not val or '선택' in text:
                                continue
                            
                            if '내륙' in text or '제주' in text or '내륙' in val or '제주' in val:
                                continue
                                
                            parts = val.split(',')
                            if len(parts) >= 2:
                                opt_name = text.split(' +')[0].strip() if ' +' in text else text
                                try:
                                    add_price = int(parts[1])
                                except ValueError:
                                    add_price = 0
                                final_price = base_price + add_price
                                
                                all_data.append({
                                    '카테고리명': cat_name,
                                    '제품명': product_name,
                                    '옵션명': opt_name,
                                    '최종 가격': final_price,
                                    '상세페이지 URL': detail_url,
                                    '썸네일 이미지 URL': thumb_url,
                                    '본문 텍스트 내용': desc_text
                                })
                                has_valid_options = True
                                
                    if not has_valid_options:
                        all_data.append({
                            '카테고리명': cat_name,
                            '제품명': product_name,
                            '옵션명': '기본상품',
                            '최종 가격': base_price,
                            '상세페이지 URL': detail_url,
                            '썸네일 이미지 URL': thumb_url,
                            '본문 텍스트 내용': desc_text
                        })
                        
                except Exception as e:
                    print(f"상세 페이지 파싱 에러 {detail_url}: {e}")
            
            target_page_str = f"page={page+1}"
            next_a = soup.find('a', href=lambda h: h and target_page_str in h)
            
            if next_a:
                page += 1
                time.sleep(random.uniform(1.0, 2.0))
            else:
                break
                
    print("모든 크롤링 완료. 데이터를 엑셀로 저장합니다.")
    df = pd.DataFrame(all_data)
    df.to_excel(str(OUTPUT_FILE), index=False)
    print(f"저장 완료! 파일 위치: {OUTPUT_FILE}")

if __name__ == '__main__':
    crawl()

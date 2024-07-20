from time import sleep
from urllib.request import urlopen
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import pandas as pd
import pickle
from tqdm.auto import tqdm
import re
import traceback


def search_target_url(BASE_URL: str, START_PAGE: int, END_PAGE: int):
    """
    引数は、ベースとなるurl、スクレイピングする開始ページ、最終ページ
    戻り値は、スクレイピングする対象のurlリスト
    dataフォルダに'target_url_list.pkl'として出力
    """
    pages = [i for i in range(START_PAGE, END_PAGE + 1)]
    list_urls = [f"{BASE_URL}&sort=10&page={page}" for page in pages]
    target_url_list = []
    try: 
        for list_url in tqdm(list_urls):
            html = urlopen(list_url).read()
            sleep(1)
            soup = BeautifulSoup(html, "lxml")
            boxies = soup.find_all("li", class_="search_result_box")
            target_urls = []
            for box in boxies:
                try: 
                    target_url = f"https://www.cmoa.jp{box.find('a')['href']}"
                    target_urls.append(target_url)
                except:
                    print(list_url)
                    print(box)
                    print("An error occurred:")
                    traceback.print_exc()
            target_url_list.extend(target_urls)
    except: 
        print(list_url)
        print("An error occurred:")
        traceback.print_exc()
    with open(f"../data/target_url_list{START_PAGE}-{END_PAGE}.pkl", "wb") as f:
        pickle.dump(target_url_list, f)
    return target_url_list

def get_result(target_url_list: list): 
    """
    引数は、スクレイピング対象のurlリスト
    戻り値はスクレイピング結果のデータフレーム
    dataフォルダに'result.csv'を出力
    """
    driver_path = ChromeDriverManager().install()
    options = Options()
    options.add_argument("--headless")
    service = Service(executable_path=driver_path)
    browser = webdriver.Chrome(options=options, service=service)
    browser.maximize_window()
    result_list = []
    for url in tqdm(target_url_list): 
        try: 
            browser.get(url)
            body = WebDriverWait(browser, 15).until(EC.presence_of_all_elements_located((By.TAG_NAME, 'body')))
            browser.find_element(By.ID, 'description_btn').click()
            html = browser.page_source
            soup = BeautifulSoup(html, 'lxml')
            author = soup.title.text.split('｜')[1]
            title = soup.title.text.split('｜')[0]
            try: 
                volume = int(soup.find('div', class_='volume').text.strip().replace('\n', '').split('巻')[0])
                completed = soup.find('div', class_='volume').text.strip().replace('\n', '').split('巻')[1].replace('配信中', '連載')
            except:
                volume = ' - '
                completed = ' - '
                print(url)
                print("An error occurred:")
                traceback.print_exc()
            details = soup.find_all('div', class_='category_line')
            detail_list = [detail.text.replace('\n', '').strip() for detail in details]
            for d in detail_list:
                if '配信開始日' in d:
                    start_date = re.search(r'(\d{4}年\d{1,2}月)', d.split('：')[1].strip()).group(1)
                elif '作品タグ' in d: 
                    tag = d.split('：')[1].replace('※システムにて自動抽出したものを表示しています', '').strip()
                elif '出版社' in d: 
                    publisher = d.split('：')[1].strip()
                else: 
                    pass
            content = soup.find('div', class_='title_intro_box_area').find('p').text.replace('\u3000', ' ')
            dic = dict()
            dic['作者名'] = author
            dic['タイトル'] = title
            dic['既巻数'] = volume
            dic['完結or連載'] = completed
            dic['出版年月'] = start_date
            try:
                dic['作品タグ'] = tag
            except:
                dic['作品タグ'] = ' - '
                print(url)
                print("An error occurred:")
                traceback.print_exc()
            dic['出版社'] = publisher
            dic['作品内容'] = content
            result_list.append(dic)
        except: 
            print(url)
            print("An error occurred: このページはスクレイピングできませんでした")
            traceback.print_exc()
    browser.quit()
    result_df = pd.DataFrame(result_list)
    result_df.to_csv(f'../data/result_to_title{target_url_list[-1].split("/")[-2]}.csv', index=False)
    return result_df
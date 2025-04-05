
import requests
import random
import time 

import validators
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.common.action_chains import ActionChains



def get_content(page): 
    soup = BeautifulSoup(page, "html.parser")
    page_text = soup.get_text(strip=True) # .replace("\n", "")
    return page_text


def get_features(page): 
    features = ""
    try: 
        soup = BeautifulSoup(page, "html.parser")
        features = soup.find_all(id="feature-bullets")[0].get_text(strip=True)
    except IndexError: 
        return None
    return features


def get_description(page): 
    description = None
    try: 
        soup = BeautifulSoup(page, "html.parser")
        description = soup.find_all(id="productDescription")[0].get_text(strip=True)
    except IndexError: 
        return None
    return description


def get_title(page): 
    item_title = ""
    try: 
        soup = BeautifulSoup(page, "html.parser")
        item_title = soup.find_all(id="productTitle")[0].get_text(strip=True)
    except IndexError: 
        return None 
    return item_title


def detector(url): 
    options = Options()
    options.add_argument("--no-sandbox")  # Fix permission issues in WSL
    options.add_argument("--headless=new")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    # options.add_argument("-incognito")

    options.set_capability("goog:loggingPrefs", {"performance": "ALL"})  # Enable network logs

    chromedriver_path = "/usr/bin/chromedriver" 
    service = Service(chromedriver_path)

    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(10)
    driver.set_script_timeout(10) 

    actions = ActionChains(driver)
    actions.move_by_offset(random.randint(0, 100), random.randint(0, 100)).perform()
    time.sleep(random.uniform(1, 3))


    driver.get(url)
    logs = driver.get_log("performance")
    rendered_html = driver.page_source


    title = get_title(rendered_html)
    description = get_description(rendered_html)
    features = get_features(rendered_html)

    if not title: 
        content = get_content(rendered_html)
        print(f"first 128 characters of content: {content[:128]}")
    else: 
        print(f"title: {title}") ### 


    driver.quit()


# url = "https://www.amazon.com/Kickstand-Replacement-Compatible-Microsoft-Surface/dp/B08J294T72?th=1"
# url = "https://www.amazon.com/CeraVe-Salicylic-Cleanser-Exfoliating-Fragrance/dp/B08CQ9T6KN/ref=sr_1_1?crid=1OKWMO2Y9XOWL&dib=eyJ2IjoiMSJ9.DpzXuYoOxzbDr-pCi-mKC0FFjRwUx9j3EkivcalZpUbQXe08tyno_3OJe8zvkoPSPmKjprp1AU1IOIl6-A0oc6kFm8_-9Ba0TGYKkMPz5-5Sm_YYSYHH8_1JZz6uitMbNggoNg_hjE7JaT9S1maOR65LGeSgYRVgnO0xP0r92agjsHvq-W5Xn6nNwdWx4QWT6qB5uHy02KNCHKGkIlF_ushXzTu8uKG9dMCn2FpU15Axrs6uP7PBK19OW_udmZBLRjSoXlSwMbf9lQ4q5YZ914d6AofxLvgLlaKIPrP-0COsPc3LAXSJln0NbLfD0XvYSmsmnrCDsPoSLh_u0hDGVrkBBIustXc_wtbJMPBPnqEeEMoEThG8p0CbKXe8H_kuCBqUk4uCxHRd3T9wBp80fAtT7GmkIVLTLqXuM-R_Rnq82vO4RiIbUKZTQVrEVquf.0MsMkbXc4VgjxBqB5UqpirKkQNL3MD9khMxLpMfWVLs&dib_tag=se&keywords=CERAVE&qid=1742758409&rdc=1&sprefix=cerave%2Caps%2C176&sr=8-1&th=1"

urls = [
    "https://www.amazon.com/s?k=television&i=tools&crid=2J3Z0Q0HFWB4H&sprefix=television%2Ctools%2C107&ref=nb_sb_noss_2", 
    "https://www.amazon.com/insignia-fire-tv-50-inch-class-f30-series-4k-smart-tv/dp/B0BTTVRWPR?ref=dlx_bigsp_dg_dcl_B0BTTVRWPR_dt_sl15_a7&pf_rd_r=7D854E2MDC526C9D3VBK&pf_rd_p=8f2d149e-8218-467e-bea8-84efdeabcca7", 
    "https://www.amazon.com/insignia-fire-tv-43-inch-class-f30-series-4k-smart-tv/dp/B0CMDJ8TK3/ref=pd_adz_ddpd_wwa_d_sccl_1_4/142-0862937-0937229?pd_rd_w=A0yj1&content-id=amzn1.sym.724cd912-c474-41a7-8556-024b17de3454&pf_rd_p=724cd912-c474-41a7-8556-024b17de3454&pf_rd_r=19RS4MJ8ZYGPVDD2WM19&pd_rd_wg=yqAuN&pd_rd_r=e0da80b0-39fd-4980-b335-8e928946ba7e&pd_rd_i=B0CMDJ8TK3&psc=1", 
    "https://www.amazon.com/Flip-n-Store-EverGoodTM-Fits-anywhereTM-Kitchenware-Indicator/dp/B0CYHZFMFX/ref=hw_25_e_dag_d_24bc?pf_rd_p=2db5dd94-38f1-4bee-afda-ba831ef84c44&pf_rd_r=3QCYYKR5D326CGRCMR1W&sr=1-10-e910b296-10e5-4d29-9a4c-087eb8ed5418", 
]

for url in urls: 
    print(f"------- {url} -------")
    detector(url)

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
        feature_tags = soup.find_all(attrs={"class": "ipc-chip__text"})[:-1] # remove the back_to_top one
        features =  [feature_tag.get_text(strip=True) for feature_tag in feature_tags]
        features = ",".join(features)
    except IndexError: 
        return None
    return features


def get_description(page): 
    description = None
    try:
        soup = BeautifulSoup(page, "html.parser")
        description = soup.find_all(attrs={"data-testid": "plot-l"})[0].get_text(strip=True)
    except IndexError: 
        return None
    return description


def get_title(page): 
    item_title = ""
    try: 
        soup = BeautifulSoup(page, "html.parser")
        # item_title = soup.find_all(attrs={"data-testid": "hero__pageTitle"})[0].get_text(strip=True)
        item_title = soup.find_all("title")[0].get_text(strip=True)
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

    content = get_content(rendered_html)
    title = get_title(rendered_html)
    features = get_features(rendered_html)
    description = get_description(rendered_html)


    if not title: 
        content = get_content(rendered_html)
        print(f"first 128 characters of content: {content[:128]}")
    else: 
        print(f"title: {title}") ### 


    driver.quit()


urls = [
    "https://www.imdb.com/title/tt8999762/?ref_=hm_fanfav_t_5_pd_fp1_r", 
    "https://www.imdb.com/title/tt0120737/?ref_=chttp_t_9"
]

for url in urls: 
    print(f"------- {url} -------")
    detector(url)

import requests

from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs

# from playwright.sync_api import sync_playwright

# def is_url_accessible_playwright(url):
#     with sync_playwright() as p:
#         browser = p.chromium.launch(headless=True)
#         page = browser.new_page()
#         breakpoint()
#         try:
#             response = page.goto(url, timeout=10000)  # 0.5-second timeout
#             # loaded successfully (status 200)
#             if response and response.status == 200:
#                 page_content = page.content().lower()
#                 # Look for known error messages or blank content
#                 error_messages = ["404 not found", "403 forbidden", "sign in"]
#                 for msg in error_messages: 
#                     print(msg)
#                 if any(msg in page_content for msg in error_messages):
#                     return False
                
#                 return True
#             else:
#                 return False

#         except Exception as e:
#             return False
#         finally:
#             browser.close()


def is_url_accessible(url):
    try:
        url_session = requests.Session()
        # User-Agent header to mimic a browser
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
        }
        # request with headers and session
        url_session.cookies.clear()
        response = url_session.get(url, headers=headers, timeout=10, allow_redirects=False)

        # output code in log 
        print("response.status_code: ", response.status_code)

        if response.status_code in [401, 403, 404]:  
            return False
        return response.status_code == 200
    
    except requests.RequestException as e:
        print(f"Request failed: {e}")
        return False
    

def is_generated_page(url):

    # criteria 1: query or search operator 
    def contains_query_optr(url): 
        parsed_url = urlparse(url)
        if len(parse_qs(parsed_url.query)) > 2: 
            return True
        if "search" in parsed_url.path or "query" in parsed_url.query:  
            return True
    
    # criteria 2: link structure 
    def is_mostly_links(soup):
        # links outnumber paragraphs significantly, assume it's a generated page
        links = soup.find_all("a")
        paragraphs = soup.find_all("p")
        text_length = len(soup.get_text(strip=True))
        return len(links) > 5 * len(paragraphs) and text_length < 100

    # c1: url link inpsection 
    if contains_query_optr(url):  
        return True 
    
    # c2-c3: bs4 related processing 
    try:
        response = requests.get(url, timeout=5)
        soup = BeautifulSoup(response.text, "html.parser")
    except requests.RequestException:
            return True
    if is_mostly_links(soup): 
        return True 

    return False

# url = "https://hpc.lti.cs.cmu.edu/wiki/index.php?title=BABEL"
# print(is_url_accessible(url))
# print(is_generated_page(url))

# print(is_generated_page("https://steelersdepot.com/"))
# is_url_accessible_playwright: doesn't work for wandb and steeler 


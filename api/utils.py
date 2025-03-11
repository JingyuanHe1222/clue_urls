import requests 


def is_url_accessible(url):
    try:
        session = requests.Session()
        response = session.get(url, timeout=10, allow_redirects=True)
        # Check for authentication-required status codes
        if response.status_code in [401, 403]:
            return False
        login_keywords = ["404", "sign in", "log in", "authentication required", "please sign in", "create an account"]
        if any(keyword in response.text.lower() for keyword in login_keywords):
            return False
        
        return response.status_code == 200
    except requests.RequestException:
        return False
    

import asyncio
from playwright.async_api import async_playwright


def is_url_public_accessible(url): 
    async def run():
        async with async_playwright() as p:
            browser = await p.firefox.launch(headless=True)  # or p.chromium, p.webkit
            page = await browser.new_page()
            await page.goto(url)
            content = await page.content()
            await browser.close()
            return content

    return asyncio.run(run())



url = 'https://wandb.ai/jingyuanhe1222/RecSys-Benchmark/runs/nwro6ial?nw=nwuserjingyuanhe1222'

print(is_url_accessible(url))

# Example usage:
print(is_url_public_accessible(url))

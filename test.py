from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

from webdriver_manager.chrome import ChromeDriverManager

import time

options = Options()

options.page_load_strategy = 'none'

options.add_argument("--start-maximized")

options.add_argument("--disable-notifications")

options.add_argument("--disable-blink-features=AutomationControlled")

driver = webdriver.Chrome(
    service=Service(
        ChromeDriverManager().install()
    ),
    options=options
)

try:

    driver.set_page_load_timeout(20)

    driver.get(
        "https://reportplus.mizopower.com/"
    )

except Exception as e:

    print("⚠ Page load timeout")

    print(e)

    driver.execute_script("window.stop();")

print("Website opening...")

time.sleep(15)

print("Current URL:", driver.current_url)

print("Title:", driver.title)

time.sleep(60)

driver.quit()
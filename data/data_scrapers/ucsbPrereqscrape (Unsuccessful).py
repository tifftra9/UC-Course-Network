from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time, csv, random, os, requests

#--------
#This scraper was unsuccessful due to bot detection
#-------

TOTAL_PAGES = 614
def human_delay(a=0.3, b=0.6):
    time.sleep(round(random.uniform(a, b), 2))

options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")
options.add_argument("--disable-blink-features=AutomationControlled")
driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, 10)

outputFile = "ucsb_prereqs.csv"

if not os.path.exists(outputFile):
    with open(outputFile, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(["course_link", "prerequisites"])
    startPage = 1
else:
    with open(outputFile, "r", encoding="utf-8") as f:
        rows = f.readlines()
    scrapedCount = len(rows) - 1
    startPage = scrapedCount // 20 + 1
    print("Resuming from page:", startPage)

def scroll_to_load_all():
    last_h = 0
    while True:
        driver.execute_script("window.scrollBy(0, 500);")
        time.sleep(0.2)
        newH = driver.execute_script("return document.body.scrollHeight")
        if newH == last_h:
            break
        last_h = newH
# flip through all pages
for page in range(startPage, TOTAL_PAGES + 1):
    list_url = f"https://catalog.ucsb.edu/courses?sortBy=code&cq=&page={page}"
    print(f"\n Page {page}/{TOTAL_PAGES}")
    driver.get(list_url)

    human_delay()
    wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "course-button")))
    scroll_to_load_all()
    human_delay()

    hrefs = []
    links = driver.find_elements(By.CSS_SELECTOR, ".course-button a")

    for link in links: 
        try:
            hrefs.append(link.get_attribute("href"))
        except:
            pass

    print(f"Found {len(hrefs)} course links")

    for href in hrefs: # this processes each link

        print(f"Scraping: {href}")

        apiLink = href.replace("https://catalog.ucsb.edu", "https://catalog.ucsb.edu/api")
        try:
            data = requests.get(apiLink).json()
            prereq = data.get("prerequisites", "").strip()
        except:
            prereq = ""
        with open(outputFile, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([href, prereq])
        human_delay()

print("\n Scraping Finished")
driver.quit()

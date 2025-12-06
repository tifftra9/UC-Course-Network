from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.options import Options
import time
import csv

#selenium web setup
chrome_options = Options()
chrome_options.add_argument("--headless=new") 
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--window-size=1920,1080")
driver = webdriver.Chrome(options=chrome_options)

driver.get("https://pisa.ucsc.edu/class_search/") #this opens the url
wait = WebDriverWait(driver, 20)

output = open("ucsc_courses_full.csv", "w", newline="", encoding="utf-8")
writer = csv.writer(output)
writer.writerow(["Term", "Course Name", "Description", "Units", "Prerequisites"]) # we start with these columns, when cleaning we add the rest

termDropdown = wait.until(EC.presence_of_element_located((By.ID, "term_dropdown"))) # we choose terms here
termSelect = Select(termDropdown)

termValues = [opt.get_attribute("value") for opt in termSelect.options if opt.get_attribute("value")]

termValues = termValues[:4] # we want to scrape the first 4
print("\n terms scraped:", termValues)

for term_value in termValues: # each terms courses get collected
    print(f"Currently scraping term: {term_value}")
    
    driver.get("https://pisa.ucsc.edu/class_search/")
    wait.until(EC.presence_of_element_located((By.ID, "term_dropdown")))

    Select(driver.find_element(By.ID, "term_dropdown")).select_by_value(term_value)

    Select(driver.find_element(By.ID, "subject")).select_by_index(0)

    driver.find_element(By.CLASS_NAME, "btn-block").click()
    time.sleep(2)

    while True: #flip tthrough the pages here
        try:
            wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a[id^='class_id_']")))
        except TimeoutException:
            break

        courseLinks = driver.find_elements(By.CSS_SELECTOR, "a[id^='class_id_']")
        courseLinks = [link.get_attribute("href") for link in courseLinks]
        print(f"Found {len(courseLinks)} classes on this page.")
        
        for url in courseLinks: #iterate through each course
            try: # title
                driver.execute_script("window.open(arguments[0], '_blank');", url)
                driver.switch_to.window(driver.window_handles[-1])
                
                courseName = wait.until(
                    EC.presence_of_element_located((By.TAG_NAME, "h2"))
                ).text.strip()
                try: #unots
                    courseUnits = driver.find_element(
                        By.XPATH, "//dt[text()='Credits']/following-sibling::dd[1]"
                    ).text.strip()
                except:
                    courseUnits = "N/A"
                try: #description
                    courseDesc = driver.find_element(
                        By.XPATH,
                        "//div[@class='panel panel-default row'][div[@class='panel-heading panel-heading-custom']/h2[contains(., 'Description')]]/div[@class='panel-body']"
                    ).text.strip()
                except:
                    courseDesc = "N/A"
                try: #prereqs
                    prereqText = driver.find_element(
                        By.XPATH,
                        "//div[@class='panel panel-default row'][div[@class='panel-heading panel-heading-custom']/h2[contains(., 'Enrollment Requirements')]]/div[@class='panel-body']"
                    ).text.strip()
                except:
                    prereqText = "None"
                writer.writerow([term_value, courseName, courseDesc, courseUnits, prereqText])
                print(f"Scraped {courseName}")

            except Exception as e:
                print(f" Error when scraping {url}: {e}")
            finally:
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
                time.sleep(0.3)
        try:
            next_link = driver.find_element(By.LINK_TEXT, "next")
            if "disabled" in next_link.get_attribute("class"):
                break
            next_link.click()
            time.sleep(2)
        except NoSuchElementException:
            break

output.close()
driver.quit()
print("\n Scraping finished, saved to ucsc_courses_full.csv")

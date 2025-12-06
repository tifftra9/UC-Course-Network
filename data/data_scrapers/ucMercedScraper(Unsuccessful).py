from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd

options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")
driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, 20)

driver.get("https://reg-prod.ec.ucmerced.edu/StudentRegistrationSsb/ssb/classSearch/classSearch")

#lots of buttons to click since the link doens't take us straight to the course directory
catalogBtn = wait.until(
    EC.element_to_be_clickable((By.ID, "catalogSearchLink"))
)
catalogBtn.click()

dropdown_arrow = wait.until(
    EC.element_to_be_clickable((By.CLASS_NAME, "select2-choice"))
)
dropdown_arrow.click()

fallOption = wait.until(
    EC.element_to_be_clickable((
        By.ID,
        "202530"
    ))
)
fallOption.click()

continueBtn = wait.until(
    EC.element_to_be_clickable((By.ID, "term-go"))
)
continueBtn.click()

searchBtn = wait.until(
    EC.element_to_be_clickable((By.ID, "search-go"))
)
searchBtn.click()
wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table#table1 tbody tr")))

## Discontinued past this point since we couldn't get through to the actual table of courses


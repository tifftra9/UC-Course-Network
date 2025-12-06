from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import time

options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")
driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, 20)

#url for riverside course catalog (same as merced in terms of layout)
#html layout between for riverside and merced are identical, so the code pretty much stays the same, that being said this is why it is discontinued at the same point
driver.get("https://registrationssb.ucr.edu/StudentRegistrationSsb/ssb/classSearch/classSearch")

catalogBtn = wait.until(
    EC.element_to_be_clickable((By.ID, "catalogSearchLink"))
)
catalogBtn.click()

time.sleep(3)

dropdownArrow = wait.until(
    EC.element_to_be_clickable((By.CLASS_NAME, "select2-arrow"))
)
dropdownArrow.click()

fallOption = wait.until(
    EC.element_to_be_clickable((
        By.CLASS_NAME,
        "select2-result-label-3"
    ))
)
fallOption.click()

continueButton = wait.until(
    EC.element_to_be_clickable((By.ID, "term-go"))
)
continueButton.click()

searchButton = wait.until(
    EC.element_to_be_clickable((By.ID, "search-go"))
)
searchButton.click()

wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table#table1 tbody tr")))

#discontinued since the page didn't respond past this point

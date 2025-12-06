from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time
import re
import pandas as pd
from urllib.parse import urlparse

BASE_URL = "https://catalog.ucsd.edu/front/courses.html"

#these functions help with cleaning the data while scraping it
def extractUnits(title_text):
    match = re.search(r"\((.*?)\)", title_text)
    if not match:
        return None, None
    nums = re.findall(r"\d+", match.group(1))
    if not nums:
        return None, None
    nums = [int(x) for x in nums]
    if len(nums) == 1:
        return nums[0], nums[0]
    return nums[0], nums[-1]

def extractCourseCodeTitle(title_text):
    cleaned = re.sub(r"\(.*?\)", "", title_text).strip()
    parts = cleaned.split(".", 1)
    left = parts[0].strip()
    title = parts[1].strip() if len(parts) > 1 else ""
    if " " in left:
        code = left.split(" ", 1)[1]
    else:
        code = ""
    return code, title

def extractPrereqs(text):
    match = re.search(r"(Prereq[^.]*\.)", text, re.IGNORECASE)
    return match.group(1).strip() if match else ""

#main scraping function
def scrape_ucsd_courses():

    chrome_options = Options()
    chrome_options.add_argument("--headless=new") 
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")

    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 15)

    driver.get(BASE_URL)
    wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "courseFacLink")))
    time.sleep(1)

    subjectRows = driver.find_elements(By.CLASS_NAME, "courseFacLink")
    subjects = []

    print(f"There are {len(subjectRows)} subject rows on main page")

    for row in subjectRows:
        try:
            courses_link_el = row.find_element(By.LINK_TEXT, "courses")
        except:
            continue

        href = courses_link_el.get_attribute("href")
        if not href:
            continue

        subjectName = courses_link_el.get_attribute("title").strip()
        fileName = urlparse(href).path.split("/")[-1]
        subjectCode = fileName.split(".")[0].upper()

        subjects.append({
            "subject_name": subjectName,
            "subject_code": subjectCode,
            "url": href
        })

    print(f"Subjects With Courses: {len(subjects)}")

    allCourses = []

    #Iterates through every subject page
    for idx, subj in enumerate(subjects, start=1):
        print(f"\n[{idx}/{len(subjects)}] → {subj['subject_name']} | {subj['url']}")
        driver.get(subj["url"])
        try:
            wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "course-name")))
        except:
            print("Error: No course names found.")
            continue

        time.sleep(1)
        
        #these lists are made in parrell the descriptive qualities of San Diego are not nested well with the title info   
        courseBlocks = driver.find_elements(By.CLASS_NAME, "course-name") #gets all course title info
        descriptionBlocks = driver.find_elements(By.CLASS_NAME, "course-descriptions") #gets descriptive info
        print(f" Found {len(courseBlocks)} course titles and {len(descriptionBlocks)} course descriptions") #make sure we are scraping the right amount of courses

        limit = min(len(courseBlocks), len(descriptionBlocks))

        for i in range(limit):
            title = courseBlocks[i].text.strip()
            description = descriptionBlocks[i].text.strip()

            unitsMin, unitsMax = extractUnits(title)
            couseCode, courseTitle = extractCourseCodeTitle(title)
            prereqs = extractPrereqs(description)
            crosslist = ""

            allCourses.append({
                "Campus": "UC San Diego",
                "Subject": subj["subject_name"],
                "Subject Code": subj["subject_code"],
                "Course Code": couseCode,
                "Title": courseTitle,
                "Description": description,
                "Prerequisites": prereqs,
                "Units Min": unitsMin,
                "Units Max": unitsMax,
                "Cross Listing": crosslist,
                "URL": subj["url"],
            })

    #Saving to a csv
    df = pd.DataFrame(allCourses)
    df.to_csv("ucsd_courses.csv", index=False)
    print(f"\nCourses Scraped: {len(allCourses)}, Saved to: ucsd_courses.csv")
    driver.quit()
    
if __name__ == "__main__":
    scrape_ucsd_courses()

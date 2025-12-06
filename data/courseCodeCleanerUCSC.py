import pandas as pd
import re

df = pd.read_csv("/Users/sanjith/Downloads/ucsc_final.csv")
# we want to seperate course title, acronym, and code
def cleanCourseCode(courseTitle):
    parts = courseTitle.split(" ", 1)
    if len(parts) < 2:
        return ""
    rest = parts[1]
    codeSec = rest.split("-", 1)[0].strip()
    match = re.match(r"^([0-9]+[A-Za-z]*)", codeSec)
    return match.group(1) if match else ""

df['course_code'] = df['Course Name'].apply(cleanCourseCode)
df = df.drop(columns=['Course Name'])
df = df.rename(columns={'course_code': 'Course Name'})
df.to_csv("ucsc_final_cleaned.csv", index=False)

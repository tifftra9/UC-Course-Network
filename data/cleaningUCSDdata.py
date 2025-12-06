import pandas as pd
import re

#in this I'm mainly cleaning the preqreuisite column, and making sure the description doesn't contain any info that it doesn't need to, I'm getting rid of the url column

df = pd.read_csv("ucsd_courses.csv")

df['Description'] = df['Description'].apply(
    lambda x: re.split(r"Prereq[^.]*\.", x, flags=re.IGNORECASE)[0].strip()
    if isinstance(x, str) else x
)

df['Cross Listing'] = "null"

if 'URL' in df.columns:
    df = df.drop(columns=['URL'])

df.to_csv("ucsd_courses_cleaned.csv", index=False)
print("Cleaned File Saved")

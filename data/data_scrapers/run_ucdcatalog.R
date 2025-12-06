library(devtools)
install_github("duncantl/HAR", force = TRUE)
library(HAR)
library(RJSONIO)
library(RCurl)
library(XML)
library(RSelenium)
library(stringr)
library(dplyr)
library(tidyr)

source("ucdcatalog.R")

url = "https://catalog.ucdavis.edu/courses-subject-code/"
lines = readLines(url)
page = htmlParse(lines)

subjects = getSubjects(page)
courses = lapply(names(subjects), getCourses)
names(courses) = subjects
complete = bind_rows(courses, .id = "subject")

completeFinal = complete %>% 
  select(-tail(names(.), 2)) %>% 
  mutate("Quarter No Longer Offered" = coalesce(V2, V3)) %>% 
  select(-V2, -V3) %>%
  mutate(across(everything(), ~ gsub("\u00A0", " ", .))) 

write.csv(completeFinal, "ucd_course_catalog.csv", row.names = FALSE, 
          fileEncoding = "UTF-8", na = "")

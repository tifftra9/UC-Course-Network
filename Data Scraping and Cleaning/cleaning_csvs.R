## install packages
library(RJSONIO)
library(RCurl)
library(XML)
library(RSelenium)
library(stringr)
library(dplyr)
library(tidyr)

## UC Davis ----
UCD = read.csv("./Uncleaned/ucd_course_catalog.csv", check.names = FALSE)

UCD_clean = UCD %>% 
  mutate(Units = gsub(" units| unit", "", Units),
         Units_Min = gsub("-[0-9\\.]+", "", Units),
         Units_Max = gsub("^[0-9\\.]+-", "", Units),
         Subject = subject,
         Subject_Code = sub("^(.*) ([^ ]+)$", "\\1", Code),
         Course_Code = sub("^(.*) ([^ ]+)$", "\\2", Code)) %>% 
  relocate(Subject, Subject_Code, Course_Code, Title, Units_Min, Units_Max) %>% 
  select(-subject, -Units, -Code)

#write.csv(UCD_clean, "./Cleaned/ucd_course_catalog_CLEAN.csv", row.names = FALSE, 
       #   fileEncoding = "UTF-8", na = "")

## UCLA ----
UCLA = read.csv("./Uncleaned/UCLA.csv")

activities = list("Lecture", "Laboratory", "Seminar", "Discussion", "Tutorial", 
                  "Studio", "Fieldwork", "Activity", "Field studies", "Clinic", "Proseminar",
                  "Research group meeting", "Practicum", "Recitation", "Readings",
                  "Off-campus field archaeology", "Site-based", "Colloquium",
                  "Workshop", "Student presentation")
activities_regex = paste(unlist(activities), collapse = "|")
activities_regex = paste0("(", activities_regex, ")", 
                          "[^.]*\\b(hours?|minutes?|to be arranged)\\b[^.]*\\.")

requisties = list("Requisites?", "Recommended?:", "Corequisites?", "Prerequisites?",
                  "Requisites? for", "Enforced requisites?", "Enforced corequisites?",
                  "Recommended requisites?", "Strongly recommended requisites?",
                  "Requisites? or corequisites?", "Highly recommended requisites?", 
                  "Recommended corequisites?")
requisties = lapply(requisties, function(x) paste0(x, "[^\\.]+\\."))
requisties_regex = paste(unlist(requisties), collapse = "|")
requisties_regex = paste0(requisties_regex, "|[^.]*\\b(requisite to)\\b[^.]*\\.")

limited = list("^Limited", "^Mandatory for and limited", "^Normally limited")
limited = lapply(limited, function(x) paste0(x, "[^\\.]+\\. "))
limited_regex = paste(unlist(limited), collapse = "|")

preparation = list("Preparation:", "Recommended preparation:")
preparation = lapply(preparation, function(x) paste0(x, "[^\\n]*?(?<!\\d)\\."))
preparation_regex = paste(unlist(preparation), collapse = "|")

UCLA_clean = UCLA %>% 
  mutate(course_number = gsub(". (?<=. ).*", "", course_title, perl = TRUE),
         course_title = gsub("^[^.]+. ", "", course_title),
         subj_area_nm = gsub(" \\([A-Z ]+\\) $", "", subj_area_nm),
         unt_min = gsub(" to [0-9\\.]+| or [0-9\\.]+", "", unt_rng),
         unt_max = gsub("[0-9\\.]+ to |[0-9\\.]+ or ", "", unt_rng),
         
         formerly = str_extract(crs_desc, "\\(Formerly [^\\)]+\\)"),
         formerly = gsub("\\(Formerly numbered |\\.\\)", "", formerly),
         crs_desc = gsub("\\(Formerly [^\\)]+\\) ", "", crs_desc),
         
         same_as = str_extract(crs_desc, "\\(Same [^\\)]+\\)"),
         same_as = gsub("\\(Same as |[.)]", "", same_as),
         crs_desc = gsub("\\(Same [^\\)]+\\) ", "", crs_desc),
         
         activities = str_extract(crs_desc, activities_regex),
         crs_desc = gsub(activities_regex, "", crs_desc),
         
         crs_desc = trimws(gsub("\\s+", " ", crs_desc)),
         
         requisites = str_extract(crs_desc, requisties_regex),
         crs_desc = gsub(requisties_regex, "", crs_desc),
         requisites = trimws(gsub("\\s+", " ", requisites)),
         
         preparation = str_extract(crs_desc, preparation_regex),
         crs_desc = gsub(preparation_regex, "", crs_desc, perl = TRUE),
         
         crs_desc = trimws(gsub("\\s+", " ", crs_desc)),
         
         limited_to = str_extract(crs_desc, limited_regex),
         crs_desc = gsub(limited_regex, "", crs_desc),
         
         grading = str_extract(crs_desc, "[^.]*\\bgrading\\b[^.]*\\.?"),
         crs_desc = gsub("[^.]*\\bgrading\\b[^.]*\\.?", "", crs_desc),
         grading = trimws(gsub("\\s+", " ", grading)),
         
         concurrently = str_extract(crs_desc, "Concurrently[^\\.]+\\."),
         crs_desc = gsub("Concurrently[^\\.]+\\.", "", crs_desc),
         
         may_be = str_extract(crs_desc, "May be[^\\.]+\\."),
         crs_desc = gsub("May be[^\\.]+\\.", "", crs_desc),
         
         not_open_credit = str_extract(crs_desc, "Not open[^\\.]+\\."),
         crs_desc = gsub("Not open[^\\.]+\\.", "", crs_desc),
         
         crs_desc = trimws(gsub("\\s+", " ", crs_desc))) %>% 
  relocate(subj_area_nm, subj_area_cd, course_number) %>% 
  select(-unt_rng)

#write.csv(UCLA_clean, "./Cleaned/ucla_CLEAN.csv", row.names = FALSE, 
         # fileEncoding = "UTF-8", na = "")

## UC Irvine ----
UCI = read.csv("./Uncleaned/uci_courses_catalog.csv", check.names = FALSE)

UCI_clean = UCI %>% 
  mutate(units = gsub(" Units\\.| Unit\\.", "", units),
         units_min = gsub("-[0-9\\.]+", "", units),
         units_max = gsub("^[0-9\\.]+-", "", units),
         subject_name = gsub(" \\([A-Z ]+\\)$", "", course_name),
         subject_code = sub("^(.*) ([^ ]+)$", "\\1", code),
         course_code = sub("^(.*) ([^ ]+)$", "\\2", code),
         course_code = gsub("\\.", "", course_code),
         prerequisites = gsub("Prerequisite: ", "", prerequisites),
         repeatability = gsub("Repeatability: ", "", repeatability)) %>% 
  relocate(subject_name, subject_code, course_code, title, units_min, units_max) %>% 
  select(-code, -course_name, -units)

#write.csv(UCI_clean, "./Cleaned/uci_courses_catalog_CLEAN.csv", row.names = FALSE, 
        #  fileEncoding = "UTF-8", na = "")

## UC Santa Cruz ----
UCSC = read.csv("./Uncleaned/ucsc_final_cleaned.csv", check.names = FALSE)
  
UCSC_clean = UCSC %>% 
  mutate(Prerequisites = str_extract(Prerequisites,
                                  "Prerequisites?\\(s\\): ?.*?(?:\\.|$)|Prerequisites: ?.*?(?:\\.|$)"),
         Prerequisites = gsub("Prerequisites?\\(s\\): ?|Prerequisites: ?|\\.", "", Prerequisites),
         Prerequisites = ifelse(grepl("Enrollment is", Prerequisites), NA, Prerequisites),
         
         formerly = str_extract(Description, 
                                "\\(Formerly,? [^\\)]+\\)|Formerly [^\\)]+\\)?|\\([^)]*formerly[^)]*\\)"),
         formerly = gsub("\\(Formerly,? |\\.\\)|Formerly |\\.|\\(|\\)", "", formerly),
         Description = gsub("\\(Formerly,? [^\\)]+\\)|Formerly [^\\)]+\\)?|\\([^)]*formerly[^)]*\\)?", 
                            "", Description),
         
         cannot_credit = str_extract(Description, 
                               "Students cannot receive credit for (both )?[^\\.]*\\."),
         cannot_credit = gsub("Students cannot receive credit for (both )?|\\.", 
                              "", cannot_credit),
         cannot_credit = gsub("courses|this courses? and |for |this course after they have completed |this course after receiving credit for |this course if they have already received credit |this course if they have previously received credit ", 
                              "", cannot_credit),
         Description = gsub("Students cannot receive credit for (both )?[^\\.]*\\.", 
                            "", Description),
         
         may_be = str_extract(Description, "May be[^\\.]+\\."),
         Description = gsub("May be[^\\.]+\\.", "", Description),
         
         prerequisties_des = str_extract(Description, "Prerequisites?\\(s\\): ?[^\\.]*\\.|Prerequisite: ?[^\\.]*\\."),
         prerequisties_des = gsub("Prerequisites?\\(s\\): ?|Prerequisite: ?|\\.", "", prerequisties_des),
         Description = gsub("Prerequisite\\(s\\): ?[^\\.]*\\.|Prerequisite: ?[^\\.]*\\.", "", Description),
         
         Prerequisites = coalesce(Prerequisites, prerequisties_des),
         
         enrollment = str_extract(Description, "Enrollment[^\\.]+\\."),
         Description = gsub("Enrollment[^\\.]+\\.", "", Description),
         
         Cross_Listing = str_extract(Description, "\\(?Also offered[^\\.]+\\. ?\\)?"),
         Cross_Listing = gsub("\\(?Also offered as |\\.|\\)", "", Cross_Listing),
         Description = gsub("\\(?Also offered[^\\.]+\\. ?\\)?", "", Description)) %>% 
  select(-prerequisties_des)

#write.csv(UCSC_clean, "./Cleaned/ucsc_courses_catalog_CLEAN.csv", row.names = FALSE, 
       #   fileEncoding = "UTF-8", na = "")

## final dataset ----
UCD_short = UCD_clean %>% 
  filter(grepl("^0|^1", Course_Code)) %>% 
  mutate(Campus = "UCD",
         Units_Min = as.character(Units_Min),
         Units_Max = as.character(Units_Max)) %>%
  select(Campus,
         Subject, Subject_Code, Course_Code, Title, `Course Description`, 
         `Prerequisite(s)`, Units_Min, Units_Max, `Cross Listing`)

UCLA_short = UCLA_clean %>% 
  filter(crs_career_lvl_nm != "Graduate Courses") %>% 
  mutate(Campus = "UCLA",
         unt_min = as.character(unt_min),
         unt_max = as.character(unt_max)) %>% 
  select(Campus,
         subj_area_nm, subj_area_cd, course_number, course_title, crs_desc, 
         requisites, unt_min, unt_max, same_as)
names(UCLA_short) = names(UCD_short)

UCI_short = UCI_clean %>% 
  filter(!grepl("([A-Z]+)?2[0-9]{2}([A-Z]+)?", course_code)) %>% 
  mutate(Campus = "UCI",
         units_min = as.character(units_min),
         units_max = as.character(units_max)) %>% 
  select(Campus,
         subject_name, subject_code, course_code, title, description, 
         prerequisites, units_min, units_max)
names(UCI_short) = names(UCD_short[-ncol(UCD_short)])

UCSC_short = UCSC_clean %>% 
  filter(!grepl("([A-Z]+)?2[0-9]{2}([A-Z]+)?", `Course Name`)) %>% 
  mutate(Units_Min = as.character(Units_Min),
         Units_Max = as.character(Units_Max)) %>%
  select(Campus, Subject_Name, Subject, `Course Name`, Course_Title, Description,
         Prerequisites, Units_Min, Units_Max, Cross_Listing)
names(UCSC_short) = names(UCD_short)

combined = bind_rows(UCD_short, UCLA_short, UCI_short, UCSC_short)
combined = combined %>%
  mutate(across(everything(), ~na_if(., "")),
         Units_Min = as.numeric(Units_Min),
         Units_Max = as.numeric(Units_Max)) %>% 
  distinct()

write.csv(combined, "./Cleaned/combined_CLEAN.csv", row.names = FALSE, 
          fileEncoding = "UTF-8", na = "")

## only include classes w/ min units
combined_filtered = combined %>% 
  filter(Units_Min <= 2)
  
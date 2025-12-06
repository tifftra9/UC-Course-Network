start = function(url = "https://catalog.ucdavis.edu/courses-subject-code/"){
  lines = readLines(url)
  page = htmlParse(lines)
  
  subjects = getSubjects(page)
  courses = lapply(names(subjects), getCourses)
}


getSubjects = function(page){
  # get nodes with title attributes
  nodes = getNodeSet(page, "//a[starts-with(@href, '/courses-subject-code/')]")
  subjects = sapply(nodes, xmlValue)
  
  # remove first and last "subjects" as they are not actually subjects
  subjects = subjects[-c(1, length(subjects))]
  
  # get subject codes and titles
  subj_codes = str_extract(subjects, "\\([A-Z]{3}\\)") 
  subj_codes = gsub("\\(|\\)", "", subj_codes)
  subj_titles = gsub("\\([A-Z]{3}\\)", "", subjects) %>% 
    trimws()
  names(subj_titles) = subj_codes
  
  subj_titles
}

getCourses = function(subj_code, url = "https://catalog.ucdavis.edu/courses-subject-code/"){
  # access subject link
  subj_url = paste0(url, tolower(subj_code), "/")
  subj_lines = readLines(subj_url)
  subj_page = htmlParse(subj_lines)
  
  # obtain all the courses of a subject 
  course_nodes = getNodeSet(subj_page, "//div[@class = 'courseblock']")
  
  # obtain all info from /b and /div
  bold = getBoldInfo(course_nodes)
  div = getDivInfo(course_nodes)
  
  courses_df = cbind(bold, div)
}

getBoldInfo = function(course_nodes){
  # extract bolded information from h3 -> df
  bold = sapply(course_nodes, function(x) xpathSApply(x, ".//h3//b", xmlValue))
  if (length(bold) == 0) {
    return(data.frame())
  }
  bold = as.data.frame(t(bold))
  colnames(bold) = c("Code", "Title", "Units")
  cleanBold(bold)
}

cleanBold = function(bold){
  bold = bold %>% 
    mutate(Title = gsub("—\u00A0", "", Title),
           Units = gsub("\\(|\\)", "", Units))
}

getDivInfo = function(course_nodes){
  # extract text from div -> df
  # extra information held in third column -> split into multiple columns
  div_list = lapply(course_nodes, function(x) trimws(xpathSApply(x, ".//div", xmlValue)))
  if (length(div_list) == 0) {
    return(data.frame())
  }
  div_matrix = sapply(div_list, function(x) {
    length(x) = max(max(lengths(div_list)), 4)
    x})  
  div_df = as.data.frame(t(div_matrix)) # transpose and remove redundant info
  div_df = div_df %>% 
    mutate(last_non_na = apply(., 1, function(row) tail(na.omit(row), 1)),
           V4 = ifelse(grepl("^This|^Starting", V2), last_non_na, V4),
           V2 = ifelse(grepl("^This|^Starting", V2), NA, V2),
           V4 = str_replace(V4, ".*?(Course Description:)", "\\1"), # remove anything before
           V4 = str_replace(V4, "\\.\\s*(?=This course version)",
                            "\\.\n")) %>% 
  select(1:min(8, ncol(.)))
  div_df = separate_wider_delim(div_df, cols = 4, delim = "\n", 
                                names_sep = "_", too_few = "align_start")
  
  # extract variable names from "Variable: text" format 
  names = str_extract_all(unlist(div_df[, -1]), "^([^:]*)") %>% 
    unlist() %>% 
    trimws() %>% 
    unique()
  names = names[!is.na(names)] # remove NAs
  
  # after split, some entries are "out of order" and are not in the correct columns
    # unlist them, then sort them based on what variable they start with
  div_unlist = apply(div_df, 1, as.list) %>% 
    lapply(function(course) unlist(course)) # unlist into one vector per course
  div = lapply(div_unlist, function(course) # for each course
    sapply(names, function(name){ # for each variable name
      m = grep(paste0("^", str_escape(name)), course, value = TRUE) # select the element that starts
      m = ifelse(length(m) == 0, NA, m) # if nothing is selected, return NA
      gsub(paste0("^", str_escape(name), ":\\s"), "", m)})) # clean out "Variable: " parts
  
  # combine into dataframe
  div = as.data.frame(do.call(rbind, div), stringsAsFactors = FALSE, check.names = FALSE)
  cleanDiv(div)
}

cleanDiv = function(div){
  div = lapply(div, trimws)
  div = as.data.frame(div, stringsAsFactors = FALSE, check.names = FALSE)
  
  div[div == ""] = NA
  div = div %>% select(where(~ any(!is.na(.))))
}
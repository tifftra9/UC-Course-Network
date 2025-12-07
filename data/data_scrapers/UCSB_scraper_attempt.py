import requests
import json
import csv
import os

headers = {
    'authority': 'app.coursedog.com',
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'zh-CN,zh;q=0.9',
    'content-type': 'application/json',
    'origin': 'https://catalog.ucsb.edu',
    'referer': 'https://catalog.ucsb.edu/courses?cq=&page=2',
    'sec-ch-ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'cross-site',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.95 Safari/537.36',
    'x-requested-with': 'catalog',
}
def search(skip=0):
    params = {
        'catalogId': 'mZXlGvYb30h2fSq3aYLn',
        'skip': str(skip),  # 将skip转换为字符串
        'limit': '20',
        'orderBy': 'code',
        'formatDependents': 'false',
        'effectiveDatesRange': '2026-03-30,2026-03-30',
        'ignoreEffectiveDating': 'false',
        'columns': 'customFields.rawCourseId,customFields.crseOfferNbr,customFields.catalogAttributes,customFields.advisorEnrollmentComments,customFields.generalSubjectAreas,customFields.specialSubjectAreas,customFields.universityRequirements,customFields.repeatComments,displayName,department,description,name,courseNumber,subjectCode,code,courseGroupId,career,college,longName,status,institution,institutionId,credits,requisites',
    }

    json_data = {
        'condition': 'AND',
        'filters': [
            {
                'filters': [
                    {
                        'id': 'description-course',
                        'condition': 'field',
                        'name': 'description',
                        'inputType': 'text',
                        'group': 'course',
                        'type': 'isNotEmpty',
                    },
                    {
                        'id': 'startTerm-course',
                        'condition': 'field',
                        'name': 'startTerm',
                        'inputType': 'text',
                        'group': 'course',
                        'type': 'isNotEmpty',
                    },
                    {
                        'id': 'HiPz3-course',
                        'condition': 'field',
                        'name': 'HiPz3',
                        'inputType': 'boolean',
                        'group': 'course',
                        'type': 'isNot',
                        'value': True,
                        'customField': True,
                    },
                ],
                'id': 'HXkaROAK',
                'condition': 'and',
            },
        ],
    }

    response = requests.post(
        'https://app.coursedog.com/api/v1/cm/ucsb/courses/search/%24filters',
        params=params,
        headers=headers,
        json=json_data,
    ).json()
    # 返回
    return response
def attributeMappings(fieldName):
    # 使用正确的字段名
    params = {
        'school': 'ucsb',
        'fieldName': fieldName,
        'type': 'courses',
    }

    try:
        response = requests.get('https://app.coursedog.com/api/v1/ucsb/integration/attributeMappings', params=params, headers=headers, timeout=10).json()
        return response
    except Exception as e:
        print(f"请求 {fieldName} 时出错: {e}")
        return {}

def process_general_subject_areas(generalSubjectAreas, general_res):
    """处理generalSubjectAreas，返回逗号分隔的描述字符串"""
    result_list = []
    for i in range(len(generalSubjectAreas)):
        target_code = generalSubjectAreas[i]
        # 遍历res字典查找匹配的code
        for key, value in general_res.items():
            if isinstance(value, dict) and value.get("code") == target_code:
                result_list.append(value.get('description', '无描述'))
                break
        else:
            result_list.append(f"未找到{target_code}的匹配项")
    
    # 返回逗号分隔的字符串，末尾不带逗号
    return ",".join(result_list)

def process_special_subject_areas(specialSubjectAreas, special_res):
    """处理specialSubjectAreas，返回逗号分隔的描述字符串"""
    result_list = []
    for i in range(len(specialSubjectAreas)):
        target_code = specialSubjectAreas[i]
        # 遍历res字典查找匹配的code
        for key, value in special_res.items():
            if isinstance(value, dict) and value.get("code") == target_code:
                result_list.append(value.get('description', '无描述'))
                break
        else:
            result_list.append(f"未找到{target_code}的匹配项")
    
    # 返回逗号分隔的字符串，末尾不带逗号
    return ",".join(result_list)

def write_to_csv(data, filename='courses_data.csv'):
    """将数据写入CSV文件"""
    # 定义CSV文件的列名
    fieldnames = ['code', 'globalCourseTitle', 'longName', 'Units_Fixed', 'description', 'General Subject Areas', 'Special Subject Areas']
    
    # 检查文件是否存在，如果不存在则写入表头
    file_exists = os.path.isfile(filename)
    
    with open(filename, mode='a', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        # 如果文件不存在，写入表头
        if not file_exists:
            writer.writeheader()
        
        # 写入数据行
        writer.writerow(data)

if __name__ == '__main__':
    # 删除已存在的CSV文件
    if os.path.exists('courses_data.csv'):
        os.remove('courses_data.csv')
    
    # 获取学科领域映射数据
    general_res = attributeMappings("gEGeneralSubjectAreas")
    special_res = attributeMappings("gESpecialSubjectAreas")
    
    # 分页获取所有数据
    skip =1600
    limit = 20
    total_processed = 0
    
    while True:
        print(f"正在获取数据，skip: {skip}")
        response = search(skip)
        data_list = response.get('data', [])
        
        # 如果没有数据了，跳出循环
        if not data_list:
            print("没有更多数据了，结束循环")
            break
            
        print(f"获取到 {len(data_list)} 条数据")
        
        # 处理当前页的数据
        for d in data_list:
            code = d['code']
            globalCourseTitle = d.get("globalCourseTitle", "")
            longName = d.get("longName", "")
            Units_Fixed = d["credits"]["creditHours"].get("min", "") if "credits" in d and "creditHours" in d["credits"] else ""
            description = d.get("description", "")
            generalSubjectAreas = d["customFields"].get("generalSubjectAreas", [])
            specialSubjectAreas = d["customFields"].get("specialSubjectAreas", [])

            # 处理generalSubjectAreas和specialSubjectAreas并获取描述字符串
            general_descriptions = ""
            special_descriptions = ""
            
            if len(generalSubjectAreas) > 0:
                general_descriptions = process_general_subject_areas(generalSubjectAreas, general_res)
        
            if len(specialSubjectAreas) > 0:
                special_descriptions = process_special_subject_areas(specialSubjectAreas, special_res)
                
            # 准备写入CSV的数据
            csv_data = {
                'code': code,
                'globalCourseTitle': globalCourseTitle,
                'longName': longName,
                'Units_Fixed': Units_Fixed,
                'description': description,
                'General Subject Areas': general_descriptions,
                'Special Subject Areas': special_descriptions
            }
            
            # 写入CSV文件
            write_to_csv(csv_data)
            
        # 更新计数器和skip值
        total_processed += len(data_list)
        skip += limit
        
        # 如果当前页数据少于limit，说明已经是最后一页了
        if len(data_list) < limit:
            print("已到达最后一页，结束循环")
            break
    
    print(f"总共处理了 {total_processed} 条课程数据，并已写入到 courses_data.csv 文件中。")
import requests
import json
import os
from dotenv import load_dotenv
import logging
import shutil
from datetime import datetime

# 加载环境变量
load_dotenv()

# 在文件开头设置日志级别
logging.basicConfig(level=logging.DEBUG)

# 飞书应用的 App ID 和 App Secret
APP_ID = os.getenv("FEISHU_APP_ID")
APP_SECRET = os.getenv("FEISHU_APP_SECRET")
GPT4_API_KEY = os.getenv("GPT4_API_KEY")
BITABLE_APP_TOKEN = os.getenv("BITABLE_APP_TOKEN")
TABLE_ID = os.getenv("TABLE_ID")

# 添加新的常量
NEW_ACCOUNT_FILE = "new_account.txt"
ARCHIVE_FOLDER = "archived_accounts"

def get_tenant_access_token():
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    data = {
        "app_id": APP_ID,
        "app_secret": APP_SECRET
    }
    
    response = requests.post(url, headers=headers, data=json.dumps(data))
    
    if response.status_code == 200:
        return response.json().get("tenant_access_token")
    else:
        print(f"获取 token 失败: {response.text}")
        return None

def parse_text_with_gpt4(text):
    url = "https://api.openai-next.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GPT4_API_KEY}",
        "Content-Type": "application/json"
    }
    system_prompt = '''
    你是一个专门解析文本的AI助手。请将给定的文本解析为JSON格式，包含以下字段：登录说明、账号信息、产品。其中账号信息应该是一个数组，每个元素对应一行账号信息。例如
    Cursor:

"谷歌登录 账号-密码-辅助邮箱"
"KatharinaNijazi144@gmail.com----passwordxxx----McdonalFeagin322@pmail.1s.fr"
Bolt:

"会员-账号（-辅助邮箱）"
"ShahrourLolo641@gmail.com----passwordxxx----caguewilliaq@hotmail.com"
V0:

"邮箱验证码登录 账号-密码"
"atoubaboily@hotmail.com----passwordxxxx"
Reweb:

"账号-密码"
"csengakye@hotmail.com----passwordxxxx"
    目标数据结构如下,账号信息需要是多行，产品、登录说明 需要冗余：
    ```
    {
    "records": [
        {
            "fields": {
                "产品": "Cursor",
                "登录说明": "谷歌登录 账号-密码-辅助邮箱",
                "账号信息": "KatharinaNijazi144@gmail.com----passwordxxx----McdonalFeagin322@pmail.1s.fr"
            }
        },
        {
            "fields": {
                "产品": "Bolt",
                "登录说明": "会员-账号（-辅助邮箱）",
                "账号信息": "ShahrourLolo641@gmail.com----passwordxxx----caguewilliaq@hotmail.com"
            }
        },
        {
            "fields": {
                "产品": "V0",
                "登录说明": "邮箱验证码登录 账号-密码",
                "账号信息": "atoubaboily@hotmail.com----passwordxxx"
            }
        },
        {
            "fields": {
                "产品": "Reweb",
                "登录说明": "账号-密码",
                "账号信息": "csengakye@hotmail.com----passwordxxx"
            }
        }
    ]
    }
    ```
    要求：返回的结果只能是 JSON 数据，不能有其他非 JSON 字符，例如不要有 "```json"
    '''
    data = {
        "model": "gpt-4o",
        "messages": [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": f"{text}"
            }
        ],
        "temperature": 0.7
    }
    
    response = requests.post(url, headers=headers, json=data)
    logging.debug(f"GPT-4 API 响应状态码: {response.status_code}")
    logging.debug(f"GPT-4 API 响应头: {response.headers}")
    
    if response.status_code == 200:
        response_json = response.json()
        logging.debug(f"GPT-4 API 完整响应: {response_json}")
        
        parsed_content = response_json["choices"][0]["message"]["content"]
        logging.info(f"GPT-4 返回的内容: {parsed_content}")
        
        try:
            parsed_data = json.loads(parsed_content)
            # 确保"产品"字段是一个字符串
            if "产品" in parsed_data and isinstance(parsed_data["产品"], list):
                parsed_data["产品"] = parsed_data["产品"][0] if parsed_data["产品"] else ""
            return parsed_data
        except json.JSONDecodeError as e:
            logging.error(f"JSON 解析错误: {e}")
            logging.error(f"GPT-4 返回的内容不是有效的 JSON 格式: {parsed_content}")
            return None
    else:
        logging.error(f"GPT-4 API 调用失败: {response.text}")
        return None

def read_new_account_file():
    if not os.path.exists(NEW_ACCOUNT_FILE):
        logging.error(f"文件 {NEW_ACCOUNT_FILE} 不存在")
        return None
    
    with open(NEW_ACCOUNT_FILE, 'r', encoding='utf-8') as file:
        content = file.read()
    return content

def archive_file_content():
    if not os.path.exists(ARCHIVE_FOLDER):
        os.makedirs(ARCHIVE_FOLDER)
    
    if os.path.exists(NEW_ACCOUNT_FILE):
        try:
            with open(NEW_ACCOUNT_FILE, 'r', encoding='utf-8') as file:
                content = file.read()
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_filename = f"account_{timestamp}.txt"
            archive_path = os.path.join(ARCHIVE_FOLDER, archive_filename)
            
            with open(archive_path, 'w', encoding='utf-8') as archive_file:
                archive_file.write(content)
            
            logging.info(f"文件内容已归档: {archive_path}")
        except IOError as e:
            logging.error(f"归档文件内容时发生错误: {e}")
    else:
        logging.warning(f"文件 {NEW_ACCOUNT_FILE} 不存在，无法归档")

def clear_file_content():
    if os.path.exists(NEW_ACCOUNT_FILE):
        try:
            archive_file_content()  # 先归档文件内容
            with open(NEW_ACCOUNT_FILE, 'w', encoding='utf-8') as file:
                file.write('')
            logging.info(f"文件 {NEW_ACCOUNT_FILE} 内容已清空")
        except IOError as e:
            logging.error(f"清空文件 {NEW_ACCOUNT_FILE} 时发生错误: {e}")
    else:
        logging.warning(f"文件 {NEW_ACCOUNT_FILE} 不存在，无需清空")

def add_records_to_bitable(token, parsed_data):
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{BITABLE_APP_TOKEN}/tables/{TABLE_ID}/records/batch_create"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    if not parsed_data or "records" not in parsed_data or not parsed_data["records"]:
        logging.error("没有有效的记录可以添加到 Bitable")
        return False
    
    data = {"records": parsed_data["records"]}
    
    logging.info(f"正在向 Bitable 添加记录，URL: {url}")
    logging.debug(f"请求头: {headers}")
    logging.debug(f"请求数据: {data}")
    
    response = requests.post(url, headers=headers, json=data)
    logging.info(f"Bitable API 响应状态码: {response.status_code}")
    
    if response.status_code == 200:
        logging.info("成功添加记录到 Bitable")
        logging.debug(f"Bitable API 响应: {response.json()}")
        return True
    else:
        response_json = response.json()
        logging.error(f"添加记录失败: {response_json}")
        logging.error(f"BITABLE_APP_TOKEN: {BITABLE_APP_TOKEN}")
        logging.error(f"TABLE_ID: {TABLE_ID}")
        
        if response_json.get('code') == 1254062:
            logging.error("单选字段转换失败，需要人工检查")
        return False

def main():
    token = get_tenant_access_token()
    if token:
        logging.info(f"成功获取 token: {token}")
        
        content = read_new_account_file()
        if content is None:
            return
        
        parsed_data = parse_text_with_gpt4(content)
        
        if parsed_data:
            success = add_records_to_bitable(token, parsed_data)
            if success:
                clear_file_content()  # 这个函数现在会先归档内容，然后清空文件
            else:
                logging.error("添加记录失败，文件内容未清空和归档")
        else:
            logging.error("无法解析文本，跳过添加记录到 Bitable")

if __name__ == "__main__":
    main()

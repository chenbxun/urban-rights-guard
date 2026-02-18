import os
import json
from PIL import Image, ImageDraw, ImageFont # 核心画图库
import random
import re

def load_json(dir: str, filename: str):
    file_path = os.path.join(dir, filename)
    if not os.path.exists(file_path):
        return []
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

# 格式: { "uuid_string": "XY7Z", ... }
CAPTCHA_STORE = {}

# --- 辅助函数：生成随机验证码图片 ---
def create_captcha_image(text):
    """画一张带干扰线和噪点的验证码"""
    width, height = 120, 50
    # 1. 创建灰色背景图片 (RGB颜色: 230, 230, 230)
    image = Image.new('RGB', (width, height), (230, 230, 230))
    draw = ImageDraw.Draw(image)

    # 2. 尝试加载字体 (如果找不到就用默认的)
    try:
        # Windows 常用字体路径，Mac/Linux 可能不同
        font = ImageFont.truetype("arial.ttf", 36)
    except:
        font = ImageFont.load_default()

    # 3. 画干扰线 (随机画 5 条)
    for _ in range(5):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = random.randint(0, width)
        y2 = random.randint(0, height)
        draw.line(((x1, y1), (x2, y2)), fill=(150, 150, 150), width=2)

    # 4. 画噪点 (随机画 50 个点)
    for _ in range(50):
        xy = (random.randint(0, width), random.randint(0, height))
        draw.point(xy, fill=(100, 100, 100))

    # 5. 画文字 (居中大概位置)
    # 计算文字宽高有点麻烦，Demo 直接凭感觉偏移一下
    draw.text((20, 5), text, font=font, fill=(50, 50, 50))

    return image

def set_captcha(uid: str, text: str):
    """保存验证码"""
    CAPTCHA_STORE[uid] = text

def get_captcha(uid: str):
    """获取验证码"""
    return CAPTCHA_STORE.get(uid)

def delete_captcha(uid: str):
    """删除验证码"""
    del CAPTCHA_STORE[uid]

def traverse_captcha():
    """遍历验证码"""
    print("traverse captcha:")
    for uid, text in CAPTCHA_STORE.items():
        print(f"{uid}: {text}")

def save_json_append(data, dir: str, filename: str):
    file_path = os.path.join(dir, filename)
    # 如果文件不存在，先建个空的
    if not os.path.exists(file_path):
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump([], f)
    
    # 读取旧数据
    with open(file_path, "r", encoding="utf-8") as f:
        submissions = json.load(f)
    
    # 追加新数据
    submissions.append(data)
    
    # 写入
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(submissions, f, ensure_ascii=False, indent=4)

def remove_html_tags(text):
    """把 HTML 字符串转为纯文本"""
    clean = re.compile('<.*?>')
    return re.sub(clean, '', text)

# 生成智能摘要
def generate_smart_snippet(content_html, keyword, length=100):
    """
    从 HTML 内容中提取包含 keyword 的纯文本片段。
    如果没找到 keyword，就返回开头的内容。
    """
    # 转纯文本
    plain_text = remove_html_tags(content_html)
    # print(plain_text)
    # 去除多余的空行和空格，让摘要更紧凑
    plain_text = re.sub(r'\s+', ' ', plain_text).strip()
    # print(plain_text)

    if not keyword:
        return plain_text[:length] + "..." if length != -1 else plain_text

    # 查找关键词位置 (忽略大小写)
    idx = plain_text.lower().find(keyword.lower())

    if idx != -1:
        # 截取：关键词前面留 20 字，后面留 80 字
        start = max(0, idx - 20)
        end = min(len(plain_text), idx + 80)
        snippet = plain_text[start:end]
        return "..." + snippet + "..."
    else:
        # 如果关键词只在标题里出现，正文里没找到，就返回正文开头
        return plain_text[:length] + "..."
import os
import json
import re
import pdfplumber

SOURCE_ROOT = '../案例' 
# 输出HTML目录
OUTPUT_HTML_DIR = 'data/cases_content'
# 输出JSON路径
OUTPUT_JSON_PATH = 'data/cases.json'

# 正则表达式预编译
NOISE_PATTERN = re.compile(r'^\s*(第\s*\d+\s*页|人民法院.*例库)\s*$')
# 匹配案号：2024-16-2-092-001 (4位-2位-1位-3位-3位)
CASE_NO_PATTERN = re.compile(r'(\d{4}-\d{1,2}-\d-\d{3}-\d{3})')
# 匹配关键词行
KEYWORDS_PATTERN = re.compile(r'^\s*关键词[:\s](.*)')
# 匹配正文四大板块标题
SECTION_HEADERS = ['基本案情', '裁判理由', '执行理由', '裁判要旨', '执行要旨', '关联索引']

def clean_text(text):
    """清洗PDF提取的文本，去除页眉页脚噪音"""
    lines = []
    for line in text.split('\n'):
        # 去除首尾空白
        stripped = line.strip()
        if not stripped:
            continue
        # 如果不是噪音行，则保留
        if not NOISE_PATTERN.match(stripped):
            lines.append(stripped)
    return lines

def parse_pdf_content(file_path):
    """
    解析PDF，分离元数据和正文
    返回: (metadata_dict, html_content_string)
    """
    try:
        with pdfplumber.open(file_path) as pdf:
            # 拼接所有页面的文本
            raw_text = "\n".join([page.extract_text() or "" for page in pdf.pages])
    except Exception as e:
        print(f"读取PDF失败: {file_path} error: {e}")
        return None, None

    lines = clean_text(raw_text)
    print(lines)
    metadata = {
        "case_no": "",
        "title": "",
        "subtitle": "",
        "keywords": []
    }

    # 辅助变量，用于正文分块
    current_section_title = ""
    sections = {k: [] for k in SECTION_HEADERS}

    for i, line in enumerate(lines):
        if i == 0:
            case_no_match = CASE_NO_PATTERN.search(line)
            assert case_no_match, f"案号匹配失败: {line}"
            metadata['case_no'] = case_no_match.group(1)

        elif i == 1:
            metadata['title'] = line
        
        elif i == 2: 
            metadata['subtitle'] = line

        elif i == 3:
            keywords_match = KEYWORDS_PATTERN.match(line)
            assert keywords_match, f"关键词匹配失败: {line}"
            raw_keys = keywords_match.group(1)
            metadata['keywords'] = [k.strip() for k in raw_keys.split() if k.strip()] 
        
        else:
            # 检查是否是四大标题之一
            # 有时候标题会和正文连在一起，这里做简单匹配
            is_header = False
            for header in SECTION_HEADERS:
                if line.startswith(header):
                    current_section_title = header
                    is_header = True
                    # 如果标题后面紧跟内容（例如：基本案情 原告...），需要把内容切出来
                    content_part = line[len(header):].strip()
                    assert not content_part, f"标题后面紧跟内容：{line}"
                    break
            
            if not is_header:
                assert current_section_title, f"未知标题: {line}"
                sections[current_section_title].append(line)

    # --- 2. 生成 HTML ---
    html_parts = []
    html_parts.append('<div class="law-content">')
    
    # 遍历四大板块生成内容
    for header in SECTION_HEADERS:
        content_list = sections.get(header, [])
        if content_list:
            html_parts.append(f'<h3 class="section-title">{header}</h3>')
            for p in content_list:
                html_parts.append(f'<p>{p}</p>')
    html_parts.append('</div>')

    return metadata, "\n".join(html_parts)

def main():
    if not os.path.exists(OUTPUT_HTML_DIR):
        os.makedirs(OUTPUT_HTML_DIR)
        print(f"已创建输出目录: {OUTPUT_HTML_DIR}")
    
    if not os.path.exists(SOURCE_ROOT):
        print(f"错误：源目录 {SOURCE_ROOT} 不存在。请创建该目录并按类别存放PDF文件夹。")
        return

    # 最终的JSON结构: { "民事案例": [list of cases], "刑事案例": [...] }
    final_data = {}

    # 遍历类别文件夹
    for category in os.listdir(SOURCE_ROOT):
        category_path = os.path.join(SOURCE_ROOT, category)
        if not os.path.isdir(category_path):
            continue
        
        print(f"正在处理分类: {category} ...")
        final_data[category] = []
        
        files = [f for f in os.listdir(category_path) if f.lower().endswith('.pdf')]
        
        for file in files:
            file_path = os.path.join(category_path, file)
            print(f"  -> 解析: {file}")
            meta, html_content = parse_pdf_content(file_path)
            if meta and html_content:
                meta['filename'] = file.split('.')[0]
                dir = os.path.join(OUTPUT_HTML_DIR, category)
                if not os.path.exists(dir):
                    os.makedirs(dir)
                    print(f"已创建输出目录: {dir}")
                
                save_html_path = os.path.join(dir, meta['filename'] + ".html")
                with open(save_html_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                
                final_data[category].append(meta)

    with open(OUTPUT_JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, indent=4)
    
    print(f"\n处理完成！")
    print(f"元数据已保存至: {OUTPUT_JSON_PATH}")
    print(f"HTML正文已保存至: {OUTPUT_HTML_DIR}")

if __name__ == "__main__":
    main()
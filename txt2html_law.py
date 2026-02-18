import os
import re

# ================= 配置区域 =================
SOURCE_DIR = '..\\法律法规'  # 源文件目录
OUTPUT_DIR = '.\\data\\laws_html' # 输出文件目录
# ===========================================

# 正则表达式预编译
# 匹配标题：第xxx编、第xxx分编、第xxx章、第xxx节、附则
# 逻辑：以“第”开头，中文数字，以“编/章/节”结尾；或者“附”开头，“则”结尾
HEADER_PATTERN = re.compile(r'^\s*(第[零一二三四五六七八九十百千]+[编章节]|第[零一二三四五六七八九十百千]+分编|附\s*则)')

# 匹配法条：第xxx条
ARTICLE_PATTERN = re.compile(r'^\s*(第[零一二三四五六七八九十百千]+条)')

# 匹配原文中的“目录”二字
TOC_TITLE_PATTERN = re.compile(r'^\s*目\s*录\s*$')

def ensure_dirs():
    if not os.path.exists(SOURCE_DIR):
        os.makedirs(SOURCE_DIR)
        print(f"已创建源目录 '{SOURCE_DIR}'，请将txt文件放入其中。")
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

def get_line_type(text):
    """
    判断单行文本的类型
    返回: 'header' | 'article' | 'text' | 'toc_mark' | 'empty'
    """
    text = text.strip()
    if not text:
        return 'empty'
    
    if TOC_TITLE_PATTERN.match(text):
        return 'toc_mark'

    if HEADER_PATTERN.match(text):
        return 'header'

    if ARTICLE_PATTERN.match(text):
        return 'article'

    return 'text'

def format_body_line(text, line_type):
    """格式化正文行"""
    text = text.strip()
    if line_type == 'article':
        match = ARTICLE_PATTERN.match(text)
        title = match.group(1)
        content = text[len(title):]
        return f"<p><strong>{title}</strong>{content}</p>"
    else:
        return f"<p>{text}</p>"

def convert_file(file_path, file_name):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        try:
            with open(file_path, 'r', encoding='gbk') as f:
                lines = f.readlines()
        except Exception as e:
            print(f"打开文件失败 {file_name}: {e}")
            return

    # 预处理：去除首尾空白
    lines = [line.strip() for line in lines if line.strip()]

    if len(lines) < 3:
        print(f"文件内容过少，跳过: {file_name}")
        return

    # --- 1. 提取文件名和元数据 ---
    doc_title = lines[0]
    meta_html = f"<p>{lines[1]}</p>"

    # --- 2. 划分 目录块 和 正文块 ---
    # 策略：找到第一个 Header，记为 anchor。
    # 从第3行开始扫描，当 anchor 第二次出现时，视为正文开始的边界。
    
    content_lines_start = lines[2:] # 除去标题和元数据的所有行
    
    first_header_str = None
    split_index = -1 # 分割点索引

    # 2.1 寻找第一个 Header (作为定位锚点)
    for i, line in enumerate(content_lines_start):
        if get_line_type(line) == 'header':
            first_header_str = line
            break
    
    # 2.2 寻找锚点的第二次出现位置 (正文起点)
    if first_header_str:
        occurrence = 0
        for i, line in enumerate(content_lines_start):
            if line == first_header_str:
                occurrence += 1
                if occurrence == 2:
                    split_index = i
                    break
    
    # 如果没找到第二次出现（可能没有目录，或者文档结构只有正文），则全部视为正文
    if split_index == -1:
        toc_part_lines = []
        body_part_lines = content_lines_start
    else:
        toc_part_lines = content_lines_start[:split_index]
        body_part_lines = content_lines_start[split_index:]

    # --- 3. 生成 HTML ---
    
    final_html_parts = []
    final_html_parts.append(meta_html)
    final_html_parts.append("")

    # === 生成目录部分 ===
    # 注意：目录部分只提取 Header 类型
    if toc_part_lines:
        final_html_parts.append("<h3>目　　录</h3>")
        toc_counter = 0
        for line in toc_part_lines:
            if get_line_type(line) == 'header':
                toc_counter += 1
                # 对应正文的ID
                link_id = f"chap{toc_counter}"
                final_html_parts.append(f'<p><a href="#{link_id}">{line}</a></p>')
    
    final_html_parts.append("") # 空行

    # === 生成正文部分 ===
    body_header_counter = 0 # 独立计数，确保和目录对应
    
    for line in body_part_lines:
        l_type = get_line_type(line)
        
        if l_type == 'toc_mark':
            continue # 跳过正文中可能残留的“目录”字样（通常不会有，但以防万一）
            
        if l_type == 'header':
            body_header_counter += 1
            # 赋予和目录相同的ID
            curr_id = f"chap{body_header_counter}"
            final_html_parts.append(f'<h3 id="{curr_id}">{line}</h3>')
        
        elif l_type == 'article' or l_type == 'text':
            final_html_parts.append(format_body_line(line, l_type))

    # --- 4. 保存 ---
    result_html = "\n".join(final_html_parts)
    safe_filename = re.sub(r'[\\/*?:"<>|]', "", doc_title)
    output_path = os.path.join(OUTPUT_DIR, safe_filename + ".html")

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(result_html)
    
    print(f"转换成功: {output_path} (检测到 {len(toc_part_lines)} 行目录数据)")

def main():
    ensure_dirs()
    files = [f for f in os.listdir(SOURCE_DIR) if f.lower().endswith('.txt')]
    if not files:
        print(f"'{SOURCE_DIR}' 目录下没有找到 .txt 文件。")
        return
    
    print(f"找到 {len(files)} 个txt文件，开始处理...")
    for filename in files:
        convert_file(os.path.join(SOURCE_DIR, filename), filename)
    print("所有任务完成。")

if __name__ == '__main__':
    main()
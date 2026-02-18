from fastapi import APIRouter, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, FileResponse
import os
import sys
sys.path.append("..")
from utils import load_json, generate_smart_snippet

api_case = APIRouter()
templates = Jinja2Templates(directory="templates")


@api_case.get("/", response_class=HTMLResponse)
async def case_index(request: Request, category: str = "全部"):
    all_cases = load_json("data", "cases.json")
    results = []

    for cg, cases in all_cases.items():
        if category != "全部" and cg != category:
            continue

        for case in cases:
            html_path = os.path.join("data", "cases_html", cg, case['filename'] + ".html")
            with open(html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            case['category'] = cg
            case['summary'] = generate_smart_snippet(html_content, '')
            results.append(case)

    return templates.TemplateResponse("case.html", {
        "request": request,
        "results": results,
        "active_tab": "case",
        "current_category": category,
        "search_query": ""
    })

@api_case.post("/search", response_class=HTMLResponse)
async def case_search(request: Request, keyword: str = Form(...)):
    all_cases = load_json("data", "cases.json")
    scored_results = []
    
    for cg, cases in all_cases.items():
        for case in cases:
            score = 0
            html_path = os.path.join("data", "cases_html", cg, case['filename'] + ".html")
            with open(html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            clean_content = generate_smart_snippet(html_content, '', -1)
            # print(clean_content)
            title = case['title']
            keywords = " ".join(case['keywords'])

            # --- 核心：智能加权算法 ---
            if keyword in title:
                score += 10       # 标题命中，权重最高
            if keyword in keywords:
                score += 5        # 标签/关键词命中，权重次之
            if keyword in clean_content:
                score += 1        # 正文命中，权重最低
            
            if score > 0:
                # 动态生成高亮摘要
                case['summary'] = generate_smart_snippet(html_content, keyword)
                case['score'] = score
                case['category'] = cg
                scored_results.append(case)

    # 按分数从高到低排序 (Lambda表达式)
    scored_results.sort(key=lambda x: x['score'], reverse=True)

    return templates.TemplateResponse("case.html", {
        "request": request,
        "results": scored_results,
        "active_tab": "case",
        "current_category": "搜索结果",
        "search_query": keyword
    })

@api_case.get("/detail/{case_no}", response_class=HTMLResponse)
async def case_detail(request: Request, case_no: str):
    all_cases = load_json("data", "cases.json")
    case = None
    category = None
    for cg, cs in all_cases.items():
        for c in cs:
            if c['case_no'] == case_no:
                case = c
                category = cg
                break
        if case:
            break
    
    if not case:
        return HTMLResponse("案例不存在", status_code=404)
    
    html_path = os.path.join("data", "cases_html", category, case['filename'] + ".html")
    with open(html_path, 'r', encoding='utf-8') as f:
        case['content'] = f.read()

    return templates.TemplateResponse("case_detail.html", {
        "request": request,
        "case": case,
        "active_tab": "case",
        "category": category
    })

@api_case.get("/dl/{category}/{filename}")
async def download_case_pdf(category: str, filename: str):
    file_path = os.path.join("data", "cases_pdf", category, filename + ".pdf")
    if os.path.exists(file_path):
        return FileResponse(
            file_path,
            filename=filename + ".pdf",
            media_type="application/pdf",
        )
    return HTMLResponse("文件不存在", status_code=404)
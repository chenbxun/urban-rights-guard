from fastapi import FastAPI, Request, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import uvicorn
from utils import load_json
from api.mediation import api_mediation
from api.case import api_case
from api.policy import api_policy
import os
from utils import remove_html_tags, generate_smart_snippet

app = FastAPI()

# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")

# 设置模板目录
templates = Jinja2Templates(directory="templates")
    
app.include_router(api_mediation, prefix='/mediation', tags=['纠纷调解接口'])
app.include_router(api_case, prefix='/case', tags=['案例检索接口'])
app.include_router(api_policy, prefix='/policy', tags=['政策公示接口'])

DEFAULT_SUMMARY = "..."

# 首页即法规检索页
@app.get("/", response_class=HTMLResponse)
async def read_search(request: Request):
    current_laws = load_json("data", "laws.json")
    for item in current_laws:
        # 尝试读取对应的 HTML 正文文件
        filename = f"{item['title']}.html"
        file_path = os.path.join("data", "laws_html", filename)
        content_html = ''
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                content_html = f.read()
            item['summary'] = generate_smart_snippet(content_html, '')
        else:
            item['summary'] = DEFAULT_SUMMARY

    return templates.TemplateResponse("search.html", {
        "request": request,
        "results": current_laws,
        "query": "",
        "active_tab": "law"
    })

# 简单的模糊搜索
@app.post("/search", response_class=HTMLResponse)
async def do_search(request: Request, keyword: str = Form(...)):
    current_laws = load_json("data", "laws.json")
    results = []

    for item in current_laws:
        # 尝试读取对应的 HTML 正文文件
        filename = f"{item['title']}.html"
        file_path = os.path.join("data", "laws_html", filename)
        
        content_html = ""
        full_text_for_search = item['title'] # 默认搜索范围至少包含标题

        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                content_html = f.read()
                # 把正文加到搜索范围里
                full_text_for_search += remove_html_tags(content_html)
        
        # 搜索匹配：检查关键词是否在标题或正文中
        if keyword.lower() in full_text_for_search.lower():
            # 动态生成摘要
            # 如果正文有内容，就从正文截取；否则用默认summary字段
            if content_html:
                item['summary'] = generate_smart_snippet(content_html, keyword)
            else:
                item['summary'] = DEFAULT_SUMMARY
            
            results.append(item)

    return templates.TemplateResponse("search.html", {
        "request": request,
        "results": results,
        "query": keyword,
        "active_tab": "law"
    })

@app.get("/law/{law_id}", response_class=HTMLResponse)
async def read_law_detail(request: Request, law_id: int):
    current_laws = load_json("data", "laws.json")
    law = next((item for item in current_laws if item["id"] == law_id), None)
    if law:
        content_path = os.path.join("data", "laws_html", f"{law["title"]}.html")
        if os.path.exists(content_path):
            with open(content_path, "r", encoding="utf-8") as f:
                law["content"] = f.read() # 把文件内容读出来，塞给 law 对象
        else:
            law["content"] = "<p>暂无详细内容，或文件丢失。</p>"

        return templates.TemplateResponse("detail.html", {
            "request": request,
            "law": law,
            "active_tab": "law"
        })
    else:
        return HTMLResponse(content="找不到该法规", status_code=404)
 
if __name__ == "__main__":
    # 启动命令：python main.py
    uvicorn.run(app, host="127.0.0.1", port=8080)
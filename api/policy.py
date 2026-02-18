from fastapi import Request, APIRouter
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, FileResponse
import os
import sys
sys.path.append("..")
from utils import load_json

#实例化子路由对象
api_policy = APIRouter()

# 设置模板目录
templates = Jinja2Templates(directory="templates")

# 政策列表页
@api_policy.get("/", response_class=HTMLResponse)
async def read_policies(request: Request, region: str = "武汉"):
    policies = load_json("data", "policies.json")
    current_list = policies.get(region, [])
    return templates.TemplateResponse("policy.html", {
        "request": request,
        "results": current_list,
        "active_tab": "policy",
        "current_region": region
    })

# 政策文件下载/阅读接口
@api_policy.get("/{region}/{filename}")
async def download_policy(region: str, filename: str):
    # 路径安全检查，防止路径穿越攻击
    if ".." in filename or filename.startswith("/"):
        return HTMLResponse("非法请求", status_code=400)
    
    file_path = os.path.join("data", "policies_word", region, filename)
    # print(file_path)
    if os.path.exists(file_path):
        # 浏览器碰到 .doc/.docx 默认会触发下载
        return FileResponse(
            file_path, 
            filename=filename, 
            media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
    return HTMLResponse("文件不存在", status_code=404)

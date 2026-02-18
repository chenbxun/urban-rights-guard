from fastapi import Request, UploadFile, APIRouter, Form, File
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse
import os
import shutil
import uuid
from datetime import datetime
from typing import List
import string
import io
import random
import sys 
sys.path.append("..")
from utils import load_json, save_json_append, create_captcha_image, set_captcha, get_captcha, delete_captcha, traverse_captcha

#实例化子路由对象
api_mediation = APIRouter()

# 设置模板目录
templates = Jinja2Templates(directory="templates")

@api_mediation.get("/", response_class=HTMLResponse)
async def read_mediation(request: Request):
    mediators = load_json("data", "mediators.json")
    return templates.TemplateResponse("mediation.html", {
        "request": request,
        "mediators": mediators,
        "active_tab": "mediation"
    })

# 渲染预约页面
@api_mediation.get("/book", response_class=HTMLResponse)
async def book_page(request: Request, mediator: str = "专家"):
    # mediator 参数从 URL 问号后面获取，例如 /book?mediator=张三
    return templates.TemplateResponse("mediation_book.html", {
        "request": request,
        "active_tab": "mediation",
        "mediator_name": mediator
    })

# 处理预约提交
@api_mediation.post("/book/submit", response_class=HTMLResponse)
async def book_submit(
    request: Request,
    mediator_name: str = Form(...),
    name: str = Form(...),
    phone: str = Form(...),
    book_date: str = Form(...),
    book_time: str = Form(...),
    note: str = Form(None)
):
    # 这里为了简单，我们直接把预约信息当作一种特殊的 submission 保存
    # 你也可以单独建一个 appointments.json
    appointment_data = {
        "submit_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "target_mediator": mediator_name,
        "name": name,
        "phone": phone,
        "book_date": book_date,
        "book_time": book_time,
        "note": note or "无"
    }
    
    save_json_append(appointment_data, "uploads", "appointments.json")

    return HTMLResponse(f"""
    <script>
        alert("预约成功！\\n专家【{mediator_name}】已收到您的请求，将通过电话 {phone} 与您确认具体时间。");
        window.location.href = "/mediation";
    </script>
    """)

@api_mediation.get("/captcha/{uid}")
async def get_captcha_img(uid: str, old_uid: str = None):
    # print(f"old_uid: {old_uid}")
    # 清理旧验证码
    if old_uid:
        try:
            delete_captcha(old_uid)
        except KeyError:
            # 防止 old_uid 不存在或已被删除时报错
            pass

    # 生成 4 位随机字符 (字母+数字)
    code = ''.join(random.choices(string.ascii_letters + string.digits, k=4))

    # 把答案存进全局字典，方便待会儿验证
    set_captcha(uid, code) # uid 是前端随机生成的 ID，code 是后端随机生成的验证码答案
    # traverse_captcha()
    # 画图
    img = create_captcha_image(code)
    
    # 转成二进制流返回给浏览器
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_byte_arr.seek(0)
    
    return StreamingResponse(img_byte_arr, media_type="image/png")

@api_mediation.get("/apply", response_class=HTMLResponse)
async def mediation_apply(request: Request):
    # 现在不需要传 captchas 列表了，前端自己生成 UID 就行
    return templates.TemplateResponse("mediation_apply.html", {
        "request": request, 
        "active_tab": "mediation"
    })

@api_mediation.post("/submit", response_class=HTMLResponse)
async def mediation_submit(
    request: Request,
    name: str = Form(...),
    gender: str = Form(...),
    phone: str = Form(...),
    secret: str = Form(...),
    address: str = Form(...),
    type: str = Form(...),
    desc: str = Form(...),
    files: List[UploadFile] = File(None),
    captcha_input: str = Form(...), 
    captcha_id: str = Form(...) 
):

    correct_answer = get_captcha(captcha_id)
    delete_captcha(captcha_id)
    if not correct_answer or correct_answer.lower() != captcha_input.lower():
        return HTMLResponse(f"""
        <script>
            alert("验证码错误！");
            history.back();
        </script>
        """)
    
    saved_file_paths = []
    if files:
        for file in files:
            if file.filename:
                safe_filename = f"{uuid.uuid4().hex[:8]}_{file.filename}"
                save_dir = os.path.join("uploads", "evidence")
                if not os.path.exists(save_dir):
                    os.makedirs(save_dir)
                save_path = os.path.join(save_dir, safe_filename)
                with open(save_path, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)
                saved_file_paths.append(save_path)

    submission_data = {
        # "id": uuid.uuid4().hex,
        "submit_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "name": name,
        "gender": gender,
        "phone": phone,
        "is_secret": secret,
        "address": address,
        "dispute_type": type,
        "description": desc,
        "evidence_files": saved_file_paths
    }
    save_json_append(submission_data, "uploads", "submissions.json")

    return HTMLResponse("""
    <script>
        alert("提交成功！您的申请已归档。");
        window.location.href = "/mediation/apply";
    </script>
    """)

@api_mediation.get("/status", response_class=HTMLResponse)
async def mediation_status_page(request: Request):
    return templates.TemplateResponse("mediation_status.html", {
        "request": request,
        "active_tab": "mediation",
        "has_searched": False,
        "query_phone": ""
    })

@api_mediation.post("/status", response_class=HTMLResponse)
async def mediation_status_search(request: Request, phone: str = Form(...)):
    all_submissions = load_json("uploads", "submissions.json")
    
    # 简单的筛选逻辑：按手机号过滤
    results = [s for s in all_submissions if s.get("phone") == phone or s.get("phone") == "+86" + phone]
    
    # 纠纷类型映射（因为存的是 1, 2, 3，显示时最好转成中文）
    type_map = {"1": "合同", "2": "宅基地", "3": "债务", "4": "其他"}
    
    # 处理一下数据，方便前端显示
    for r in results:
        r['dispute_type_text'] = type_map.get(r.get('dispute_type'), "其他")

    # 按时间倒序排列，最新的在前面
    results.reverse()

    return templates.TemplateResponse("mediation_status.html", {
        "request": request,
        "active_tab": "mediation",
        "has_searched": True,     # 标记用户已经点击了搜索
        "results": results,       # 搜索结果列表
        "query_phone": phone      # 回显用户输入的手机号
    })

@api_mediation.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request):
    return templates.TemplateResponse("mediation_upload.html", {
        "request": request,
        "active_tab": "mediation"
    })

@api_mediation.post("/upload/submit", response_class=HTMLResponse)
async def upload_submit(
    request: Request,
    file: UploadFile = File(...), # 必填文件
    captcha_input: str = Form(...), 
    captcha_id: str = Form(...)
):
    # --- 验证码校验逻辑 (复用) ---
    correct_answer = get_captcha(captcha_id)
    delete_captcha(captcha_id) # 验证一次即销毁，防止重放
    
    if not correct_answer or correct_answer.lower() != captcha_input.lower():
        return HTMLResponse(f"""
        <script>
            alert("验证码错误，请重新输入！");
            history.back();
        </script>
        """)
    
    # --- 文件保存逻辑 ---
    if file.filename:
        # 生成安全的文件名，防止文件名冲突
        safe_filename = f"{uuid.uuid4().hex[:8]}_{file.filename}"
        save_dir = os.path.join("uploads", "media")
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        save_path = os.path.join(save_dir, safe_filename)
        
        # 写入文件
        with open(save_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

    return HTMLResponse("""
    <script>
        alert("上传成功！文件已保存到服务器。");
        window.location.href = "/mediation/upload";
    </script>
    """)

# 渲染下载列表页面
@api_mediation.get("/download", response_class=HTMLResponse)
async def download_page(request: Request):
    upload_dir = "uploads/media"
    file_list = []
    
    # 确保文件夹存在
    if os.path.exists(upload_dir):
        # 遍历文件夹
        for filename in os.listdir(upload_dir):
            # 简单的过滤：只显示媒体文件，隐藏 json 和 py 等系统文件
            if filename.lower().endswith(('.mp4', '.mp3', '.wav', '.mov', '.jpg', '.png', '.doc', '.pdf')):
                
                # 获取文件大小 (转为 KB/MB)
                file_path = os.path.join(upload_dir, filename)
                size_bytes = os.path.getsize(file_path)
                if size_bytes < 1024 * 1024:
                    size_str = f"{size_bytes / 1024:.1f} KB"
                else:
                    size_str = f"{size_bytes / (1024 * 1024):.1f} MB"

                file_list.append({
                    "name": filename,
                    "size": size_str
                })
    
    return templates.TemplateResponse("mediation_download.html", {
        "request": request,
        "active_tab": "mediation",
        "files": file_list
    })

# 执行文件下载
@api_mediation.get("/download/{filename}")
async def download_file(filename: str):
    file_path = os.path.join("uploads", "media", filename)
    
    # 安全检查：防止路径遍历攻击 (../)
    if ".." in filename or "/" in filename:
        return HTMLResponse("非法的文件名", status_code=400)

    if os.path.exists(file_path):
        # filename=filename 让浏览器下载时显示原文件名
        return FileResponse(file_path, media_type='application/octet-stream', filename=filename)
    else:
        return HTMLResponse("文件不存在", status_code=404)
    
@api_mediation.get("/hotline", response_class=HTMLResponse)
async def hotline_page(request: Request):
    return templates.TemplateResponse("mediation_hotline.html", {
        "request": request,
        "active_tab": "mediation"
    })
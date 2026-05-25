import os
import json
import logging
import socket
import subprocess
import time
import urllib.request

from flask import Flask, request, jsonify, send_from_directory, Response, stream_with_context
from flask_cors import CORS
from werkzeug.utils import secure_filename

from backend.agent import Agent
from backend.config import client, MODEL
from backend.tools import TOOLS, TOOL_MAP

# ---------- 日志 ----------
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# ---------- 静态文件（前端页面） ----------
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")


@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/index2.html")
def index2():
    return send_from_directory(FRONTEND_DIR, "index2.HTML")


@app.route("/resume.html")
def resume():
    return send_from_directory(FRONTEND_DIR, "resume.html")


@app.route("/job-search.html")
def job_search():
    return send_from_directory(FRONTEND_DIR, "job-search.html")


@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(FRONTEND_DIR, path)


# ---------- 文件上传 ----------
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx'}

# ----- 系统提示词 -----
CHAT_PROMPT = """你是一位就业指导专家，服务对象是在校学生和应届生。
【核心规则】
1. 紧扣问题：回复前先确认你的回答直接回应了用户的问题，不要跑题或发散。
2. 极简输出：每条回复控制在150字以内，用短句、分点列出，不要写长篇大论。
3. 口语化：像同学聊天一样说话，多用"你"，少用书面语和官腔。
4. 给干货：直接给具体建议、步骤、例子，不要铺垫和空话。
5. 如果问题太宽泛，先反问用户一个具体问题来缩小范围，而不是直接写一大段。
使用中文回复。"""

RESUME_PROMPT = """你是一位简历分析师，服务对象是在校学生。用户已上传简历。
【核心规则】
1. 紧扣问题：只回答用户当前问的问题，不要一次性把所有分析都倒出来。
2. 极简输出：每条回复控制在150字以内，用短句分点，每点不超过2行。
3. 给具体建议：比如"把'参与了'改成'负责了'，并加上数据成果"。
4. 口语化：像学长学姐改简历一样说话，直接、友善。
5. 一次只说最重要的1-3个点，不要面面俱到。
使用中文回复。"""

JOB_PROMPT = """你是一位职位搜索与推荐专家，服务对象是在校学生和应届生。
【核心规则】
1. 紧扣问题：先看用户问了什么，只回答那一两个点，不要把所有功能都用上。
2. 极简输出：每条回复控制在150字以内，用短句。搜索结果的每条岗位介绍不超过30字。
3. 岗位推荐直接给：公司名+岗位名+一句话亮点，不要长篇介绍。
4. 口语化：像朋友分享招聘信息一样，轻松直接。
5. 如果用户没说清楚意向行业/岗位，先反问一个具体问题确认方向。
使用中文回复。"""

# ----- Agent 实例 -----
chat_agent = Agent(client=client, model=MODEL, system_prompt=CHAT_PROMPT, tools=TOOLS, tool_map=TOOL_MAP)
resume_agent = Agent(client=client, model=MODEL, system_prompt=RESUME_PROMPT, tools=TOOLS, tool_map=TOOL_MAP)
job_agent = Agent(client=client, model=MODEL, system_prompt=JOB_PROMPT, tools=TOOLS, tool_map=TOOL_MAP)


# ----- 文件文本提取 -----
def extract_text(filepath, filename):
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''

    if ext == 'txt':
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()

    if ext == 'docx':
        from docx import Document
        doc = Document(filepath)
        return '\n'.join(p.text for p in doc.paragraphs if p.text.strip())

    if ext == 'pdf':
        from PyPDF2 import PdfReader
        reader = PdfReader(filepath)
        return '\n'.join(page.extract_text() or '' for page in reader.pages)

    return None


# ----- API 路由 -----
@app.route("/chat", methods=["POST"])
def chat_api():
    data = request.json
    user_message = data.get("message", "").strip()
    if not user_message:
        return jsonify({"error": "消息不能为空"}), 400

    reply = chat_agent.chat(user_message)
    return jsonify({"reply": reply})


@app.route("/resume-chat", methods=["POST"])
def resume_chat():
    data = request.json
    user_message = data.get("message", "").strip()
    if not user_message:
        return jsonify({"error": "消息不能为空"}), 400

    reply = resume_agent.chat(user_message)
    return jsonify({"reply": reply})


@app.route("/job-chat", methods=["POST"])
def job_chat():
    data = request.json
    user_message = data.get("message", "").strip()
    if not user_message:
        return jsonify({"error": "消息不能为空"}), 400

    reply = job_agent.chat(user_message)
    return jsonify({"reply": reply})


@app.route("/upload-resume", methods=["POST"])
def upload_resume():
    if 'file' not in request.files:
        return jsonify({"error": "未找到文件"}), 400

    file = request.files['file']
    original_filename = file.filename
    if not original_filename:
        return jsonify({"error": "文件名为空"}), 400

    ext = original_filename.rsplit('.', 1)[-1].lower() if '.' in original_filename else ''
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({"error": f"不支持的文件格式：.{ext}，仅支持 txt、docx、pdf"}), 400

    filename = secure_filename(original_filename)
    if not filename or filename == original_filename:
        import uuid
        filename = f"{uuid.uuid4().hex}.{ext}"
    else:
        name_part = filename.rsplit('.', 1)[0] if '.' in filename else filename
        if not name_part:
            import uuid
            filename = f"{uuid.uuid4().hex}.{ext}"
        else:
            filename = f"{name_part}.{ext}"

    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    try:
        content = extract_text(filepath, original_filename)
    except Exception as e:
        if os.path.exists(filepath):
            os.remove(filepath)
        return jsonify({"error": f"文件解析失败：{str(e)}"}), 500

    if not content:
        if os.path.exists(filepath):
            os.remove(filepath)
        return jsonify({"error": "无法提取文件内容，文件可能为空"}), 400

    txt_path = filepath.rsplit('.', 1)[0] + '.txt'
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(content)

    from backend.skill.resume_analyzer.resume_analyzer import analyze
    try:
        analysis = analyze(txt_path)
    except Exception as e:
        analysis = {"error": str(e)}

    if os.path.exists(txt_path):
        os.remove(txt_path)
    if os.path.exists(filepath):
        os.remove(filepath)

    resume_agent.history.append({
        "role": "user",
        "content": f"【用户已上传简历，内容如下】\n\n{content}"
    })
    resume_agent.history.append({
        "role": "assistant",
        "content": f"好的，我已收到你的简历。以下是我的初步分析：\n\n{analysis}"
    })

    return jsonify({
        "filename": filename,
        "raw_text": content,
        "analysis": analysis,
    })


# ---------- 历史记录 ----------
def _get_history(agent):
    """提取 agent 历史中的 user 和 assistant 对话"""
    messages = []
    for msg in agent.history:
        if msg["role"] == "system":
            continue
        if msg["role"] == "tool":
            continue
        content = msg.get("content")
        if content and msg["role"] in ("user", "assistant"):
            messages.append({"role": msg["role"], "content": content})
    return messages


@app.route("/chat/history", methods=["GET"])
def chat_history():
    return jsonify({"messages": _get_history(chat_agent)})


@app.route("/resume-chat/history", methods=["GET"])
def resume_chat_history():
    return jsonify({"messages": _get_history(resume_agent)})


@app.route("/job-chat/history", methods=["GET"])
def job_chat_history():
    return jsonify({"messages": _get_history(job_agent)})


# ---------- 流式 API ----------
def _stream_reply(agent, user_message):
    """SSE 流式输出生成器"""
    for chunk in agent.chat_stream(user_message):
        yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"
    yield "data: [DONE]\n\n"


@app.route("/chat/stream", methods=["POST"])
def chat_stream_api():
    data = request.json
    user_message = data.get("message", "").strip()
    if not user_message:
        return jsonify({"error": "消息不能为空"}), 400
    return Response(
        stream_with_context(_stream_reply(chat_agent, user_message)),
        mimetype="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )


@app.route("/resume-chat/stream", methods=["POST"])
def resume_chat_stream_api():
    data = request.json
    user_message = data.get("message", "").strip()
    if not user_message:
        return jsonify({"error": "消息不能为空"}), 400
    return Response(
        stream_with_context(_stream_reply(resume_agent, user_message)),
        mimetype="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )


@app.route("/job-chat/stream", methods=["POST"])
def job_chat_stream_api():
    data = request.json
    user_message = data.get("message", "").strip()
    if not user_message:
        return jsonify({"error": "消息不能为空"}), 400
    return Response(
        stream_with_context(_stream_reply(job_agent, user_message)),
        mimetype="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )


# ---------- cpolar ----------
def get_cpolar_url():
    """通过 cpolar 本地 API 获取公网地址"""
    try:
        req = urllib.request.Request("http://127.0.0.1:4040/api/tunnels")
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode())
            for tunnel in data.get("tunnels", []):
                url = tunnel.get("public_url", "")
                if url and url.startswith("https://"):
                    return url
            for tunnel in data.get("tunnels", []):
                url = tunnel.get("public_url", "")
                if url:
                    return url
            return None
    except Exception:
        return None


def start_cpolar(port):
    """后台启动 cpolar"""
    try:
        if get_cpolar_url():
            logger.info("cpolar 已在运行")
            return True

        subprocess.Popen(
            ["cpolar", "http", str(port)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        for _ in range(10):
            time.sleep(1)
            url = get_cpolar_url()
            if url:
                logger.info(f"cpolar 公网地址: {url}")
                return True
        logger.warning(f"cpolar 启动超时，请手动运行: cpolar http {port}")
        return False
    except FileNotFoundError:
        logger.warning("未找到 cpolar，请先安装: https://www.cpolar.com/")
        return False
    except Exception as e:
        logger.warning(f"启动 cpolar 失败: {e}")
        return False


# ---------- 启动 ----------
if __name__ == "__main__":
    PORT = 5000

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
    finally:
        s.close()

    print("=" * 50)
    logger.info(f"本地访问:    http://127.0.0.1:{PORT}")
    logger.info(f"局域网访问:  http://{local_ip}:{PORT}")

    cpolar_started = start_cpolar(PORT)
    if cpolar_started:
        public_url = get_cpolar_url()
        if public_url:
            logger.info(f"公网访问:    {public_url}")
    else:
        logger.info(f"公网访问:    请手动运行 cpolar http {PORT}")
    print("=" * 50)

    app.run(host="0.0.0.0", port=PORT, debug=True)

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
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "app.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ],
)
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


@app.route("/interview.html")
def interview():
    return send_from_directory(FRONTEND_DIR, "interview.html")


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

【考试查询工具】
- 用户问考研（研究生考试）分数线、国家线、大学复试线、报考人数 → 用 query_kaoyan_scores
- 用户问考研院校信息（大学推荐专业、硕士点、博士点、招生专业目录、考试科目、985/211/双一流）→ 用 query_kaoyan_school
- 用户问国考（公务员考试）分数线、进面分、省份部门分数线、报考人数 → 用 query_guokao_scores
- 提到具体岗位时，顺便输出该岗位对应年份的报考人数
- 用户问考研备考资料（教材推荐、复习方法、备考规划、网课等）或考公备考资料（行测/申论学习方法、面试技巧、选岗建议等）→ 用 query_doubao 查询豆包大模型，然后将其回答重新整理为简洁、口语化、分点列出的干货回复
- 分数线等硬数据用 query_kaoyan_scores / query_guokao_scores，院校信息用 query_kaoyan_school，备考方法等软信息用 query_doubao

使用中文回复。"""

RESUME_PROMPT = """你是一位简历分析师，服务对象是在校学生。用户已上传简历。
【核心规则】
1. 紧扣问题：只回答用户当前问的问题，不要一次性把所有分析都倒出来。
2. 极简输出：每条回复控制在150字以内，用短句分点，每点不超过2行。
3. 给具体建议：比如"把'参与了'改成'负责了'，并加上数据成果"。
4. 口语化：像学长学姐改简历一样说话，直接、友善。
5. 一次只说最重要的1-3个点，不要面面俱到。
使用中文回复。"""

INTERVIEW_PROMPT = """你是一位专业的模拟面试官，服务对象是在校学生和应届生。你的任务是为用户进行模拟面试练习。

【面试流程】
1. 如果用户没有说明自己的专业和目标岗位，必须先问清楚这两点再开始。不要替用户假设专业或岗位
2. 了解用户背景后，开始正式的模拟面试，每次只问一个问题
3. 根据用户的回答，给予简短点评（一句话），然后继续下一个问题
4. 每轮面试问3-5个问题即可，结束时给出总体评价

【核心规则】
1. 一次只问一个问题，不要一次性抛出多个问题
2. 问题要有针对性，根据用户说的岗位方向来问
3. 点评要具体、有建设性，不要只说"回答得不错"
4. 保持专业但友好的面试官语气
5. 总体评价包含：优点、不足、改进建议，每条一句话

使用中文回复。"""

JOB_PROMPT = """你是一位职位搜索与推荐专家，服务对象是在校学生和应届生。
【核心规则】
1. 紧扣问题：先看用户问了什么，只回答那一两个点，不要把所有功能都用上。
2. 极简输出：每条回复控制在150字以内，用短句。搜索结果的每条岗位介绍不超过30字。
3. 岗位推荐直接给：公司名+岗位名+一句话亮点，不要长篇介绍。
4. 口语化：像朋友分享招聘信息一样，轻松直接。
5. 如果用户没说清楚意向行业/岗位，先反问一个具体问题确认方向。

【考试查询工具】
- 用户问考研（研究生考试）分数线、国家线、大学复试线、报考人数 → 用 query_kaoyan_scores
- 用户问考研院校信息（大学推荐专业、硕士点、博士点、招生专业目录、考试科目、985/211/双一流）→ 用 query_kaoyan_school
- 用户问国考（公务员考试）分数线、进面分、省份部门分数线、报考人数 → 用 query_guokao_scores
- 提到具体岗位时，顺便输出该岗位对应年份的报考人数
- 用户问考研备考资料（教材推荐、复习方法、备考规划、网课等）或考公备考资料（行测/申论学习方法、面试技巧、选岗建议等）→ 用 query_doubao 查询豆包大模型，然后将其回答重新整理为简洁、口语化、分点列出的干货回复
- 分数线等硬数据用 query_kaoyan_scores / query_guokao_scores，院校信息用 query_kaoyan_school，备考方法等软信息用 query_doubao

使用中文回复。"""

# ----- 用户隔离的 Agent 实例 -----
user_agents = {}  # {user_id: {"chat": Agent, "resume": Agent, "job": Agent, "interview": Agent}}


def _get_user_id():
    """从请求头获取用户 ID"""
    return request.headers.get("X-User-Id", "anonymous")


def _get_user_agents(user_id):
    """获取或创建某个用户的 Agent 实例"""
    if user_id not in user_agents:
        user_agents[user_id] = {
            "chat": Agent(client=client, model=MODEL, system_prompt=CHAT_PROMPT, tools=TOOLS, tool_map=TOOL_MAP),
            "resume": Agent(client=client, model=MODEL, system_prompt=RESUME_PROMPT, tools=TOOLS, tool_map=TOOL_MAP),
            "job": Agent(client=client, model=MODEL, system_prompt=JOB_PROMPT, tools=TOOLS, tool_map=TOOL_MAP),
            "interview": Agent(client=client, model=MODEL, system_prompt=INTERVIEW_PROMPT, tools=TOOLS, tool_map=TOOL_MAP),
        }
    return user_agents[user_id]


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

    agents = _get_user_agents(_get_user_id())
    reply = agents["chat"].chat(user_message)
    return jsonify({"reply": reply})


@app.route("/resume-chat", methods=["POST"])
def resume_chat():
    data = request.json
    user_message = data.get("message", "").strip()
    if not user_message:
        return jsonify({"error": "消息不能为空"}), 400

    agents = _get_user_agents(_get_user_id())
    reply = agents["resume"].chat(user_message)
    return jsonify({"reply": reply})


@app.route("/job-chat", methods=["POST"])
def job_chat():
    data = request.json
    user_message = data.get("message", "").strip()
    if not user_message:
        return jsonify({"error": "消息不能为空"}), 400

    agents = _get_user_agents(_get_user_id())
    reply = agents["job"].chat(user_message)
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

    agents = _get_user_agents(_get_user_id())
    agents["resume"].history.append({
        "role": "user",
        "content": f"【用户已上传简历，内容如下】\n\n{content}"
    })
    agents["resume"].history.append({
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
    agents = _get_user_agents(_get_user_id())
    return jsonify({"messages": _get_history(agents["chat"])})


@app.route("/resume-chat/history", methods=["GET"])
def resume_chat_history():
    agents = _get_user_agents(_get_user_id())
    return jsonify({"messages": _get_history(agents["resume"])})


@app.route("/job-chat/history", methods=["GET"])
def job_chat_history():
    agents = _get_user_agents(_get_user_id())
    return jsonify({"messages": _get_history(agents["job"])})


@app.route("/interview/history", methods=["GET"])
def interview_history():
    agents = _get_user_agents(_get_user_id())
    return jsonify({"messages": _get_history(agents["interview"])})


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
    agents = _get_user_agents(_get_user_id())
    return Response(
        stream_with_context(_stream_reply(agents["chat"], user_message)),
        mimetype="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )


@app.route("/resume-chat/stream", methods=["POST"])
def resume_chat_stream_api():
    data = request.json
    user_message = data.get("message", "").strip()
    if not user_message:
        return jsonify({"error": "消息不能为空"}), 400
    agents = _get_user_agents(_get_user_id())
    return Response(
        stream_with_context(_stream_reply(agents["resume"], user_message)),
        mimetype="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )


@app.route("/job-chat/stream", methods=["POST"])
def job_chat_stream_api():
    data = request.json
    user_message = data.get("message", "").strip()
    if not user_message:
        return jsonify({"error": "消息不能为空"}), 400
    agents = _get_user_agents(_get_user_id())
    return Response(
        stream_with_context(_stream_reply(agents["job"], user_message)),
        mimetype="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )


@app.route("/interview/stream", methods=["POST"])
def interview_stream_api():
    data = request.json
    user_message = data.get("message", "").strip()
    if not user_message:
        return jsonify({"error": "消息不能为空"}), 400
    agents = _get_user_agents(_get_user_id())
    return Response(
        stream_with_context(_stream_reply(agents["interview"], user_message)),
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

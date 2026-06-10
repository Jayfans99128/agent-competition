import os
import json
import logging
import socket
import subprocess
import time
import urllib.parse
import urllib.request

from flask import Flask, request, jsonify, send_from_directory, Response, stream_with_context
from flask_cors import CORS
from werkzeug.utils import secure_filename

from backend.agent import Agent
from backend.config import client, MODEL, CHAT_TOOLS, RESUME_TOOLS, JOB_TOOLS
from backend.tools import TOOL_MAP
from backend.personality_test import QUESTIONS, calculate_result, QUESTIONS_PER_PAGE

# ---------- 日志 ----------
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "app.log")

# 简洁格式：只有时间和消息，级别用彩色标记
LOG_FORMAT = "%(asctime)s  %(message)s"
DATE_FORMAT = "%H:%M:%S"

# 文件日志：保留完整信息
file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

# 控制台日志：简洁格式
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))

# 只配置我们自己的 logger，不动 root logger
logger = logging.getLogger("zhipig")
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.addHandler(console_handler)
logger.propagate = False  # 不往 root 传，避免重复

# 关闭 Flask / Werkzeug 的请求日志（那些 304/静态文件日志）
logging.getLogger("werkzeug").setLevel(logging.WARNING)

# 关闭 OpenAI / httpx 的 HTTP 请求日志
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

app = Flask(__name__)
CORS(app)

# ---------- 请求日志（简洁格式） ----------
@app.before_request
def _log_request_start():
    request._start_time = time.time()

@app.after_request
def _log_request(response):
    duration = (time.time() - getattr(request, "_start_time", time.time())) * 1000
    method = request.method
    path = request.path
    status = response.status_code
    # 跳过静态文件
    if path.startswith("/download-resume/"):
        pass  # 下载链接也记录
    elif method == "GET" and (
        path == "/" or path.endswith(".html") or path.endswith(".js") or
        path.endswith(".css") or path.endswith(".png") or path.endswith(".ico") or
        path.endswith(".jpg") or path.endswith(".svg")):
        return response
    # 也跳过轮询类请求
    if path == "/get-resume" and request.headers.get("X-No-Log"):
        return response

    emoji = "✓" if 200 <= status < 300 else "✗"
    logger.info("%s %s %s  →  %s  (%dms)",
                emoji, method, path, status, int(duration))
    return response

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


@app.route("/interview-video.html")
def interview_video():
    return send_from_directory(FRONTEND_DIR, "interview-video.html")


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
CHAT_PROMPT = """你是一位就业指导专家，服务对象是在校学生和应届生。今天是2026年6月。

【核心规则 — 最重要】
- ⚠️ 强制字数限制：每条回复不超过150字。超长回复会消耗用户时间，必须严格控制
- 直接报结果，零铺垫：上来就报数据/结论，删掉"根据数据显示"、"让我为你分析"等废话
- 分点用短横线，每点不超过2行
- 口语化，像发微信一样简洁
- 不要展示搜索/查询过程：绝对禁止说"我帮你查了"、"数据库返回"、"搜了一下"等
- 问题太宽泛时，反问一句缩小范围即可，用「」强调关键词

【时间转换】
- "今年"/"最新"→2026，"去年"→2025，"前年"→2024

【数据注意事项】
- 最低分明显低于国家线（如工学264→名单218）→说明可能含专项计划考生，建议参考复试资格线
- 广东技术师范大学复试线多数按国家A线执行

【工具规则】
- 问复试线/分数线/国家线/报考人数 → 调 query_kaoyan_scores
- 问国考分数线/进面分 → 调 query_guokao_scores
- 问考研院校信息 → 调 query_kaoyan_school
- 问备考资料/学习方法 → 调 query_doubao
- 问车辆工程岗位 → 调 query_knowledge_base
- 日常聊天/建议/规划 → 直接回，别调工具
- 数据库已有2026最新数据，不要说"还没出"

使用中文回复。"""

RESUME_PROMPT = """你是一位简历分析师，服务对象是在校学生。用户已上传简历。
【核心规则】
1. 紧扣问题：只回答用户当前问的问题，不要一次性把所有分析都倒出来。
2. 极简输出：每条回复控制在150字以内，用短句分点，每点不超过2行。
3. 给具体建议：比如"把'参与了'改成'负责了'，并加上数据成果"。
4. 口语化：像学长学姐改简历一样说话，直接、友善。
5. 一次只说最重要的1-3个点，不要面面俱到。
6. 不要主动调用工具，直接回答用户的问题。
7.“请注意：控制你的文本格式，严禁输出连续两个以上的换行符。行与行之间最多只能保留一个空行。”
使用中文回复。"""

INTERVIEW_PROMPT = """你是一位专业的模拟面试官，服务对象是在校学生和应届生。你的任务是为用户进行模拟面试练习。

【面试流程】
1. 如果用户没有说明自己的专业和目标岗位，必须先问清楚这两点再开始。不要替用户假设专业或岗位
2. 了解用户背景后，开始正式的模拟面试，每次只问一个问题
3. 根据用户的回答，给予简短点评（一句话），然后继续下一个问题
4. 每轮面试问3-5个问题即可，结束时给出总体评价

【基于简历的面试 — 重要】
如果对话中已包含用户的简历内容，你必须：
- 面试问题紧密围绕简历中的项目经历、技能、教育背景来设计
- 针对简历中的具体项目问技术细节、遇到的挑战、解决方案
- 针对简历中的实习/工作经历问具体贡献和成果
- 发现简历中的亮点和薄弱点，在面试中重点考察薄弱点
- 面试结束后，额外提供一份简历修改建议（包括：结构优化、措辞建议、亮点提炼、需要补充的内容）
- 简历修改建议要具体，例如"把XX项目的描述从'参与了'改成'主导了'，并加上量化数据"

【核心规则】
1. 一次只问一个问题，不要一次性抛出多个问题
2. 问题要有针对性，根据用户说的岗位方向和简历内容来问
3. 点评要具体、有建设性，不要只说"回答得不错"
4. 保持专业但友好的面试官语气
5. 总体评价包含：优点、不足、改进建议，每条一句话
6. 如果用户说想结束面试，给出总体评价 + 简历修改建议（如有简历）
7. 面试结束后，如果用户有简历，先问用户："需要我帮你生成一份优化后的简历吗？"——等用户确认后，再告诉用户"好的，请点击下方下载按钮获取优化后的简历，我会为你生成一份干净可投递的版本"（注意：不要在消息里直接输出优化后的简历内容，让用户点击按钮下载）
8. 如果用户没有简历或用户说不需要，就不要提下载的事

使用中文回复。"""

JOB_PROMPT = """你是一位职位搜索与推荐专家，服务对象是在校学生和应届生。
【核心规则】
- 紧扣问题，只回答那一两个点，不要把所有功能都用上
- 每条回复控制在150字以内，用短句
- 直接给公司名+岗位名+一句话亮点，不要长篇介绍
- 口语化，像朋友分享招聘信息一样
- 不要展示思考过程，不要出现"让我想想"、"稍等"等过渡语
- 如果用户没说清楚意向行业/岗位，先反问一个具体问题确认方向
- 不要主动调用工具！只在用户明确问到具体信息时才用

【工具选择指引】（只在你确认需要时使用）
- 考研/国考分数线、报考人数 → query_kaoyan_scores / query_guokao_scores
- 考研院校信息 → query_kaoyan_school
- 考研/考公备考资料 → query_doubao

使用中文回复。"""

# ----- 用户隔离的 Agent 实例 -----
user_agents = {}  # {user_id: {"chat": Agent, "resume": Agent, "job": Agent, "interview": Agent}}
user_resumes = {}  # {user_id: raw_resume_text}  存储用户的简历原文
user_resume_injected = {}  # {user_id: bool}  标记是否已将简历注入面试 agent


def _get_user_id():
    """从请求头获取用户 ID"""
    return request.headers.get("X-User-Id", "anonymous")


def _get_user_agents(user_id):
    """获取或创建某个用户的 Agent 实例"""
    if user_id not in user_agents:
        user_agents[user_id] = {
            "chat": Agent(client=client, model=MODEL, system_prompt=CHAT_PROMPT, tools=CHAT_TOOLS, tool_map=TOOL_MAP),
            "resume": Agent(client=client, model=MODEL, system_prompt=RESUME_PROMPT, tools=RESUME_TOOLS, tool_map=TOOL_MAP),
            "job": Agent(client=client, model=MODEL, system_prompt=JOB_PROMPT, tools=JOB_TOOLS, tool_map=TOOL_MAP),
            "interview": Agent(client=client, model=MODEL, system_prompt=INTERVIEW_PROMPT, tools=[], tool_map=TOOL_MAP),
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


# ----- 职业性格测试 API -----
@app.route("/api/personality-test/questions", methods=["GET"])
def get_personality_questions():
    """返回所有测试题目"""
    return jsonify({
        "questions": QUESTIONS,
        "perPage": QUESTIONS_PER_PAGE,
        "dimNames": {
            "R": "实际型",
            "I": "研究型",
            "A": "艺术型",
            "S": "社会型",
            "E": "企业型",
            "C": "常规型",
        }
    })


@app.route("/api/personality-test/result", methods=["POST"])
def personality_test_result():
    """提交答案并获取测评结果"""
    data = request.json
    answers = data.get("answers", {})
    if not answers:
        return jsonify({"error": "请先完成所有题目"}), 400

    try:
        result = calculate_result(answers)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"计算结果出错: {str(e)}"}), 500


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

    # 存储简历原文，供面试等模块使用
    user_id = _get_user_id()
    user_resumes[user_id] = content
    user_resume_injected[user_id] = False  # 重置注入标记

    agents = _get_user_agents(user_id)
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


@app.route("/get-resume", methods=["GET"])
def get_resume():
    """获取当前用户已上传的简历原文"""
    user_id = _get_user_id()
    resume_text = user_resumes.get(user_id, "")
    return jsonify({
        "has_resume": bool(resume_text),
        "resume_text": resume_text,
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

    user_id = _get_user_id()
    agents = _get_user_agents(user_id)

    # 如果用户有上传简历且尚未注入到面试 agent，则注入简历上下文
    resume_text = user_resumes.get(user_id, "")
    if resume_text and not user_resume_injected.get(user_id, False):
        agents["interview"].history.append({
            "role": "user",
            "content": f"【以下是我的个人简历，请在面试中围绕简历内容进行提问】\n\n{resume_text}"
        })
        agents["interview"].history.append({
            "role": "assistant",
            "content": "收到，我已了解你的简历背景，会结合你的经历进行针对性提问。"
        })
        user_resume_injected[user_id] = True

    return Response(
        stream_with_context(_stream_reply(agents["interview"], user_message)),
        mimetype="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )


# ---------- 简历修改 ----------
@app.route("/modify-resume", methods=["POST"])
def modify_resume():
    """基于模板简历.docx 生成优化后的简历 DOCX 文件"""
    user_id = _get_user_id()
    resume_text = user_resumes.get(user_id, "")

    data = request.json or {}
    # 也支持直接传入简历文本（从面试页面等）
    input_text = data.get("resume_text", "").strip()
    if input_text:
        resume_text = input_text

    if not resume_text:
        return jsonify({"error": "没有可用的简历，请先上传简历"}), 400

    # 调用模板填充模块
    from backend.skill.resume_analyzer.template_filler import fill_template

    import uuid as _uuid
    download_token = _uuid.uuid4().hex
    download_path = os.path.join(UPLOAD_FOLDER, f"improved_{download_token}.docx")

    try:
        fill_template(resume_text, download_path)
    except Exception as e:
        logger.error(f"模板填充失败: {e}")
        return jsonify({"error": f"简历生成失败: {str(e)}"}), 500

    download_url = f"/download-resume/{download_token}"

    # 读取生成的 DOCX 文本内容用于前端预览
    try:
        from docx import Document as DocxDocument
        doc = DocxDocument(download_path)
        preview_text = '\n'.join(p.text for p in doc.paragraphs if p.text.strip())
    except Exception:
        preview_text = "简历已生成，请点击下载查看。"

    return jsonify({
        "improved_resume": preview_text,
        "download_url": download_url,
    })


@app.route("/download-resume/<token>", methods=["GET"])
def download_resume(token):
    """下载优化后的简历 DOCX 文件"""
    # 安全校验 token，防止路径遍历
    token = token.replace("..", "").replace("/", "").replace("\\", "")
    filepath = os.path.join(UPLOAD_FOLDER, f"improved_{token}.docx")
    if not os.path.exists(filepath):
        return jsonify({"error": "文件不存在或已过期"}), 404

    # 读取文件内容
    with open(filepath, 'rb') as f:
        content = f.read()

    # 清理文件
    try:
        os.remove(filepath)
    except Exception:
        pass

    safe_filename = "优化后简历.docx"
    return Response(
        content,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{urllib.parse.quote(safe_filename)}",
        },
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

    logger.info("=" * 50)
    logger.info("🐷 职小猪 启动中...")
    logger.info("")
    logger.info("  本地访问:   http://127.0.0.1:%s", PORT)
    logger.info("  局域网访问: http://%s:%s", local_ip, PORT)

    cpolar_started = start_cpolar(PORT)
    if cpolar_started:
        public_url = get_cpolar_url()
        if public_url:
            logger.info("  公网访问:   %s", public_url)
    else:
        logger.info("  公网访问:   请手动运行 cpolar http %s", PORT)
    logger.info("=" * 50)

    app.run(host="0.0.0.0", port=PORT, debug=True)

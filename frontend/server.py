import os
import json
import logging
import socket
import subprocess
import time
import urllib.request

from flask import Flask, send_from_directory

# ---------- 日志 ----------
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ---------- Flask 应用 ----------
FRONTEND_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")


@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(FRONTEND_DIR, path)


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
            # fallback: 返回第一个 http 地址
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
        # 先检查 cpolar 是否已经在运行
        if get_cpolar_url():
            logger.info("cpolar 已在运行")
            return True

        subprocess.Popen(
            ["cpolar", "http", str(port)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        # 等待 cpolar 启动并获取地址
        for _ in range(10):
            time.sleep(1)
            url = get_cpolar_url()
            if url:
                logger.info(f"cpolar 公网地址: {url}")
                return True
        logger.warning("cpolar 启动超时，请手动运行: cpolar http {}".format(port))
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

    # 获取本机局域网 IP
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
    finally:
        s.close()

    print("=" * 50)
    logger.info(f"本地访问:    http://127.0.0.1:{PORT}")
    logger.info(f"局域网访问:  http://{local_ip}:{PORT}")

    # 尝试启动 cpolar
    cpolar_started = start_cpolar(PORT)
    if cpolar_started:
        public_url = get_cpolar_url()
        if public_url:
            logger.info(f"公网访问:    {public_url}")
    else:
        logger.info("公网访问:    请手动运行 cpolar http {}".format(PORT))
    print("=" * 50)

    app.run(host="0.0.0.0", port=PORT, debug=False)

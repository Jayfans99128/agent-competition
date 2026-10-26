"""
MySQL 数据库层
存储用户数据、对话历史、简历信息
"""
import json
import logging
import os

import pymysql
from pymysql.cursors import DictCursor

from backend.config import MYSQL_CONFIG

logger = logging.getLogger("zhipig")

_pool = None


def _get_conn():
    """获取数据库连接（每次新建，简单可靠）"""
    return pymysql.connect(
        host=MYSQL_CONFIG["host"],
        port=MYSQL_CONFIG["port"],
        user=MYSQL_CONFIG["user"],
        password=MYSQL_CONFIG["password"],
        database=MYSQL_CONFIG["database"],
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=True,
    )


def init_db():
    """建表（幂等，重复运行不会报错）"""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            # 用户表：简历 + 注入标记
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id VARCHAR(64) PRIMARY KEY,
                    resume_text LONGTEXT,
                    resume_injected TINYINT DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)

            # 对话历史表：每个用户的每种 Agent 一条记录，history 整体存 JSON
            cur.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id VARCHAR(64) NOT NULL,
                    agent_type VARCHAR(16) NOT NULL COMMENT 'chat/resume/job/interview',
                    history JSON,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY uk_user_agent (user_id, agent_type)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """)

        logger.info("✅ MySQL 表初始化完成")
    finally:
        conn.close()


# ===================== users 表操作 =====================

def get_user(user_id: str) -> dict:
    """获取用户信息，不存在则返回空字典"""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
            return cur.fetchone() or {}
    finally:
        conn.close()


def upsert_user(user_id: str, resume_text: str = None, resume_injected: int = None):
    """插入或更新用户信息"""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            # 先尝试插入
            cur.execute(
                "INSERT INTO users (user_id) VALUES (%s) ON DUPLICATE KEY UPDATE user_id = user_id",
                (user_id,),
            )
            # 再更新字段（只更新非 None 的）
            if resume_text is not None:
                cur.execute(
                    "UPDATE users SET resume_text = %s WHERE user_id = %s",
                    (resume_text, user_id),
                )
            if resume_injected is not None:
                cur.execute(
                    "UPDATE users SET resume_injected = %s WHERE user_id = %s",
                    (resume_injected, user_id),
                )
    finally:
        conn.close()


def get_resume(user_id: str) -> str:
    """获取用户简历原文"""
    user = get_user(user_id)
    return user.get("resume_text") or ""


def set_resume(user_id: str, resume_text: str):
    """保存用户简历原文"""
    upsert_user(user_id, resume_text=resume_text, resume_injected=0)


def get_resume_injected(user_id: str) -> bool:
    """获取简历是否已注入面试 Agent"""
    user = get_user(user_id)
    return bool(user.get("resume_injected"))


def set_resume_injected(user_id: str, injected: bool):
    """设置简历注入标记"""
    upsert_user(user_id, resume_injected=1 if injected else 0)


# ===================== conversations 表操作 =====================

def get_history(user_id: str, agent_type: str) -> list:
    """获取对话历史，返回 list[dict]"""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT history FROM conversations WHERE user_id = %s AND agent_type = %s",
                (user_id, agent_type),
            )
            row = cur.fetchone()
            if row and row["history"]:
                # JSON 字段可能返回 str 或 dict，统一处理
                raw = row["history"]
                if isinstance(raw, str):
                    return json.loads(raw)
                return raw
            return []
    finally:
        conn.close()


def save_history(user_id: str, agent_type: str, history: list):
    """保存对话历史（整体覆盖写入）"""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO conversations (user_id, agent_type, history)
                   VALUES (%s, %s, %s)
                   ON DUPLICATE KEY UPDATE history = VALUES(history)""",
                (user_id, agent_type, json.dumps(history, ensure_ascii=False)),
            )
    finally:
        conn.close()


def user_exists(user_id: str) -> bool:
    """检查用户是否存在"""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM users WHERE user_id = %s", (user_id,))
            return cur.fetchone() is not None
    finally:
        conn.close()

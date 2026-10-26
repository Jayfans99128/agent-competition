# 🐷 职小猪 — 智能职业助手

> 面向在校学生和应届生的 AI 职业规划平台，集成智能对话、简历分析、模拟面试、沉浸式视频面试、职位搜索五大模块。

---

## 🏗️ 技术架构

| 层 | 技术栈 |
|---|---|
| 后端 | Python Flask + OpenAI 兼容 API |
| 模型 | `DeepSeek-V4-Flash`（SiliconFlow API） |
| 前端 | 原生 HTML / CSS / JavaScript，5 个独立 SPA 页面 |
| 通信 | SSE 流式输出 + REST API，`X-User-Id` 请求头隔离多用户 |
| **数据存储** | **MySQL**（用户数据 + 对话历史持久化） |
| **向量检索** | **ChromaDB**（知识库语义搜索） |
| 语音 | Web Speech API（TTS 语音合成 + STT 语音识别） |
| 内网穿透 | cpolar（自动获取公网 HTTPS 地址） |

```
agent-competition/
├── backend/
│   ├── app.py              # Flask 主服务（路由 + 日志 + 启动）
│   ├── agent.py             # Agent 类（LLM 对话循环 + 工具调用）
│   ├── config.py            # 模型/API/MySQL/ChromaDB 配置
│   ├── db.py                # 🆕 MySQL 数据库层（用户 + 对话历史）
│   ├── vector_store.py      # 🆕 ChromaDB 向量检索层
│   ├── tools.py             # 工具注册表 TOOL_MAP
│   ├── doubao_client.py     # 豆包大模型客户端（Web/API 双模式）
│   ├── personality_test.py  # MBTI 职业性格测试（20 题 / 4 维度）
│   ├── chroma_data/         # 🆕 ChromaDB 持久化目录（自动生成）
│   ├── knowledge_base/      # 本地知识库
│   │   ├── manager.py       #   车辆工程岗位知识库（23+ 方向）
│   │   ├── exam_manager.py  #   考研/国考分数线查询
│   │   ├── school_manager.py#   考研院校信息查询
│   │   ├── kaoyan_manager.py#   考研数据备选查询
│   │   ├── kaoyan_parser.py #   kaoyan.cn 网页抓取
│   │   └── *.txt            #   结构化数据文件
│   ├── skill/
│   │   ├── resume_analyzer/ # AI 简历结构化解析
│   │   └── search/          # 联网搜索引擎（DDG → Bing → 搜狗）
│   ├── network/             # HTTP 请求层（浏览器 UA 伪装）
│   └── utils/               # 文件操作、CLI 输入工具
├── frontend/
│   ├── index.html + app.js              # 智能对话页
│   ├── resume.html + resume.js          # 简历分析页
│   ├── interview.html + interview.js    # 文字模拟面试页
│   ├── interview-video.html + interview-video.js  # 沉浸式视频面试页
│   ├── job-search.html + job-search.js  # 职位搜索页
│   ├── auth.js              # 用户身份管理
│   └── style.css            # 全站样式
├── main.py                  # 独立 CLI 入口
└── requirements.txt         # 🆕 更新后的依赖列表
```

---

## 🆕 本次改动说明

### 1. MySQL 数据持久化

**改动前：** 用户数据全部存在 Python 内存字典中，服务重启即丢失。
**改动后：** 用户数据和对话历史持久化到 MySQL，重启后自动恢复。

#### 新增文件

| 文件 | 说明 |
|---|---|
| `backend/db.py` | MySQL 数据库层，提供建表、CRUD 操作 |

#### 数据库表结构

```sql
-- 用户表：简历 + 注入标记
CREATE TABLE users (
    user_id VARCHAR(64) PRIMARY KEY,
    resume_text LONGTEXT,
    resume_injected TINYINT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 对话历史表：每个用户的每种 Agent 一条记录，history 整体存 JSON
CREATE TABLE conversations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(64) NOT NULL,
    agent_type VARCHAR(16) NOT NULL COMMENT 'chat/resume/job/interview',
    history JSON,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_user_agent (user_id, agent_type)
);
```

#### 改动文件

| 文件 | 改动内容 |
|---|---|
| `backend/config.py` | 新增 `MYSQL_CONFIG` 配置项（从 `.env` 读取） |
| `backend/app.py` | ① 启动时调用 `db.init_db()` 建表<br>② 替换 `user_resumes`/`user_resume_injected` 字典为 MySQL 读写<br>③ 所有对话 API 在回复后调用 `db.save_history()` 持久化历史<br>④ 流式 API 在 `yield` 结束后持久化 |

#### 配置方式（`.env` 文件）

```bash
# MySQL 配置
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=你的密码
MYSQL_DATABASE=employment_ai
```

#### 初始化

```bash
# 1. 创建数据库
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS employment_ai DEFAULT CHARSET utf8mb4"

# 2. 表会在首次启动时自动创建（init_db 幂等）
python -m backend.app
```

---

### 2. ChromaDB 向量语义检索

**改动前：** 知识库查询使用关键词匹配，搜 "新能源核心技术" 找不到 "电池工程师"。
**改动后：** 向量语义检索，理解语义关联，大幅提升召回率。

#### 新增文件

| 文件 | 说明 |
|---|---|
| `backend/vector_store.py` | ChromaDB 向量检索层，支持建索引 + 语义搜索 |

#### 支持的检索范围

| Collection | 数据源 | 说明 |
|---|---|---|
| `knowledge_base` | `knowledge_base_data.txt` | 车辆工程岗位（23+ 方向） |
| `kaoyan_data` | `kaoyan_data.txt` | 考研分数线、院校信息 |
| `guokao_data` | `guokao_data.txt` | 国考进面分、竞争比 |

#### 改动文件

| 文件 | 改动内容 |
|---|---|
| `backend/config.py` | 新增 `CHROMA_PERSIST_DIR` 配置项；TOOLS 列表新增 `vector_search` 工具 |
| `backend/tools.py` | 新增 `_vector_search()` 函数并注册到 `TOOL_MAP` |
| `backend/app.py` | 启动时调用 `vector_store.build_indices()` 构建向量索引 |

#### 新增工具：`vector_search`

| 参数 | 类型 | 说明 |
|---|---|---|
| `query` | string | 搜索内容，如 "新能源汽车核心技术" |
| `scope` | string | 搜索范围：`all`=全部, `job`=岗位, `kaoyan`=考研, `guokao`=国考 |

**工具分配：** `vector_search` 分配给 Chat Agent 和 Job Agent，与现有关键词工具互补。

#### 配置方式（`.env` 文件）

```bash
# ChromaDB 持久化目录（可选，默认 backend/chroma_data）
CHROMA_PERSIST_DIR=./backend/chroma_data
```

---

### 3. 完整改动清单

| 类型 | 文件 | 变更 |
|---|---|---|
| **新增** | `backend/db.py` | MySQL 数据库层（~150 行） |
| **新增** | `backend/vector_store.py` | ChromaDB 向量检索层（~200 行） |
| **修改** | `backend/config.py` | +MySQL 配置 +ChromaDB 配置 +vector_search 工具定义 |
| **修改** | `backend/tools.py` | +vector_search 工具注册 |
| **修改** | `backend/app.py` | 集成 MySQL（替代内存字典）+ 启动时建表/建索引 |
| **修改** | `backend/requirements.txt` | +pymysql +chromadb |

---

## 🤖 四大 Agent

系统为每个用户维护 4 个独立的 Agent 实例，各自有独立的系统提示词、工具集和对话历史。

### 1. Chat Agent — 智能对话

| 属性 | 值 |
|---|---|
| 页面 | `index.html` |
| 端点 | `POST /chat/stream` |
| 工具 | `web_search` `query_knowledge_base` `query_kaoyan_scores` `query_guokao_scores` `query_kaoyan_school` `query_doubao` `vector_search` |
| 特点 | 紧扣问题、150 字以内、口语化、支持向量语义检索 |

### 2. Resume Agent — 简历分析

| 属性 | 值 |
|---|---|
| 页面 | `resume.html` |
| 端点 | `POST /resume-chat/stream` |
| 工具 | `list_files` `read_file` |
| 特点 | 极简输出、具体建议、口语化、不主动调工具 |

### 3. Interview Agent — 模拟面试

| 属性 | 值 |
|---|---|
| 页面 | `interview.html`（文字） / `interview-video.html`（视频通话） |
| 端点 | `POST /interview/stream` |
| 工具 | 无（纯对话） |
| 特点 | 每次只问一题、逐题点评、围绕简历精准提问 |

### 4. Job Agent — 职位搜索

| 属性 | 值 |
|---|---|
| 页面 | `job-search.html` |
| 端点 | `POST /job-chat/stream` |
| 工具 | `web_search` `query_kaoyan_scores` `query_guokao_scores` `query_kaoyan_school` `query_doubao` `vector_search` |
| 特点 | 公司名+岗位名+一句话亮点、支持向量语义检索 |

---

## 🔧 工具系统

| # | 工具名 | 功能 | 数据来源 |
|---|---|---|---|
| 1 | `web_search` | 联网搜索（返回 Top 5） | DDG → Bing → 搜狗 |
| 2 | `query_knowledge_base` | 车辆工程岗位知识库（关键词匹配） | 本地结构化文本 |
| 3 | `query_kaoyan_scores` | 考研国家线/复试线/报录比 | 本地数据 + kaoyan.cn |
| 4 | `query_guokao_scores` | 国考进面分/竞争比 | 本地数据文件 |
| 5 | `query_kaoyan_school` | 考研院校信息查询 | 本地数据 + kaoyan.cn |
| 6 | `query_doubao` | 备考资料/学习方法推荐 | 豆包大模型 |
| 7 | `vector_search` 🆕 | **语义向量检索**（跨知识库） | ChromaDB 向量索引 |
| 8 | `list_files` | 列出目录文件 | 文件系统 |
| 9 | `read_file` | 读取文件内容 | 文件系统 |

---

## 🌐 API 端点

### 流式对话

| 端点 | 方法 | 说明 |
|---|---|---|
| `/chat/stream` | POST | 智能对话（SSE） |
| `/resume-chat/stream` | POST | 简历问答（SSE） |
| `/interview/stream` | POST | 模拟面试（SSE） |
| `/job-chat/stream` | POST | 职位搜索（SSE） |

### 历史记录

| 端点 | 方法 | 说明 |
|---|---|---|
| `/chat/history` | GET | 对话历史 |
| `/resume-chat/history` | GET | 简历对话历史 |
| `/interview/history` | GET | 面试历史 |
| `/job-chat/history` | GET | 职位对话历史 |

### 简历管理

| 端点 | 方法 | 说明 |
|---|---|---|
| `/upload-resume` | POST | 上传简历 + AI 解析 |
| `/get-resume` | GET | 检查用户是否已上传简历 |
| `/modify-resume` | POST | AI 生成优化版简历 |
| `/download-resume/<token>` | GET | 下载优化简历（一次性） |

### 性格测试

| 端点 | 方法 | 说明 |
|---|---|---|
| `/api/personality-test/questions` | GET | 获取 20 道 MBTI 题目 |
| `/api/personality-test/result` | POST | 提交答案，返回 MBTI 类型 + 职业推荐 |

---

## 🚀 启动

```bash
# 1. 安装依赖
pip install -r backend/requirements.txt

# 2. 创建 MySQL 数据库
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS employment_ai DEFAULT CHARSET utf8mb4"

# 3. 配置环境变量（.env 文件）
cat > .env << EOF
# 模型 API
API_KEY=your_api_key
BASE_URL=https://api.siliconflow.cn/v1

# MySQL
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=employment_ai

# 豆包（可选）
DOUBAO_MODE=web
DOUBAO_SESSION_ID=your_session_id
EOF

# 4. 启动服务（首次启动会自动建表 + 构建向量索引）
python -m backend.app

# 5. 访问
# 本地：http://127.0.0.1:5000
# 公网：启动后自动通过 cpolar 生成 HTTPS 地址
```

---

## 📐 系统参数

| 参数 | 值 |
|---|---|
| LLM max_tokens | 2048 |
| 工具调用最大轮次 | 5 轮 |
| MySQL 连接 | 每次请求新建（简单可靠） |
| ChromaDB 索引 | 启动时自动构建，持久化到 `backend/chroma_data/` |
| 向量检索默认返回 | 岗位 3 条 / 考研 5 条 / 国考 5 条 |

---

## 📊 对比：改动前后

| 维度 | 改动前 | 改动后 |
|---|---|---|
| 用户数据存储 | Python 内存字典 | MySQL 持久化 |
| 服务重启 | 所有数据丢失 | 自动从 MySQL 恢复 |
| 知识库检索 | 纯关键词匹配 | 关键词 + 向量语义检索 |
| 搜 "新能源核心技术" | 找不到 "电池工程师" | ✅ 语义匹配命中 |
| 搜 "竞争大的公务员岗位" | 找不到 "竞争比" | ✅ 语义理解关联 |
| 新增依赖 | — | pymysql + chromadb |

---

<p align="center">Powered by <b>职通车队</b> 🚗</p>

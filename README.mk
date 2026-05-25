# 职小猪 —— 智能职业助手

职小猪是一款基于 AI 的智能职业助手，提供**智能对话**、**简历分析**和**职位搜索**三大功能，帮助在校学生和应届生更好地准备求职。

---

## 环境要求

- Python 3.10+
- Windows / macOS / Linux

## 安装步骤

### 1. 创建虚拟环境并安装依赖

```bash
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash
# 或 .venv\Scripts\activate     # Windows CMD
pip install -r backend/requirements.txt
```

如果使用简历上传的 DOCX/PDF 解析功能，还需要额外安装：

```bash
pip install python-docx PyPDF2
```

### 2. 配置 API 密钥

在项目根目录创建 `.env` 文件（可选），内容如下：

```env
API_KEY=你的API密钥
BASE_URL=https://api.siliconflow.cn/v1
```

默认使用 SiliconFlow 平台的 DeepSeek-V4-Flash 模型。如需更换模型，修改 [backend/config.py](backend/config.py) 中的 `MODEL` 变量。

---

## 使用方式

### 方式一：Web 界面（推荐）

**启动后端服务：**

```bash
cd backend
python app.py
```

服务默认运行在 `http://localhost:5000`。

**打开前端页面：**

直接用浏览器打开 `frontend/` 目录下的 HTML 文件：

| 页面 | 文件 | 功能 |
|------|------|------|
| 智能对话 | [frontend/index.html](frontend/index.html) | 通用就业咨询、职业规划、面试技巧 |
| 简历分析 | [frontend/resume.html](frontend/resume.html) | 上传简历文件，获取结构化分析和修改建议 |
| 职位搜索 | [frontend/job-search.html](frontend/job-search.html) | 搜索岗位信息、分析岗位匹配度 |

### 方式二：命令行交互

```bash
python main.py
```

在终端中直接与 AI 对话，按 **Enter** 发送消息，按 **Esc** 退出。

---

## 功能说明

### 智能对话

- 解答求职相关问题（面试准备、职业规划、简历技巧等）
- 支持联网搜索（自动调用必应、DuckDuckGo、搜狗）
- 搜索规则：AI 会先确认你想搜索的方向，再逐一精准搜索

### 简历分析

- 支持上传 **TXT**、**DOCX**、**PDF** 格式的简历文件
- 自动提取结构化信息：姓名、教育背景、技能、项目经历、工作经历
- 分析完成后可以继续追问，获取修改建议、措辞优化、模拟面试题等

### 职位搜索

- 根据专业、技能和意向搜索匹配岗位
- 分析岗位要求与个人背景的匹配度
- 提供求职策略和行业趋势信息

---

## 项目结构

```
agent-competition/
├── main.py                  # 命令行交互入口
├── frontend/                # 前端页面
│   ├── index.html           # 智能对话页面
│   ├── resume.html          # 简历分析页面
│   ├── job-search.html      # 职位搜索页面
│   ├── app.js               # 智能对话逻辑
│   ├── resume.js            # 简历分析逻辑
│   ├── job-search.js        # 职位搜索逻辑
│   └── style.css            # 统一样式
├── backend/
│   ├── app.py               # Flask Web 服务
│   ├── agent.py             # Agent 对话管理类
│   ├── config.py            # 配置（API、模型、工具定义）
│   ├── tools.py             # 工具映射
│   ├── requirements.txt     # Python 依赖
│   ├── network/             # 网络请求模块
│   │   ├── session.py       # HTTP 请求封装
│   │   └── headers.py       # 请求头配置
│   ├── skill/
│   │   ├── search/          # 搜索引擎模块
│   │   │   ├── manager.py   # 搜索调度
│   │   │   ├── bing.py      # 必应搜索
│   │   │   ├── ddg.py       # DuckDuckGo 搜索
│   │   │   └── sogou.py     # 搜狗搜索
│   │   └── resume_analyzer/ # 简历分析模块
│   │       └── resume_analyzer.py
│   └── utils/
│       ├── cli.py           # 命令行输入工具
│       └── file_operations.py # 文件读写工具
├── 简历示例.docx            # 测试用简历样本
└── 简历.txt                 # 测试用简历样本
```

---

## 可用工具

Agent 可以调用以下工具完成用户请求：

| 工具名 | 功能 |
|--------|------|
| `list_files` | 列出当前目录的文件 |
| `read_file` | 读取指定文件内容 |
| `web_search` | 联网搜索（必应 → DuckDuckGo → 搜狗 依次尝试） |
| `resume_analyzer` | 简历结构化分析 |

---

## 配置说明

在 [backend/config.py](backend/config.py) 中可以修改：

- **API_KEY**：API 密钥（建议通过 `.env` 文件设置）
- **BASE_URL**：API 地址（默认 SiliconFlow）
- **MODEL**：使用的模型名称
- **SYSTEM_PROMPT**：系统提示词（定义 AI 的行为风格和搜索规则）
- **TOOLS**：注册的工具列表（可增删工具）

# 🐷 职小猪 — 智能职业助手

> 面向在校学生和应届生的 AI 职业规划平台，集成智能对话、简历分析、模拟面试、沉浸式视频面试、职位搜索五大模块。

---

## 🏗️ 技术架构

| 层 | 技术栈 |
|---|---|
| 后端 | Python Flask + OpenAI 兼容 API |
| 模型 | `ds-v4`（DeepSeek 变体，内网 `10.0.24.102:3000/v1`） |
| 前端 | 原生 HTML / CSS / JavaScript，5 个独立 SPA 页面 |
| 通信 | SSE 流式输出 + REST API，`X-User-Id` 请求头隔离多用户 |
| 语音 | Web Speech API（TTS 语音合成 + STT 语音识别） |
| 内网穿透 | cpolar（自动获取公网 HTTPS 地址） |

```
agent-competition/
├── backend/
│   ├── app.py              # Flask 主服务（路由 + 日志 + 启动）
│   ├── agent.py             # Agent 类（LLM 对话循环 + 工具调用，max_tokens=8192）
│   ├── config.py            # 模型/API 配置 + 工具定义
│   ├── tools.py             # 工具注册表 TOOL_MAP
│   ├── doubao_client.py     # 豆包大模型客户端（Web/API 双模式）
│   ├── personality_test.py  # MBTI 职业性格测试（20 题 / 4 维度）
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
│   ├── interview-video.html + interview-video.js  # 沉浸式视频面试页 🆕
│   ├── job-search.html + job-search.js  # 职位搜索页
│   ├── 生成数字人.png                    # 数字人形象素材
│   ├── 职小猪.png                       # 吉祥物头像
│   ├── auth.js              # 用户身份管理
│   └── style.css            # 全站样式（~1700 行）
├── 生成数字人.png            # 数字人形象源文件
└── main.py                  # 独立 CLI 入口
```

---

## 🤖 四大 Agent

系统为每个用户维护 4 个独立的 Agent 实例，各自有独立的系统提示词、工具集和对话历史。

### 1. Chat Agent — 智能对话

| 属性 | 值 |
|---|---|
| 页面 | `index.html` |
| 端点 | `POST /chat/stream` |
| 工具 | `web_search` `query_knowledge_base` `query_kaoyan_scores` `query_guokao_scores` `query_kaoyan_school` `query_doubao` |
| 特点 | 紧扣问题、150 字以内、口语化、强制调用工具查数据 |

**功能：**
- 💬 SSE 流式对话，可随时中止
- 📚 考研分数线查询（国家线/复试线/报录比，13 学科门类 + 20+ 自划线高校）
- 🏛️ 国考分数线查询（进面分/竞争比，各省税务、海关）
- 🏫 考研院校信息查询（院校属性、特色专业、招生数据）
- 📖 备考资料推荐（豆包大模型辅助）
- 🚗 车辆工程岗位知识库（23+ 细分方向）
- 🌐 联网搜索（DuckDuckGo → Bing → 搜狗三级回退）
- 🧠 MBTI 职业性格测试（20 题 / 4 维度 / 16 型人格 + 职业推荐）

---

### 2. Resume Agent — 简历分析

| 属性 | 值 |
|---|---|
| 页面 | `resume.html` |
| 端点 | `POST /resume-chat/stream` |
| 工具 | `list_files` `read_file` |
| 特点 | 极简输出、具体建议、口语化、不主动调工具 |

**功能：**
- 📤 简历上传（txt / docx / pdf，自动提取文本）
- 🔍 AI 结构化解析（姓名、教育背景、技能、项目经历、工作经历）
- 💬 简历问答（诊断不足、措辞优化、岗位推荐、面试预测）
- 📥 下载优化简历（AI 生成干净版，无批注，可直接投递）

---

### 3. Interview Agent — 模拟面试

| 属性 | 值 |
|---|---|
| 页面 | `interview.html`（文字） / `interview-video.html`（视频通话） |
| 端点 | `POST /interview/stream` |
| 工具 | 无（纯对话，面试不需要查资料） |
| 特点 | 每次只问一题、逐题点评、围绕简历精准提问 |

**文字面试功能：**
- 🎯 5 种面试类型（技术面 / HR面 / 群面 / 产品面 / 行为面）
- 📋 简历关联（自动检测 → 注入上下文 → 围绕项目/技能提问）
- 🏷️ 关联简历后标题栏显示绿色标记
- 🔄 结构化流程（先确认专业+岗位 → 逐题提问 → 逐题点评 → 总体评价）
- 📝 面试结束给出简历修改建议
- 📥 按需下载优化简历（AI 先问"需要吗？"，确认后才显示下载按钮）

**沉浸式视频面试功能：** 🆕
- 📹 视频通话式界面（全屏数字人画面 + PIP 自拍小窗 + 字幕覆盖层）
- 🧑 AI 数字人形象（使用项目中的数字人图片，支持替换为视频素材）
- 🗣️ TTS 语音播报 — 面试官问题通过浏览器语音读出，支持中文女声
- 🎤 STT 语音识别 — 点击麦克风或按住空格键说话，自动识别发送
- 👄 说话动画 — AI 说话时数字人画面微动缩放 + 光晕脉冲
- 📷 PIP 摄像头 — 调用真实摄像头显示自己画面（无摄像头时显示占位头像）
- ⏱ 通话计时器 — 面试开始后自动计时
- 🔇 静音模式 — 一键切换纯文字模式
- 📝 对话记录面板 — 可折叠的实时问答记录
- ✏️ 文字输入备用 — 底部展开输入框，Enter 发送 / Shift+Enter 换行

---

### 4. Job Agent — 职位搜索

| 属性 | 值 |
|---|---|
| 页面 | `job-search.html` |
| 端点 | `POST /job-chat/stream` |
| 工具 | `web_search` `query_kaoyan_scores` `query_guokao_scores` `query_kaoyan_school` `query_doubao` |
| 特点 | 公司名+岗位名+一句话亮点、不主动调工具 |

**功能：**
- 🔍 职位搜索（根据专业/技能/意向匹配岗位）
- 🚀 快捷入口（Java开发、产品经理、数据分析、AI算法等）
- 📊 同样可查询考研/国考数据

---

## 🔧 工具系统

| # | 工具名 | 功能 | 数据来源 |
|---|---|---|---|
| 1 | `web_search` | 联网搜索（返回 Top 5） | DDG → Bing → 搜狗 |
| 2 | `query_knowledge_base` | 车辆工程岗位知识库（23+ 方向） | 本地结构化文本 |
| 3 | `query_kaoyan_scores` | 考研国家线/复试线/报录比 | 本地数据 + kaoyan.cn 抓取 |
| 4 | `query_guokao_scores` | 国考进面分/竞争比 | 本地数据文件 |
| 5 | `query_kaoyan_school` | 考研院校信息查询 | 本地数据 + kaoyan.cn 抓取 |
| 6 | `query_doubao` | 备考资料/学习方法推荐 | 豆包大模型（Web/API 双模式） |
| 7 | `list_files` | 列出目录文件 | 文件系统 |
| 8 | `read_file` | 读取文件内容 | 文件系统 |

### 工具→Agent 分配

| 工具 | Chat | Resume | Job | Interview |
|---|---|---|---|---|
| `web_search` | ✅ | | ✅ | |
| `query_knowledge_base` | ✅ | | | |
| `query_kaoyan_scores` | ✅ | | ✅ | |
| `query_guokao_scores` | ✅ | | ✅ | |
| `query_kaoyan_school` | ✅ | | ✅ | |
| `query_doubao` | ✅ | | ✅ | |
| `list_files` | | ✅ | | |
| `read_file` | | ✅ | | |

> Interview Agent 无工具 — 纯对话面试场景。

---

## 🌐 API 端点

### 流式对话

| 端点 | 方法 | 说明 |
|---|---|---|
| `/chat/stream` | POST | 智能对话（SSE） |
| `/resume-chat/stream` | POST | 简历问答（SSE） |
| `/interview/stream` | POST | 模拟面试（SSE，自动注入简历上下文） |
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
| `/upload-resume` | POST | 上传简历 + AI 解析（multipart/form-data） |
| `/get-resume` | GET | 检查用户是否已上传简历 |
| `/modify-resume` | POST | AI 生成优化版简历（返回下载链接） |
| `/download-resume/<token>` | GET | 下载优化简历（一次性，下载后删除） |

### 性格测试

| 端点 | 方法 | 说明 |
|---|---|---|
| `/api/personality-test/questions` | GET | 获取 20 道 MBTI 题目 |
| `/api/personality-test/result` | POST | 提交答案，返回 MBTI 类型 + 职业推荐 |

### 静态页面

| 路由 | 页面 |
|---|---|
| `/` | 智能对话 |
| `/resume.html` | 简历分析 |
| `/interview.html` | 模拟面试（文字） |
| `/interview-video.html` | 沉浸式视频面试 🆕 |
| `/job-search.html` | 职位搜索 |

---

## 🚀 启动

```bash
# 1. 安装依赖
pip install flask flask-cors openai python-dotenv PyPDF2 python-docx

# 2. 配置环境变量（.env 文件）
# DOUBAO_MODE=web              # 豆包模式：web 或 api
# DOUBAO_SESSION_ID=xxx        # Web 模式需要的 Cookie
# DOUBAO_API_KEY=xxx           # API 模式需要的密钥

# 3. 启动服务
python -m backend.app
# 或
python backend/app.py

# 4. 访问
# 本地：http://127.0.0.1:5000
# 公网：启动后自动通过 cpolar 生成 HTTPS 地址
```

---

## 📁 知识库数据文件

| 文件 | 内容 |
|---|---|
| `backend/knowledge_base/kaoyan_data.txt` | 考研国家线、各校复试线、院校信息 |
| `backend/knowledge_base/kaoyan_data_update.txt` | 考研补充数据 |
| `backend/knowledge_base/guokao_data.txt` | 国考进面分数线 |
| `backend/knowledge_base/wut_data.txt` | 武汉理工大学专项数据 |
| `backend/knowledge_base/knowledge_base_data.txt` | 车辆工程岗位知识库 |

---

## 🎨 前端通用能力

- 🧑 **多用户隔离** — localStorage 生成 UUID，`X-User-Id` 请求头传递
- 📋 **会话管理** — 每页最多 20 条历史，localStorage 持久化
- 📱 **移动端适配** — 底部导航栏 + 抽屉菜单
- ⌨️ **智能输入框** — Enter 发送 / Shift+Enter 换行 / 内容自动增高（最高 150px）
- ⏹️ **消息中止** — 发送中可点停止按钮中断生成
- 🌐 **cpolar 内网穿透** — 启动时自动获取公网 HTTPS 地址
- 🎨 **统一视觉风格** — 侧边栏导航、头像、快捷操作按钮、打字动画
- 🪵 **简洁日志** — 跳过静态文件请求，只记录 API 调用，格式 `✓ POST /path → 200 (123ms)`

---

## 🔌 外部集成

| 服务 | 用途 |
|---|---|
| 内网 LLM API (`10.0.24.102:3000/v1`) | 主力模型 ds-v4 |
| 豆包 Web API (`doubao.com`) | 备考资料推荐（免费，需 Cookie） |
| 火山引擎 ARK API | 豆包付费 API 模式 |
| DuckDuckGo Lite | 搜索引擎（首选） |
| Bing China (`cn.bing.com`) | 搜索引擎（备选） |
| 搜狗 (`sogou.com`) | 搜索引擎（兜底） |
| kaoyan.cn | 考研数据抓取 |
| Web Speech API | 浏览器内置 TTS 语音合成 + STT 语音识别 |
| cpolar | 内网穿透 / 公网访问 |

---

## 📐 系统参数

| 参数 | 值 |
|---|---|
| LLM max_tokens | 8192（流式/非流式统一） |
| 工具调用最大轮次 | 3 轮 |
| 会话历史上限（前端） | 20 条/页 |
| 输入框最大高度 | 150px |
| 日志格式 | `HH:MM:SS  ✓ METHOD /path → STATUS (ms)` |

---

<p align="center">Powered by <b>职通车队</b> 🚗</p>

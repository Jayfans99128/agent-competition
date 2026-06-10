// ===== 页面标识 =====
const PAGE_TYPE = 'interview';

// ===== 简历关联状态 =====
let hasResume = false;
let resumeText = '';

// ===== 欢迎消息管理 =====
let welcomeVisible = true;

function hideWelcome() {
    if (welcomeVisible) {
        const welcome = document.querySelector('.welcome-section');
        if (welcome) {
            welcome.style.display = 'none';
        }
        welcomeVisible = false;
    }
}

// ===== 消息操作 =====
function addMessage(text, className) {
    hideWelcome();
    const chatBox = document.getElementById('chat-box');
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message', className);
    messageDiv.innerText = text;
    chatBox.appendChild(messageDiv);
    chatBox.scrollTop = chatBox.scrollHeight;
    return messageDiv;
}

// ===== 打字指示器 =====
let typingIndicator = null;

function showTyping() {
    hideWelcome();
    const chatBox = document.getElementById('chat-box');
    if (typingIndicator) return;
    typingIndicator = document.createElement('div');
    typingIndicator.classList.add('message', 'bot-message', 'typing-indicator');
    typingIndicator.innerHTML =
        '<span class="dot"></span><span class="dot"></span><span class="dot"></span>';
    chatBox.appendChild(typingIndicator);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function hideTyping() {
    if (typingIndicator) {
        typingIndicator.remove();
        typingIndicator = null;
    }
}

// ===== 流式发送消息 =====
async function sendInterviewMessage() {
    const input = document.getElementById('user-input');
    const text = input.value.trim();
    if (!text) return;

    addMessage(text, 'user-message');
    saveHistoryItem(text, 'user');
    input.value = '';
    resetInputHeight();
    showTyping();

    try {
        const resp = await fetch('/interview/stream', {
            method: 'POST',
            headers: authHeaders({ 'Content-Type': 'application/json' }),
            body: JSON.stringify({ message: text }),
        });

        hideTyping();

        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let botMsg = addMessage('', 'bot-message');
        let buffer = '';
        let fullReply = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const data = line.slice(6);
                    if (data === '[DONE]') continue;
                    try {
                        const parsed = JSON.parse(data);
                        fullReply += parsed.content;
                        botMsg.innerText = fullReply;
                        document.getElementById('chat-box').scrollTop =
                            document.getElementById('chat-box').scrollHeight;
                    } catch (e) { /* ignore parse errors */ }
                }
            }
        }
        saveHistoryItem(fullReply, 'assistant');
        updateHistoryUI();

        // 当 AI 明确让用户点击下载按钮时才显示
        if (hasResume && (fullReply.includes('点击下方下载') || fullReply.includes('下载按钮'))) {
            showResumeDownloadBtn();
        }
    } catch (error) {
        hideTyping();
        addMessage('连接后端失败，请确认服务已启动', 'bot-message');
    }
}

// ===== 开始指定类型的面试 =====
function startInterviewType(type) {
    let prompt = '我想练习【' + type + '】，请先问我两个问题：1.我是什么专业的 2.我想面试什么岗位，然后根据我的回答再开始正式面试';
    if (hasResume) {
        prompt = '我想练习【' + type + '】，请根据我的简历内容来进行有针对性的面试提问。先确认我的专业和目标岗位，然后围绕简历中的项目和经历进行深入提问。';
    }
    const input = document.getElementById('user-input');
    input.value = prompt;
    sendInterviewMessage();
    startNewSession(type);
}

// ===== 结束面试 =====
async function endInterview() {
    const input = document.getElementById('user-input');
    if (hasResume) {
        input.value = '面试官你好，我想结束本轮面试，请给我一个总体评价，并针对我的简历给出具体的修改建议';
    } else {
        input.value = '面试官你好，我想结束本轮面试，请给我一个总体评价和建议';
    }
    await sendInterviewMessage();
}

// ===== 开始新面试 =====
function startNewInterview() {
    const chatBox = document.getElementById('chat-box');
    chatBox.querySelectorAll('.message').forEach(m => m.remove());
    const welcome = document.querySelector('.welcome-section');
    if (welcome) {
        welcome.style.display = '';
    }
    welcomeVisible = true;
    // 隐藏下载按钮
    const downloadBtn = document.getElementById('resume-download-area');
    if (downloadBtn) downloadBtn.style.display = 'none';
    startNewSession();
}

// ===== 简历上传（面试页面内） =====
function triggerResumeUpload() {
    document.getElementById('interview-resume-input').click();
}

async function handleInterviewResumeUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    const statusEl = document.getElementById('resume-upload-status');
    statusEl.textContent = '上传中...';
    statusEl.className = 'resume-status uploading';

    const formData = new FormData();
    formData.append('file', file);

    try {
        const resp = await fetch('/upload-resume', {
            method: 'POST',
            headers: authHeaders(),
            body: formData,
        });
        const data = await resp.json();

        if (data.error) {
            statusEl.textContent = '上传失败：' + data.error;
            statusEl.className = 'resume-status error';
            return;
        }

        hasResume = true;
        resumeText = data.raw_text || '';
        statusEl.textContent = '简历已关联：' + (data.filename || file.name);
        statusEl.className = 'resume-status success';
        updateResumeBadge();

    } catch (err) {
        statusEl.textContent = '连接失败：' + err.message;
        statusEl.className = 'resume-status error';
    }
}

// ===== 简历标记 =====
function updateResumeBadge() {
    const badge = document.getElementById('resume-badge');
    if (badge) {
        badge.style.display = hasResume ? 'inline-flex' : 'none';
    }
    const uploadArea = document.getElementById('interview-resume-upload-area');
    if (uploadArea) {
        uploadArea.style.display = hasResume ? 'none' : '';
    }
}

// ===== 显示简历下载按钮 =====
function showResumeDownloadBtn() {
    const downloadArea = document.getElementById('resume-download-area');
    if (downloadArea) {
        downloadArea.style.display = 'flex';
    }
}

// ===== 下载优化后的简历 =====
async function downloadModifiedResume() {
    const btn = document.getElementById('download-resume-btn');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<span class="spinner"></span> 生成中...';
    btn.disabled = true;

    try {
        // 1. 调用 AI 生成优化后的简历
        const resp = await fetch('/modify-resume', {
            method: 'POST',
            headers: authHeaders({ 'Content-Type': 'application/json' }),
            body: JSON.stringify({}),
        });
        const data = await resp.json();

        if (data.error) {
            alert('生成失败：' + data.error);
            btn.innerHTML = originalText;
            btn.disabled = false;
            return;
        }

        // 2. 触发下载
        const downloadUrl = data.download_url;
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = '优化后简历.docx';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);

        // 3. 在聊天区展示优化后的简历预览
        const previewMsg = document.createElement('div');
        previewMsg.className = 'message bot-message resume-preview';
        previewMsg.innerHTML = '<strong>优化后的简历已生成并开始下载</strong><br><br>' +
            data.improved_resume.replace(/\n/g, '<br>');
        document.getElementById('chat-box').appendChild(previewMsg);
        document.getElementById('chat-box').scrollTop = document.getElementById('chat-box').scrollHeight;

        btn.innerHTML = '已下载 ✓';
        setTimeout(() => {
            btn.innerHTML = originalText;
            btn.disabled = false;
        }, 3000);

    } catch (err) {
        alert('请求失败：' + err.message);
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

// ===== 会话管理 =====
let currentSessionId = Date.now().toString();

function getSessions() {
    try {
        return JSON.parse(localStorage.getItem('zpig_' + PAGE_TYPE + '_sessions') || '[]');
    } catch (e) {
        return [];
    }
}

function saveSessions(sessions) {
    localStorage.setItem('zpig_' + PAGE_TYPE + '_sessions', JSON.stringify(sessions));
}

function startNewSession(title) {
    // 保存当前会话
    const sessions = getSessions();
    if (sessions.length > 0 && sessions[0].messages && sessions[0].messages.length > 0) {
        // 当前会话有内容才保留
    }
    currentSessionId = Date.now().toString();
    const newSession = {
        id: currentSessionId,
        title: title || '新面试',
        date: new Date().toLocaleString('zh-CN'),
        messages: []
    };
    sessions.unshift(newSession);
    // 最多保留20条
    if (sessions.length > 20) sessions.pop();
    saveSessions(sessions);
    updateHistoryUI();
}

function saveHistoryItem(content, role) {
    const sessions = getSessions();
    let session = sessions.find(s => s.id === currentSessionId);
    if (!session) {
        session = {
            id: currentSessionId,
            title: content.slice(0, 20),
            date: new Date().toLocaleString('zh-CN'),
            messages: []
        };
        sessions.unshift(session);
    }
    session.messages.push({ role, content, time: new Date().toISOString() });
    // 用第一条用户消息作为标题
    if (role === 'user' && session.messages.filter(m => m.role === 'user').length === 1) {
        session.title = content.slice(0, 30);
    }
    if (sessions.length > 20) sessions.pop();
    saveSessions(sessions);
}

function updateHistoryUI() {
    const sessions = getSessions();
    const historyList = document.getElementById('history-list');
    const mobileHistoryList = document.getElementById('mobile-history-list');
    if (!historyList && !mobileHistoryList) return;

    if (sessions.length === 0) {
        const empty = '<p class="history-empty">暂无历史对话</p>';
        if (historyList) historyList.innerHTML = empty;
        if (mobileHistoryList) mobileHistoryList.innerHTML = empty;
        return;
    }

    const html = sessions.map((s, i) => `
        <div class="history-item ${s.id === currentSessionId ? 'active' : ''}" onclick="loadSession('${s.id}')">
            <div class="history-item-title">${escapeHtml(s.title)}</div>
            <div class="history-item-date">${s.date}</div>
            <button class="history-item-del" onclick="event.stopPropagation();deleteSession('${s.id}')" title="删除">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
                    <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
            </button>
        </div>
    `).join('');

    if (historyList) historyList.innerHTML = html;
    if (mobileHistoryList) mobileHistoryList.innerHTML = html;
}

function loadSession(sessionId) {
    const sessions = getSessions();
    const session = sessions.find(s => s.id === sessionId);
    if (!session || session.messages.length === 0) return;

    currentSessionId = sessionId;
    hideWelcome();
    const chatBox = document.getElementById('chat-box');
    chatBox.querySelectorAll('.message').forEach(m => m.remove());
    session.messages.forEach(msg => {
        const className = msg.role === 'user' ? 'user-message' : 'bot-message';
        addMessage(msg.content, className);
    });
    updateHistoryUI();
    // 手机端关闭抽屉
    const drawer = document.getElementById('mobile-drawer');
    if (drawer) drawer.classList.remove('open');
    const overlay = document.getElementById('mobile-drawer-overlay');
    if (overlay) overlay.classList.remove('open');
}

function deleteSession(sessionId) {
    let sessions = getSessions();
    sessions = sessions.filter(s => s.id !== sessionId);
    saveSessions(sessions);
    if (currentSessionId === sessionId) {
        startNewInterview();
    }
    updateHistoryUI();
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ===== 移动端抽屉 =====
function toggleMobileDrawer() {
    const drawer = document.getElementById('mobile-drawer');
    const overlay = document.getElementById('mobile-drawer-overlay');
    drawer.classList.toggle('open');
    overlay.classList.toggle('open');
}

// ===== 键盘事件 =====
document.getElementById('user-input').addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendInterviewMessage();
    }
});

// ===== 输入框自动增高 =====
document.getElementById('user-input').addEventListener('input', function () {
    this.style.height = 'auto';
    this.style.height = Math.min(this.scrollHeight, 150) + 'px';
});

function resetInputHeight() {
    const input = document.getElementById('user-input');
    input.style.height = 'auto';
}

// ===== 页面初始化 =====
async function initInterviewPage() {
    // 检查用户是否已上传简历
    try {
        const resp = await fetch('/get-resume', { headers: authHeaders() });
        const data = await resp.json();
        if (data.has_resume) {
            hasResume = true;
            resumeText = data.resume_text;
        }
    } catch (e) {
        // 忽略错误
    }
    updateResumeBadge();
    updateHistoryUI();
}

initInterviewPage();

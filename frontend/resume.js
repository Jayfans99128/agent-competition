// ===== 页面标识 =====
const PAGE_TYPE = 'resume';

// ===== 状态 =====
let selectedFile = null;
let analysisDone = false;

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

function ensureSession() {
    const sessions = getSessions();
    if (sessions.length === 0 || sessions[0].id !== currentSessionId) {
        const newSession = {
            id: currentSessionId,
            title: '简历分析',
            date: new Date().toLocaleString('zh-CN'),
            messages: []
        };
        sessions.unshift(newSession);
        if (sessions.length > 20) sessions.pop();
        saveSessions(sessions);
    }
}

function saveHistoryItem(content, role) {
    const sessions = getSessions();
    let session = sessions.find(s => s.id === currentSessionId);
    if (!session) {
        session = {
            id: currentSessionId,
            title: content.slice(0, 30),
            date: new Date().toLocaleString('zh-CN'),
            messages: []
        };
        sessions.unshift(session);
    }
    session.messages.push({ role, content, time: new Date().toISOString() });
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

    const html = sessions.map(s => `
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
    document.getElementById('upload-section').style.display = 'none';
    document.getElementById('resume-actions').style.display = 'flex';
    analysisDone = true;
    const chatBox = document.getElementById('chat-box');
    chatBox.querySelectorAll('.message').forEach(m => m.remove());
    session.messages.forEach(msg => {
        const className = msg.role === 'user' ? 'user-message' : 'bot-message';
        const messageDiv = document.createElement('div');
        messageDiv.classList.add('message', className);
        messageDiv.innerText = msg.content;
        chatBox.appendChild(messageDiv);
    });
    updateHistoryUI();
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
        resetResume();
    }
    updateHistoryUI();
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function toggleMobileDrawer() {
    const drawer = document.getElementById('mobile-drawer');
    const overlay = document.getElementById('mobile-drawer-overlay');
    drawer.classList.toggle('open');
    overlay.classList.toggle('open');
}

// ===== 文件选择 =====
function handleFileSelect(event) {
    const file = event.target.files[0];
    if (!file) return;

    selectedFile = file;
    document.getElementById('file-name').textContent = file.name;
    document.getElementById('analyze-btn').disabled = false;
    document.getElementById('upload-status').textContent = '';
}

// ===== 分析简历 =====
async function analyzeResume() {
    if (!selectedFile) return;

    const btn = document.getElementById('analyze-btn');
    const status = document.getElementById('upload-status');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> 分析中...';
    status.textContent = '';

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
        const resp = await fetch('/upload-resume', {
            method: 'POST',
            headers: authHeaders(),
            body: formData,
        });
        const data = await resp.json();

        if (data.error) {
            status.textContent = '错误：' + data.error;
            status.className = 'upload-status error';
            btn.disabled = false;
            btn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg> 开始分析';
            return;
        }

        document.getElementById('upload-section').style.display = 'none';
        document.getElementById('resume-actions').style.display = 'flex';
        analysisDone = true;
        showAnalysisResult(data);

    } catch (err) {
        status.textContent = '连接失败：' + err.message;
        status.className = 'upload-status error';
        btn.disabled = false;
        btn.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg> 开始分析';
    }
}

function showAnalysisResult(data) {
    const chatBox = document.getElementById('chat-box');

    const msg = document.createElement('div');
    msg.className = 'message bot-message resume-analysis';

    let html = '<strong>简历分析结果</strong><br><br>';

    if (data.analysis && !data.analysis.error) {
        const a = data.analysis;
        if (a.name) html += `<span class="resume-field">姓名：</span>${a.name}<br>`;

        if (a.education && a.education.length) {
            html += `<span class="resume-field">教育背景：</span><br>`;
            a.education.forEach(e => {
                if (typeof e === 'object') {
                    html += `&nbsp;&nbsp;${e.school || ''} · ${e.major || ''} · ${e.degree || ''} · ${e.time || ''}<br>`;
                } else {
                    html += `&nbsp;&nbsp;${e}<br>`;
                }
            });
        }

        if (a.skills && a.skills.length) {
            html += `<span class="resume-field">技能：</span>${a.skills.join('、')}<br>`;
        }

        if (a.projects && a.projects.length) {
            html += `<span class="resume-field">项目经历：</span><br>`;
            a.projects.forEach(p => {
                if (typeof p === 'object') {
                    html += `&nbsp;&nbsp;<b>${p.name || ''}</b>：${p.description || ''}<br>`;
                } else {
                    html += `&nbsp;&nbsp;${p}<br>`;
                }
            });
        }

        if (a.work_experience && a.work_experience.length) {
            html += `<span class="resume-field">工作经历：</span><br>`;
            a.work_experience.forEach(w => {
                if (typeof w === 'object') {
                    html += `&nbsp;&nbsp;<b>${w.company || ''}</b> · ${w.position || ''} · ${w.time || ''}<br>`;
                } else {
                    html += `&nbsp;&nbsp;${w}<br>`;
                }
            });
        }
    } else {
        html += '简历文本已提取，你可以在下方与我交流关于简历的任何问题。';
    }

    msg.innerHTML = html;
    chatBox.appendChild(msg);
    chatBox.scrollTop = chatBox.scrollHeight;
    saveHistoryItem(html, 'assistant');
}

// ===== 消息管理 =====
function addMessage(text, className) {
    const chatBox = document.getElementById('chat-box');
    const msg = document.createElement('div');
    msg.className = 'message ' + className;
    msg.innerText = text;
    chatBox.appendChild(msg);
    chatBox.scrollTop = chatBox.scrollHeight;
    return msg;
}

let typingEl = null;

function showTyping() {
    if (typingEl) return;
    const chatBox = document.getElementById('chat-box');
    typingEl = document.createElement('div');
    typingEl.className = 'message bot-message typing-indicator';
    typingEl.innerHTML = '<span class="dot"></span><span class="dot"></span><span class="dot"></span>';
    chatBox.appendChild(typingEl);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function hideTyping() {
    if (typingEl) { typingEl.remove(); typingEl = null; }
}

// ===== 流式发送消息 =====
async function sendResumeMessage() {
    const input = document.getElementById('user-input');
    const text = input.value.trim();
    if (!text) return;

    addMessage(text, 'user-message');
    ensureSession();
    saveHistoryItem(text, 'user');
    input.value = '';
    showTyping();

    try {
        const resp = await fetch('/resume-chat/stream', {
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
                    } catch (e) { /* ignore */ }
                }
            }
        }
        saveHistoryItem(fullReply, 'assistant');
        updateHistoryUI();
    } catch (err) {
        hideTyping();
        addMessage('连接后端失败，请确认服务已启动', 'bot-message');
    }
}

function resumeQuickAsk(text) {
    document.getElementById('user-input').value = text;
    sendResumeMessage();
}

// ===== 重置 =====
function resetResume() {
    selectedFile = null;
    analysisDone = false;
    document.getElementById('upload-section').style.display = '';
    document.getElementById('resume-actions').style.display = 'none';
    document.getElementById('file-name').textContent = '';
    document.getElementById('analyze-btn').disabled = true;
    document.getElementById('upload-status').textContent = '';
    document.getElementById('upload-status').className = 'upload-status';
    document.getElementById('file-input').value = '';
    document.getElementById('chat-box').querySelectorAll('.message').forEach(m => m.remove());
    currentSessionId = Date.now().toString();
    updateHistoryUI();
}

// ===== 加载历史记录 =====
async function loadResumeHistory() {
    try {
        const resp = await fetch('/resume-chat/history', { headers: authHeaders() });
        const data = await resp.json();
        if (data.messages && data.messages.length > 0) {
            document.getElementById('upload-section').style.display = 'none';
            document.getElementById('resume-actions').style.display = 'flex';
            analysisDone = true;
            data.messages.forEach(msg => {
                const className = msg.role === 'user' ? 'user-message' : 'bot-message';
                addMessage(msg.content, className);
            });
        }
    } catch (e) { /* ignore */ }
}

// ===== 键盘事件 =====
document.getElementById('user-input').addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendResumeMessage();
    }
});

// ===== 页面初始化 =====
loadResumeHistory();
updateHistoryUI();

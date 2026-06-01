// ===== 页面标识 =====
const PAGE_TYPE = 'chat';

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
            title: '新对话',
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
    hideWelcome();
    const chatBox = document.getElementById('chat-box');
    chatBox.querySelectorAll('.message').forEach(m => m.remove());
    session.messages.forEach(msg => {
        const className = msg.role === 'user' ? 'user-message' : 'bot-message';
        addMessage(msg.content, className);
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
        clearChat();
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
async function sendMessage() {
    const input = document.getElementById('user-input');
    const text = input.value.trim();
    if (!text) return;

    addMessage(text, 'user-message');
    ensureSession();
    saveHistoryItem(text, 'user');
    input.value = '';
    showTyping();

    try {
        const resp = await fetch('/chat/stream', {
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
    } catch (error) {
        hideTyping();
        addMessage('连接后端失败，请确认服务已启动', 'bot-message');
    }
}

// ===== 侧边栏功能切换 =====
function switchFeature(el, promptText) {
    document.querySelectorAll('.feature-item').forEach(item => item.classList.remove('active'));
    el.classList.add('active');
    quickAsk(promptText);
}

// ===== 快捷提问 =====
function quickAsk(text) {
    const input = document.getElementById('user-input');
    input.value = text;
    sendMessage();
}

// ===== 清空对话 =====
function clearChat() {
    const chatBox = document.getElementById('chat-box');
    chatBox.querySelectorAll('.message').forEach(m => m.remove());
    const welcome = document.querySelector('.welcome-section');
    if (welcome) {
        welcome.style.display = '';
    }
    welcomeVisible = true;
    currentSessionId = Date.now().toString();
    updateHistoryUI();
}

function startNewChat() {
    clearChat();
}

// ===== 加载历史记录 =====
async function loadHistory() {
    try {
        const resp = await fetch('/chat/history', { headers: authHeaders() });
        const data = await resp.json();
        if (data.messages && data.messages.length > 0) {
            hideWelcome();
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
        sendMessage();
    }
});

function toggleMenu() {
    const menu = document.getElementById('popupMenu');
    menu.style.display = menu.style.display === 'none' || menu.style.display === '' ? 'flex' : 'none';
}

function switchMode(mode) {
    console.log('切换模式:', mode);
    document.getElementById('popupMenu').style.display = 'none';
    if (mode === 'chat') {
        window.location.href = 'index.html';
    } else if (mode === 'resume') {
        window.location.href = 'resume.html';
    } else if (mode === 'interview') {
        window.location.href = 'interview.html';
    } else if (mode === 'job-search') {
        window.location.href = 'job-search.html';
    }
}

// ===== 页面初始化 =====
loadHistory();
updateHistoryUI();

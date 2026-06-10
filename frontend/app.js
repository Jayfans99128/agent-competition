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

// ===== 流式发送消息（含打断能力）=====
let abortController = null;

function setSendingState(sending) {
    const btn = document.getElementById('send-btn');
    if (!btn) return;
    if (sending) {
        btn.classList.add('sending');
        btn.innerHTML = `
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="22" height="22">
                <rect x="6" y="6" width="12" height="12" rx="2"/>
            </svg>
        `;
        btn.setAttribute('onclick', 'abortRequest()');
    } else {
        btn.classList.remove('sending');
        btn.innerHTML = `
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="22" height="22">
                <line x1="22" y1="2" x2="11" y2="13"/>
                <polygon points="22 2 15 22 11 13 2 9 22 2"/>
            </svg>
        `;
        btn.setAttribute('onclick', 'sendMessage()');
    }
}

function abortRequest() {
    if (abortController) {
        abortController.abort();
        abortController = null;
    }
    hideTyping();
    setSendingState(false);
}

async function sendMessage() {
    const input = document.getElementById('user-input');
    const text = input.value.trim();
    if (!text) return;

    // 如果已在发送中，不允许重复点击
    if (abortController) return;

    addMessage(text, 'user-message');
    ensureSession();
    saveHistoryItem(text, 'user');
    input.value = '';
    resetInputHeight();
    showTyping();
    setSendingState(true);

    abortController = new AbortController();

    try {
        const resp = await fetch('/chat/stream', {
            method: 'POST',
            headers: authHeaders({ 'Content-Type': 'application/json' }),
            body: JSON.stringify({ message: text }),
            signal: abortController.signal,
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

        if (fullReply.trim()) {
            saveHistoryItem(fullReply, 'assistant');
            updateHistoryUI();
        }
    } catch (error) {
        if (error.name === 'AbortError') {
            // 用户主动打断，不做额外提示
        } else {
            hideTyping();
            addMessage('连接后端失败，请确认服务已启动', 'bot-message');
        }
    } finally {
        abortController = null;
        setSendingState(false);
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

// ===== 输入框自动增高 =====
document.getElementById('user-input').addEventListener('input', function () {
    this.style.height = 'auto';
    this.style.height = Math.min(this.scrollHeight, 150) + 'px';
});

function resetInputHeight() {
    const input = document.getElementById('user-input');
    input.style.height = 'auto';
}

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

// ===== 职业性格测试（MBTI）=====
let testQuestions = [];
let testAnswers = {};
let testCurrentPage = 0;
let testPerPage = 5;

async function openPersonalityTest() {
    document.getElementById('popupMenu').style.display = 'none';
    const overlay = document.getElementById('testOverlay');
    const modal = document.getElementById('testModal');
    overlay.classList.add('open');
    modal.classList.add('open');
    document.getElementById('testBody').innerHTML = '<div class="test-loading">加载题目中...</div>';

    try {
        const resp = await fetch('/api/personality-test/questions', { headers: authHeaders() });
        const data = await resp.json();
        testQuestions = data.questions;
        testPerPage = data.perPage || 5;
        testAnswers = {};
        testCurrentPage = 0;
        renderTestPage(0);
    } catch (e) {
        document.getElementById('testBody').innerHTML = '<div class="test-loading">加载失败，请重试</div>';
    }
}

function closeTest() {
    document.getElementById('testOverlay').classList.remove('open');
    document.getElementById('testModal').classList.remove('open');
}

function renderTestPage(page) {
    const total = testQuestions.length;
    const perPage = testPerPage;
    const start = page * perPage;
    const end = Math.min(start + perPage, total);
    const pageQuestions = testQuestions.slice(start, end);
    const totalPages = Math.ceil(total / perPage);

    let html = `
        <div class="test-progress">
            <div class="test-progress-bar">
                <div class="test-progress-fill" style="width:${((page + 1) / totalPages) * 100}%"></div>
            </div>
            <span class="test-progress-text">${page + 1}/${totalPages}</span>
        </div>
        <div class="test-questions">
    `;

    pageQuestions.forEach(q => {
        const val = testAnswers[q.id] || '';
        html += `
            <div class="test-question">
                <div class="test-question-label">${q.id}. ${q.text}</div>
                <div class="test-options-mbti" data-qid="${q.id}">
                    <button class="test-opt-mbti ${val === 'A' ? 'active' : ''}" onclick="selectOption(${q.id}, 'A')">
                        <span class="mbti-opt-label">A</span>
                        <span class="mbti-opt-text">${q.optionA}</span>
                    </button>
                    <button class="test-opt-mbti ${val === 'B' ? 'active' : ''}" onclick="selectOption(${q.id}, 'B')">
                        <span class="mbti-opt-label">B</span>
                        <span class="mbti-opt-text">${q.optionB}</span>
                    </button>
                </div>
            </div>
        `;
    });

    html += `</div><div class="test-nav">`;

    if (page > 0) {
        html += `<button class="test-btn test-btn-prev" onclick="prevPage()">← 上一页</button>`;
    } else {
        html += `<div></div>`;
    }

    if (end < total) {
        const allAnswered = pageQuestions.every(q => testAnswers[q.id]);
        html += `<button class="test-btn test-btn-next" onclick="nextPage()" ${allAnswered ? '' : 'disabled'}>下一页 →</button>`;
    } else {
        const allAnswered = pageQuestions.every(q => testAnswers[q.id]);
        html += `<button class="test-btn test-btn-submit" onclick="submitTest()" ${allAnswered ? '' : 'disabled'}>查看结果</button>`;
    }

    html += '</div>';
    document.getElementById('testBody').innerHTML = html;
}

function selectOption(qid, value) {
    testAnswers[qid] = value;
    const container = document.querySelector(`.test-options-mbti[data-qid="${qid}"]`);
    if (container) {
        const btns = container.querySelectorAll('.test-opt-mbti');
        btns[0].classList.toggle('active', value === 'A');
        btns[1].classList.toggle('active', value === 'B');
    }
    // 更新按钮状态
    const total = testQuestions.length;
    const end = Math.min((testCurrentPage + 1) * testPerPage, total);
    const pageQuestions = testQuestions.slice(testCurrentPage * testPerPage, end);
    const allAnswered = pageQuestions.every(q => testAnswers[q.id]);

    if (end >= total) {
        const submitBtn = document.querySelector('.test-btn-submit');
        if (submitBtn) submitBtn.disabled = !allAnswered;
    }
    const nextBtn = document.querySelector('.test-btn-next');
    if (nextBtn) nextBtn.disabled = !allAnswered;
}

function nextPage() {
    testCurrentPage++;
    renderTestPage(testCurrentPage);
}

function prevPage() {
    testCurrentPage--;
    renderTestPage(testCurrentPage);
}

async function submitTest() {
    if (Object.keys(testAnswers).length < testQuestions.length) return;

    document.getElementById('testBody').innerHTML = '<div class="test-loading">分析中，请稍候...</div>';

    try {
        const resp = await fetch('/api/personality-test/result', {
            method: 'POST',
            headers: authHeaders({ 'Content-Type': 'application/json' }),
            body: JSON.stringify({ answers: testAnswers }),
        });
        const data = await resp.json();
        if (data.error) {
            document.getElementById('testBody').innerHTML = `<div class="test-loading">${data.error}</div>`;
            return;
        }
        renderResult(data);
    } catch (e) {
        document.getElementById('testBody').innerHTML = '<div class="test-loading">提交失败，请重试</div>';
    }
}

function renderResult(data) {
    let html = `
        <div class="test-result">
            <div class="test-result-code">${data.mbti_code}</div>
            <div class="test-result-hint">${data.type_name} — 你的 MBTI 性格类型</div>
            <p style="color:#cbd5e1;font-size:15px;line-height:1.7;margin-bottom:20px;text-align:left">${data.type_desc}</p>
            <div class="test-result-dims">
    `;

    data.dimensions.forEach(d => {
        const isA = d.winner === d.dim[0];
        const pctA = d.pctA;
        const pctB = d.pctB;
        html += `
            <div class="test-result-dim">
                <div class="test-result-dim-header">
                    <span class="test-result-dim-name">${d.winner_name}</span>
                    <span class="test-result-dim-score">${d.winner}</span>
                </div>
                <div class="test-result-dim-bar">
                    <div style="display:flex;gap:4px;height:8px">
                        <div style="flex:${pctA};background:${isA ? 'linear-gradient(90deg,#6366f1,#8b5cf6)' : 'rgba(255,255,255,0.10)'};border-radius:4px 0 0 4px;transition:width 0.8s"></div>
                        <div style="flex:${pctB};background:${!isA ? 'linear-gradient(90deg,#6366f1,#8b5cf6)' : 'rgba(255,255,255,0.10)'};border-radius:0 4px 4px 0;transition:width 0.8s"></div>
                    </div>
                </div>
                <div style="display:flex;justify-content:space-between;font-size:12px;color:#94a3b8;margin-bottom:6px">
                    <span>${d.descA}</span>
                    <span>${d.descB}</span>
                </div>
            </div>
        `;
    });

    html += `
            </div>
            <div class="test-result-careers" style="text-align:left;margin-bottom:20px">
                <p style="color:#cbd5e1;font-weight:600;margin-bottom:8px">🎯 推荐职业方向</p>
                ${data.careers.map(c => `<span>${c}</span>`).join('')}
            </div>
            <div class="test-nav">
                <button class="test-btn test-btn-restart" onclick="restartTest()">重新测试</button>
                <button class="test-btn test-btn-next" onclick="closeTest()">完成</button>
            </div>
        </div>
    `;

    document.getElementById('testBody').innerHTML = html;
}

function restartTest() {
    testAnswers = {};
    testCurrentPage = 0;
    renderTestPage(0);
}

// ===== 页面初始化 =====
loadHistory();
updateHistoryUI();

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
    input.value = '';
    showTyping();

    try {
        const resp = await fetch('/chat/stream', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text }),
        });

        hideTyping();

        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let botMsg = addMessage('', 'bot-message');
        let buffer = '';

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
                        botMsg.innerText += parsed.content;
                        document.getElementById('chat-box').scrollTop =
                            document.getElementById('chat-box').scrollHeight;
                    } catch (e) { /* ignore parse errors */ }
                }
            }
        }
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
}

// ===== 加载历史记录 =====
async function loadHistory() {
    try {
        const resp = await fetch('/chat/history');
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

// ===== 页面初始化 =====
loadHistory();

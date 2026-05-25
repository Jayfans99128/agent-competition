let jobWelcomeVisible = true;

function hideJobWelcome() {
    if (jobWelcomeVisible) {
        const welcome = document.querySelector('.welcome-section');
        if (welcome) welcome.style.display = 'none';
        jobWelcomeVisible = false;
    }
}

function addMessage(text, className) {
    hideJobWelcome();
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
    hideJobWelcome();
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
async function sendJobMessage() {
    const input = document.getElementById('user-input');
    const text = input.value.trim();
    if (!text) return;

    addMessage(text, 'user-message');
    input.value = '';
    showTyping();

    try {
        const resp = await fetch('/job-chat/stream', {
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
                    } catch (e) { /* ignore */ }
                }
            }
        }
    } catch (err) {
        hideTyping();
        addMessage('连接后端失败，请确认服务已启动', 'bot-message');
    }
}

function jobQuickAsk(text) {
    document.getElementById('user-input').value = text;
    sendJobMessage();
}

function clearJobChat() {
    document.getElementById('chat-box').querySelectorAll('.message').forEach(m => m.remove());
    const welcome = document.querySelector('.welcome-section');
    if (welcome) welcome.style.display = '';
    jobWelcomeVisible = true;
}

// ===== 加载历史记录 =====
async function loadJobHistory() {
    try {
        const resp = await fetch('/job-chat/history');
        const data = await resp.json();
        if (data.messages && data.messages.length > 0) {
            hideJobWelcome();
            data.messages.forEach(msg => {
                const className = msg.role === 'user' ? 'user-message' : 'bot-message';
                addMessage(msg.content, className);
            });
        }
    } catch (e) { /* ignore */ }
}

document.getElementById('user-input').addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendJobMessage();
    }
});

// ===== 页面初始化 =====
loadJobHistory();

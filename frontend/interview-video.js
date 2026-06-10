// ===== 沉浸式视频面试 — 视频通话模式 =====

// ----- 状态 -----
let interviewActive = false;
let isSpeaking = false;
let isListening = false;
let isMuted = false;
let hasResume = false;
let callStartTime = null;
let callTimerInterval = null;
let currentUtterance = null;
let speechRecognition = null;
let webcamStream = null;
let chatHistory = [];

// ----- 语音设置（localStorage 持久化）-----
let voiceSettings = {
    voiceName: localStorage.getItem('zpig_voice_name') || '',
    rate: parseFloat(localStorage.getItem('zpig_voice_rate') || '1.0'),
    pitch: parseFloat(localStorage.getItem('zpig_voice_pitch') || '1.05'),
};

function saveVoiceSettings() {
    localStorage.setItem('zpig_voice_name', voiceSettings.voiceName);
    localStorage.setItem('zpig_voice_rate', voiceSettings.rate);
    localStorage.setItem('zpig_voice_pitch', voiceSettings.pitch);
}

// ----- DOM 引用 -----
const videoStage = document.getElementById('video-stage');
const videoTypes = document.getElementById('video-types');
const remoteImg = document.getElementById('remote-img');
const speakRing = document.getElementById('vc-speak-ring');
const vcNameDot = document.getElementById('vc-name-dot');
const vcNameLabel = document.getElementById('vc-name-label');
const interviewerText = document.getElementById('interviewer-text');
const interviewerSubtitle = document.getElementById('interviewer-subtitle');
const userSubtitle = document.getElementById('user-subtitle');
const userTextEl = document.getElementById('user-text');
const statusDot = document.getElementById('status-dot');
const statusText = document.getElementById('status-text');
const callTimer = document.getElementById('call-timer');
const btnMic = document.getElementById('btn-mic');
const btnMute = document.getElementById('btn-mute');
const videoChatMessages = document.getElementById('video-chat-messages');
const pipWebcam = document.getElementById('pip-webcam');
const pipPlaceholder = document.getElementById('pip-placeholder');

// ----- 初始化 -----
async function initVideoPage() {
    // 检查简历关联
    try {
        const resp = await fetch('/get-resume', { headers: authHeaders() });
        const data = await resp.json();
        hasResume = data.has_resume;
    } catch (e) {}

    // 初始化语音识别
    initSpeechRecognition();

    // 初始化语音合成
    if (window.speechSynthesis) {
        speechSynthesis.getVoices();
        speechSynthesis.onvoiceschanged = () => speechSynthesis.getVoices();
    }

    // 键盘事件：空格键按住说话
    document.addEventListener('keydown', (e) => {
        if (e.code === 'Space' && !isListening && !isSpeaking && interviewActive &&
            document.activeElement !== document.getElementById('video-text-input')) {
            e.preventDefault();
            startListening();
        }
    });
    document.addEventListener('keyup', (e) => {
        if (e.code === 'Space' && isListening) {
            e.preventDefault();
            stopListening();
        }
    });
}

// ----- 摄像头（PIP 小窗口） -----
async function startWebcam() {
    try {
        webcamStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
        pipWebcam.srcObject = webcamStream;
        pipWebcam.style.display = 'block';
        pipPlaceholder.style.display = 'none';
    } catch (e) {
        // 没有摄像头就用占位符
        pipWebcam.style.display = 'none';
        pipPlaceholder.style.display = 'flex';
    }
}

function stopWebcam() {
    if (webcamStream) {
        webcamStream.getTracks().forEach(t => t.stop());
        webcamStream = null;
    }
    pipWebcam.style.display = 'none';
    pipPlaceholder.style.display = 'flex';
}

// ----- 通话计时 -----
function startCallTimer() {
    callStartTime = Date.now();
    callTimer.style.display = 'inline';
    callTimerInterval = setInterval(() => {
        const elapsed = Math.floor((Date.now() - callStartTime) / 1000);
        const m = String(Math.floor(elapsed / 60)).padStart(2, '0');
        const s = String(elapsed % 60).padStart(2, '0');
        callTimer.textContent = m + ':' + s;
    }, 1000);
}

function stopCallTimer() {
    if (callTimerInterval) clearInterval(callTimerInterval);
    callTimer.style.display = 'none';
}

// ===== 语音合成 TTS =====
function getSelectedVoice() {
    const voices = speechSynthesis.getVoices();
    if (!voices.length) return null;

    // 用户保存的首选声音
    if (voiceSettings.voiceName) {
        const saved = voices.find(v => v.name === voiceSettings.voiceName);
        if (saved) return saved;
    }

    // 默认：中文女声
    return voices.find(v => v.lang.startsWith('zh-CN') && v.name.includes('Female')) ||
           voices.find(v => v.lang.startsWith('zh-CN')) ||
           voices.find(v => v.lang.startsWith('zh-HK')) ||
           voices.find(v => v.lang.startsWith('zh-TW')) ||
           voices.find(v => v.lang.startsWith('zh')) ||
           null;
}

function speakText(text) {
    if (isMuted || !window.speechSynthesis) {
        simulateQuickSpeak(text);
        return;
    }

    speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = 'zh-CN';
    utterance.rate = voiceSettings.rate;
    utterance.pitch = voiceSettings.pitch;
    utterance.volume = 1.0;

    const voice = getSelectedVoice();
    if (voice) utterance.voice = voice;

    currentUtterance = utterance;

    utterance.onstart = () => {
        isSpeaking = true;
        setSpeakingState(true);
        statusText.textContent = '面试官正在提问...';
        statusDot.className = 'status-dot speaking';
        vcNameLabel.textContent = 'AI 面试官 · 说话中';
    };

    utterance.onend = () => {
        isSpeaking = false;
        currentUtterance = null;
        setSpeakingState(false);
        statusText.textContent = '按住空格键或点击麦克风回答';
        statusDot.className = 'status-dot listening';
        vcNameLabel.textContent = 'AI 面试官';
        if (interviewActive && !isMuted) {
            setTimeout(() => startListening(), 500);
        }
    };

    utterance.onerror = (e) => {
        if (e.error !== 'canceled' && e.error !== 'interrupted') {
            console.warn('TTS:', e.error);
        }
        isSpeaking = false;
        currentUtterance = null;
        setSpeakingState(false);
    };

    speechSynthesis.speak(utterance);
}

function simulateQuickSpeak(text) {
    isSpeaking = true;
    setSpeakingState(true);
    statusText.textContent = '面试官正在提问...';
    vcNameLabel.textContent = 'AI 面试官 · 说话中';
    const duration = Math.min(text.length * 50, 4000);
    setTimeout(() => {
        isSpeaking = false;
        setSpeakingState(false);
        vcNameLabel.textContent = 'AI 面试官';
        statusText.textContent = '请输入你的回答';
    }, duration);
}

function setSpeakingState(active) {
    if (active) {
        remoteImg.classList.add('talking');
        speakRing.classList.add('active');
        vcNameDot.classList.add('speaking-hide');
    } else {
        remoteImg.classList.remove('talking');
        speakRing.classList.remove('active');
        vcNameDot.classList.remove('speaking-hide');
    }
}

function toggleMute() {
    isMuted = !isMuted;
    if (isMuted) {
        btnMute.classList.add('active');
        if (window.speechSynthesis) speechSynthesis.cancel();
        statusText.textContent = '已静音 · 文字模式';
    } else {
        btnMute.classList.remove('active');
        statusText.textContent = '语音模式';
    }
}

// ===== 语音识别 STT =====
function initSpeechRecognition() {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) return;

    speechRecognition = new SR();
    speechRecognition.lang = 'zh-CN';
    speechRecognition.interimResults = true;
    speechRecognition.continuous = true;
    speechRecognition.maxAlternatives = 1;

    let interimText = '';

    speechRecognition.onresult = (event) => {
        let final = '';
        let interim = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {
            if (event.results[i].isFinal) final += event.results[i][0].transcript;
            else interim += event.results[i][0].transcript;
        }
        if (final) {
            interimText = '';
            const answer = final.trim();
            if (answer) {
                showUserAnswer(answer);
                processUserAnswer(answer);
            }
        } else if (interim) {
            interimText = interim;
            userSubtitle.style.display = 'block';
            userTextEl.textContent = interim + '...';
        }
    };

    speechRecognition.onend = () => {
        isListening = false;
        btnMic.classList.remove('active', 'listening');
        if (interviewActive && !isSpeaking) {
            statusText.textContent = '点击麦克风或按空格键回答';
            statusDot.className = 'status-dot listening';
        }
        if (interimText && interviewActive) {
            const answer = interimText.trim();
            if (answer) {
                showUserAnswer(answer);
                processUserAnswer(answer);
            }
            interimText = '';
        }
    };

    speechRecognition.onerror = (e) => {
        isListening = false;
        btnMic.classList.remove('active', 'listening');
        if (e.error !== 'no-speech' && e.error !== 'aborted') {
            statusText.textContent = '识别出错，请用文字输入';
        }
    };
}

function toggleMicrophone() {
    isListening ? stopListening() : startListening();
}

function startListening() {
    if (!speechRecognition || isSpeaking || isListening) return;
    try {
        speechRecognition.start();
        isListening = true;
        btnMic.classList.add('active', 'listening');
        statusText.textContent = '正在聆听...';
        statusDot.className = 'status-dot listening';
        userSubtitle.style.display = 'block';
        userTextEl.textContent = '...';
    } catch (e) {}
}

function stopListening() {
    if (speechRecognition && isListening) {
        try { speechRecognition.stop(); } catch (e) {}
    }
    isListening = false;
    btnMic.classList.remove('active', 'listening');
}

// ===== 文字输入（备用） =====
function toggleTextInput() {
    const area = document.getElementById('video-text-input-area');
    const show = area.style.display === 'none';
    area.style.display = show ? 'flex' : 'none';
    if (show) document.getElementById('video-text-input').focus();
}

function sendTextAnswer() {
    const input = document.getElementById('video-text-input');
    const text = input.value.trim();
    if (!text || isSpeaking) return;
    input.value = '';
    input.style.height = 'auto';
    showUserAnswer(text);
    processUserAnswer(text);
}

// 输入框自动增高
document.addEventListener('DOMContentLoaded', () => {
    const ti = document.getElementById('video-text-input');
    if (ti) {
        ti.addEventListener('input', function () {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 100) + 'px';
        });
        ti.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendTextAnswer();
            }
        });
    }
});

// ===== 面试流程 =====
async function startVideoInterview(type) {
    interviewActive = true;
    videoTypes.style.display = 'none';
    videoStage.style.display = 'flex';
    chatHistory = [];
    interviewerSubtitle.style.display = 'block';

    // 开启摄像头 + 计时
    startWebcam();
    startCallTimer();
    statusText.textContent = '正在连接面试官...';
    statusDot.className = 'status-dot';

    let prompt = '我想练习【' + type + '】，请先确认我的专业和目标岗位，然后开始正式的模拟面试。每次只问一个问题，问题简短清晰，适合语音交流。';
    if (hasResume) {
        prompt = '我想练习【' + type + '】，请根据我的简历内容进行有针对性的面试提问。每次只问一个问题，问题简短清晰，适合语音交流。';
    }

    try {
        const fullReply = await sendToInterview(prompt);
        if (fullReply) {
            showInterviewerMessage(fullReply);
            speakText(fullReply);
        }
    } catch (e) {
        statusText.textContent = '连接失败：' + e.message;
    }
}

async function processUserAnswer(answer) {
    if (!interviewActive || isSpeaking) return;
    stopListening();
    statusText.textContent = '面试官思考中...';
    statusDot.className = 'status-dot thinking';
    interviewerText.textContent = '...';

    try {
        const fullReply = await sendToInterview(answer);
        if (fullReply) {
            showInterviewerMessage(fullReply);
            speakText(fullReply);
        }
    } catch (e) {
        statusText.textContent = '连接失败：' + e.message;
    }
}

async function sendToInterview(message) {
    const resp = await fetch('/interview/stream', {
        method: 'POST',
        headers: authHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ message }),
    });

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
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
                    interviewerText.textContent = fullReply;
                } catch (e) {}
            }
        }
    }
    return fullReply.trim();
}

let _userSubtitleTimer = null;

function showUserAnswer(text) {
    // 清除上一次的隐藏定时器
    if (_userSubtitleTimer) clearTimeout(_userSubtitleTimer);
    userSubtitle.classList.remove('fading');
    userSubtitle.style.display = 'block';
    userTextEl.textContent = text;
    // 保存到对话记录
    chatHistory.push({ role: 'user', content: text });
    addChatRecord('user', text);
    // 5 秒后淡出消失
    _userSubtitleTimer = setTimeout(() => {
        userSubtitle.classList.add('fading');
        _userSubtitleTimer = setTimeout(() => {
            userSubtitle.style.display = 'none';
            userSubtitle.classList.remove('fading');
        }, 500);
    }, 5000);
}

function showInterviewerMessage(text) {
    interviewerSubtitle.style.display = 'block';
    interviewerText.textContent = text;
    chatHistory.push({ role: 'assistant', content: text });
    addChatRecord('assistant', text);
}

// ===== 对话记录 =====
function toggleChatPanel() {
    const panel = document.getElementById('video-chat-panel');
    panel.style.display = panel.style.display === 'none' ? 'flex' : 'none';
}

function addChatRecord(role, text) {
    const div = document.createElement('div');
    div.className = 'vc-message ' + role;
    div.innerHTML = `<span class="vc-msg-label">${role === 'assistant' ? '🤖 面试官' : '🎤 你'}</span><p>${text}</p>`;
    videoChatMessages.appendChild(div);
    videoChatMessages.scrollTop = videoChatMessages.scrollHeight;
}

// ===== 结束面试 =====
async function endVideoInterview() {
    if (!interviewActive) {
        window.location.href = 'interview.html';
        return;
    }

    interviewActive = false;
    stopListening();
    stopWebcam();
    stopCallTimer();
    if (window.speechSynthesis) speechSynthesis.cancel();
    setSpeakingState(false);
    statusText.textContent = '正在生成面试评价...';
    interviewerSubtitle.style.display = 'block';

    const closingMsg = hasResume
        ? '面试官你好，我想结束本轮面试，请给我一个总体评价，并针对我的简历给出具体的修改建议。'
        : '面试官你好，我想结束本轮面试，请给我一个总体评价和建议。';

    try {
        const fullReply = await sendToInterview(closingMsg);
        if (fullReply) {
            showInterviewerMessage(fullReply);
            speakText(fullReply);
        }
    } catch (e) {}

    statusText.textContent = '面试已结束';
    statusDot.className = 'status-dot';
}

// ===== 语音设置面板 =====
function toggleVoiceSettings() {
    const panel = document.getElementById('voice-settings-panel');
    const overlay = document.getElementById('voice-settings-overlay');
    const show = panel.style.display === 'none';
    panel.style.display = show ? 'flex' : 'none';
    overlay.style.display = show ? 'block' : 'none';
    if (show) populateVoiceList();
}

function populateVoiceList() {
    const voices = speechSynthesis.getVoices();
    // 确保 voices 已加载
    if (!voices.length) {
        speechSynthesis.onvoiceschanged = () => populateVoiceList();
        return;
    }

    const select = document.getElementById('voice-select');
    const zhVoices = voices.filter(v =>
        v.lang.startsWith('zh-CN') || v.lang.startsWith('zh-HK') ||
        v.lang.startsWith('zh-TW') || v.lang.startsWith('zh')
    );

    select.innerHTML = zhVoices.map(v => {
        const selected = v.name === voiceSettings.voiceName ? ' selected' : '';
        const label = `${v.name} (${v.lang})`;
        return `<option value="${v.name}"${selected}>${label}</option>`;
    }).join('');

    // 如果没有中文语音，显示所有
    if (!zhVoices.length) {
        select.innerHTML = voices.map(v => {
            const selected = v.name === voiceSettings.voiceName ? ' selected' : '';
            return `<option value="${v.name}"${selected}>${v.name} (${v.lang})</option>`;
        }).join('');
    }

    document.getElementById('voice-rate-val').textContent = voiceSettings.rate.toFixed(1) + 'x';
    document.getElementById('voice-rate').value = voiceSettings.rate;
    document.getElementById('voice-pitch-val').textContent = voiceSettings.pitch.toFixed(2);
    document.getElementById('voice-pitch').value = voiceSettings.pitch;
}

function onVoiceChange() {
    const select = document.getElementById('voice-select');
    voiceSettings.voiceName = select.value;
    saveVoiceSettings();
    previewVoice();
}

function onRateChange() {
    voiceSettings.rate = parseFloat(document.getElementById('voice-rate').value);
    document.getElementById('voice-rate-val').textContent = voiceSettings.rate.toFixed(1) + 'x';
    saveVoiceSettings();
}

function onPitchChange() {
    voiceSettings.pitch = parseFloat(document.getElementById('voice-pitch').value);
    document.getElementById('voice-pitch-val').textContent = voiceSettings.pitch.toFixed(2);
    saveVoiceSettings();
}

function previewVoice() {
    const utterance = new SpeechSynthesisUtterance('你好，我是你的AI面试官，这是我的声音。');
    utterance.lang = 'zh-CN';
    utterance.rate = voiceSettings.rate;
    utterance.pitch = voiceSettings.pitch;
    const voice = getSelectedVoice();
    if (voice) utterance.voice = voice;
    speechSynthesis.cancel();
    speechSynthesis.speak(utterance);
}

// ===== 初始化 =====
initVideoPage();

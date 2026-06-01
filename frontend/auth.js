// ===== 用户识别模块 =====

function getUserId() {
    let userId = localStorage.getItem('zpig_user_id');
    if (!userId) {
        userId = 'user_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        localStorage.setItem('zpig_user_id', userId);
    }
    return userId;
}

function getUserName() {
    return localStorage.getItem('zpig_user_name') || '';
}

function setUserName(name) {
    localStorage.setItem('zpig_user_name', name);
}

function authHeaders(extra = {}) {
    return Object.assign({ 'X-User-Id': getUserId() }, extra);
}

function updateUserDisplay() {
    const el = document.getElementById('current-user-name');
    if (el) el.textContent = getUserName() || '未设置昵称';
}

function showLoginDialog() {
    const name = prompt('请输入你的昵称，以便区分不同用户的对话：');
    if (name && name.trim()) {
        setUserName(name.trim());
        updateUserDisplay();
    }
}

function changeUser() {
    if (confirm('切换用户将使用新的身份，之前的对话记录仍然保留。确定吗？')) {
        localStorage.removeItem('zpig_user_id');
        localStorage.removeItem('zpig_user_name');
        location.reload();
    }
}

// 页面加载时检查
(function () {
    if (!getUserName()) {
        showLoginDialog();
    }
    document.addEventListener('DOMContentLoaded', updateUserDisplay);
})();

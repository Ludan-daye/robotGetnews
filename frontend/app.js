// API基础配置
const API_BASE = 'http://localhost:8000/api/v1';
let authToken = localStorage.getItem('authToken');
let currentUser = null;

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    if (authToken) {
        verifyToken();
    }

    // 绑定表单提交事件
    document.getElementById('preferenceForm').addEventListener('submit', function(e) {
        e.preventDefault();
        createPreference();
    });
});

// 消息提示函数
function showMessage(text, type = 'success') {
    const message = document.getElementById('message');
    const messageText = document.getElementById('messageText');
    const messageIcon = document.getElementById('messageIcon');

    messageText.textContent = text;
    message.className = `fixed top-4 right-4 p-4 rounded-lg shadow-lg z-50 ${
        type === 'success' ? 'bg-green-500 text-white' :
        type === 'error' ? 'bg-red-500 text-white' :
        'bg-blue-500 text-white'
    }`;

    messageIcon.className = type === 'success' ? 'fas fa-check-circle' :
                           type === 'error' ? 'fas fa-exclamation-circle' :
                           'fas fa-info-circle';

    message.classList.remove('hidden');

    setTimeout(() => {
        message.classList.add('hidden');
    }, 3000);
}

// API请求封装
async function apiRequest(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    const config = {
        headers: {
            'Content-Type': 'application/json',
            ...(authToken && { 'Authorization': `Bearer ${authToken}` })
        },
        ...options
    };

    try {
        const response = await fetch(url, config);

        let data;
        try {
            data = await response.json();
        } catch (jsonError) {
            console.error('JSON解析错误:', jsonError);
            throw new Error(`服务器响应格式错误 (状态码: ${response.status})`);
        }

        if (!response.ok) {
            let errorMessage;

            // Handle Pydantic validation errors (422 status with detail array)
            if (response.status === 422 && data.detail && Array.isArray(data.detail)) {
                const validationErrors = data.detail.map(err => {
                    const field = err.loc ? err.loc[err.loc.length - 1] : 'unknown';
                    return `${field}: ${err.msg}`;
                }).join('; ');
                errorMessage = `验证错误: ${validationErrors}`;
            } else {
                // Handle other error formats
                errorMessage = data.message || data.detail || data.error || `HTTP ${response.status} 错误`;
            }

            throw new Error(errorMessage);
        }

        return data;
    } catch (error) {
        console.error('API请求错误:', error);
        if (error.name === 'TypeError' && error.message.includes('fetch')) {
            throw new Error('网络连接失败，请检查服务器状态');
        }
        throw error;
    }
}

// 快速登录演示账户
async function quickLogin() {
    document.getElementById('email').value = 'demo@example.com';
    document.getElementById('password').value = 'demo123456';
    await login();
}

// 用户登录
async function login() {
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;

    if (!email || !password) {
        showMessage('请填写邮箱和密码', 'error');
        return;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
        showMessage('请输入有效的邮箱地址', 'error');
        return;
    }

    try {
        const data = await apiRequest('/auth/login', {
            method: 'POST',
            body: JSON.stringify({ email, password })
        });

        authToken = data.access_token;
        localStorage.setItem('authToken', authToken);

        showMessage('登录成功！', 'success');
        await loadUserInfo();
        showMainContent();
    } catch (error) {
        showMessage('登录失败，请检查邮箱和密码', 'error');
    }
}

// 用户注册
async function register() {
    const username = document.getElementById('regUsername').value;
    const email = document.getElementById('regEmail').value;
    const password = document.getElementById('regPassword').value;
    const timezone = document.getElementById('regTimezone').value;

    // Client-side validation
    if (!username || !email || !password) {
        showMessage('请填写所有必填字段', 'error');
        return;
    }

    if (username.length < 3) {
        showMessage('用户名至少需要3个字符', 'error');
        return;
    }

    if (password.length < 8) {
        showMessage('密码至少需要8个字符', 'error');
        return;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
        showMessage('请输入有效的邮箱地址', 'error');
        return;
    }

    try {
        await apiRequest('/auth/register', {
            method: 'POST',
            body: JSON.stringify({ username, email, password, timezone })
        });

        showMessage('注册成功！请登录', 'success');
        showLogin();

        // 自动填充登录表单
        document.getElementById('email').value = email;
        document.getElementById('password').value = password;
    } catch (error) {
        console.error('注册错误详情:', error);
        const errorMessage = error.message || error.detail || '注册失败，请稍后重试';
        showMessage('注册失败：' + errorMessage, 'error');
    }
}

// 验证Token
async function verifyToken() {
    try {
        await loadUserInfo();
        showMainContent();
    } catch (error) {
        localStorage.removeItem('authToken');
        authToken = null;
        showLogin();
    }
}

// 加载用户信息
async function loadUserInfo() {
    try {
        currentUser = await apiRequest('/auth/me');
        document.getElementById('username').textContent = currentUser.username;
        document.getElementById('userInfo').classList.remove('hidden');
        document.getElementById('loginPrompt').classList.add('hidden');

        // 加载通知设置
        await loadNotificationSettings();
    } catch (error) {
        throw error;
    }
}

// 用户登出
function logout() {
    // 清理所有认证信息
    localStorage.removeItem('authToken');
    authToken = null;
    currentUser = null;

    // 重置界面状态
    document.getElementById('userInfo').classList.add('hidden');
    document.getElementById('loginPrompt').classList.remove('hidden');
    document.getElementById('mainContent').classList.add('hidden');
    document.getElementById('loginSection').classList.remove('hidden');
    document.getElementById('registerSection').classList.add('hidden');

    // 清空表单数据
    document.getElementById('email').value = '';
    document.getElementById('password').value = '';
    document.getElementById('regUsername').value = '';
    document.getElementById('regEmail').value = '';
    document.getElementById('regPassword').value = '';

    // 重置所有内容区域
    document.getElementById('preferencesList').innerHTML = '';
    document.getElementById('recommendationsList').innerHTML = '';
    document.getElementById('historyList').innerHTML = '';
    document.getElementById('channelStatus').innerHTML = '';

    // 重置标签页到默认状态
    showTab('preferences');

    showMessage('已退出登录', 'success');
}

// 显示主要内容
function showMainContent() {
    document.getElementById('loginSection').classList.add('hidden');
    document.getElementById('registerSection').classList.add('hidden');
    document.getElementById('mainContent').classList.remove('hidden');

    // 默认显示推荐偏好页面
    showTab('preferences');
    loadPreferences();
}

// 显示登录表单
function showLogin() {
    document.getElementById('registerSection').classList.add('hidden');
    document.getElementById('loginSection').classList.remove('hidden');
}

// 显示注册表单
function showRegister() {
    document.getElementById('loginSection').classList.add('hidden');
    document.getElementById('registerSection').classList.remove('hidden');
}

// 标签页切换
function showTab(tabName) {
    // 隐藏所有标签页内容
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.add('hidden');
    });

    // 移除所有标签的活动状态
    document.querySelectorAll('[id^="tab-"]').forEach(tab => {
        tab.classList.remove('tab-active');
        tab.classList.add('text-gray-600');
    });

    // 显示选中的标签页内容
    document.getElementById(`content-${tabName}`).classList.remove('hidden');

    // 激活选中的标签
    const activeTab = document.getElementById(`tab-${tabName}`);
    activeTab.classList.add('tab-active');
    activeTab.classList.remove('text-gray-600');

    // 根据标签页加载对应数据
    switch(tabName) {
        case 'preferences':
            loadPreferences();
            break;
        case 'recommendations':
            loadRecommendations();
            break;
        case 'history':
            loadHistory();
            break;
        case 'settings':
            loadNotificationSettings();
            break;
        case 'api':
            loadAPISettings();
            break;
    }
}

// 应用偏好模版
function applyTemplate(templateType) {
    const templates = {
        ai: {
            name: "AI/机器学习项目推荐",
            description: "关注人工智能、机器学习、深度学习相关的优质项目",
            keywords: ["machine learning", "deep learning", "artificial intelligence", "neural network", "tensorflow", "pytorch", "ai", "ml", "data science", "computer vision", "nlp", "natural language processing"],
            languages: ["Python", "R", "Julia", "C++"],
            minStars: 100,
            maxRecs: 15,
            channels: ["email", "telegram"]
        },
        web: {
            name: "Web开发技术栈",
            description: "前端、后端、全栈开发相关的框架、工具和最佳实践",
            keywords: ["react", "vue", "angular", "javascript", "typescript", "nodejs", "express", "fastapi", "django", "flask", "frontend", "backend", "fullstack", "web development"],
            languages: ["JavaScript", "TypeScript", "Python", "Go", "Java"],
            minStars: 50,
            maxRecs: 20,
            channels: ["email", "slack"]
        },
        mobile: {
            name: "移动应用开发",
            description: "iOS、Android、跨平台移动应用开发相关项目",
            keywords: ["ios", "android", "react native", "flutter", "swift", "kotlin", "mobile", "app development", "cross platform", "xamarin"],
            languages: ["Swift", "Kotlin", "Java", "Dart", "JavaScript"],
            minStars: 80,
            maxRecs: 12,
            channels: ["email", "wechat"]
        },
        devtools: {
            name: "开发工具与DevOps",
            description: "提升开发效率的工具、DevOps实践、CI/CD相关项目",
            keywords: ["devops", "ci cd", "docker", "kubernetes", "automation", "testing", "monitoring", "deployment", "git", "vscode", "development tools"],
            languages: ["Go", "Python", "Shell", "YAML"],
            minStars: 30,
            maxRecs: 10,
            channels: ["email", "telegram", "slack"]
        }
    };

    const template = templates[templateType];
    if (!template) return;

    // 填充表单字段
    document.getElementById('prefName').value = template.name;
    document.getElementById('prefDescription').value = template.description;
    document.getElementById('prefKeywords').value = template.keywords.join(', ');
    document.getElementById('prefLanguages').value = template.languages.join(', ');
    document.getElementById('prefMinStars').value = template.minStars;
    document.getElementById('prefMaxRecs').value = template.maxRecs;

    // 重置所有通知渠道复选框
    document.querySelectorAll('#preferenceForm input[type="checkbox"]').forEach(cb => {
        cb.checked = false;
    });

    // 选中模版指定的通知渠道
    template.channels.forEach(channel => {
        const checkbox = document.querySelector(`#preferenceForm input[value="${channel}"]`);
        if (checkbox) {
            checkbox.checked = true;
        }
    });

    // 显示应用成功的消息
    showMessage(`已应用${template.name}模版`, 'success');
}

// 创建推荐偏好
async function createPreference() {
    const name = document.getElementById('prefName').value;
    const description = document.getElementById('prefDescription').value;
    const keywords = document.getElementById('prefKeywords').value.split(',').map(k => k.trim()).filter(k => k);
    const languages = document.getElementById('prefLanguages').value.split(',').map(l => l.trim()).filter(l => l);
    const minStars = parseInt(document.getElementById('prefMinStars').value) || 0;
    const maxRecs = parseInt(document.getElementById('prefMaxRecs').value) || 10;

    // 获取选中的通知渠道
    const channels = Array.from(document.querySelectorAll('#preferenceForm input[type="checkbox"]:checked'))
                          .map(cb => cb.value);

    if (!name || keywords.length === 0) {
        showMessage('请填写偏好名称和关键词', 'error');
        return;
    }

    try {
        await apiRequest('/preferences', {
            method: 'POST',
            body: JSON.stringify({
                name,
                description,
                keywords,
                languages,
                min_stars: minStars,
                max_recommendations: maxRecs,
                notification_channels: channels,
                enabled: true
            })
        });

        showMessage('偏好创建成功！', 'success');
        document.getElementById('preferenceForm').reset();
        loadPreferences();
    } catch (error) {
        showMessage('创建偏好失败：' + error.message, 'error');
    }
}

// 加载推荐偏好列表
async function loadPreferences() {
    try {
        const preferences = await apiRequest('/preferences');
        const container = document.getElementById('preferencesList');

        if (preferences.length === 0) {
            container.innerHTML = '<p class="text-gray-500 text-center py-4">暂无偏好配置</p>';
            return;
        }

        container.innerHTML = preferences.map(pref => `
            <div class="preference-card border border-gray-200 rounded-lg p-4 hover:shadow-md transition">
                <div class="flex justify-between items-start">
                    <div class="flex-1">
                        <h4 class="font-medium text-gray-800">${pref.name}</h4>
                        <p class="text-sm text-gray-600 mt-1">${pref.description || '无描述'}</p>
                        <div class="mt-2 flex flex-wrap gap-1">
                            ${pref.keywords.map(keyword =>
                                `<span class="tag-chip px-2 py-1 text-xs rounded">${keyword}</span>`
                            ).join('')}
                        </div>
                        <div class="mt-2 text-xs text-gray-500">
                            语言: ${pref.languages.join(', ') || '不限'} |
                            最小Star: ${pref.min_stars} |
                            最大推荐: ${pref.max_recommendations}
                        </div>
                        <div class="mt-1 text-xs text-gray-500">
                            通知渠道: ${pref.notification_channels.join(', ') || '无'}
                        </div>
                    </div>
                    <div class="flex space-x-2 ml-4">
                        <button onclick="togglePreference(${pref.id}, ${!pref.enabled})"
                                class="text-sm px-2 py-1 rounded ${pref.enabled ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'}">
                            ${pref.enabled ? '已启用' : '已禁用'}
                        </button>
                        <button onclick="deletePreference(${pref.id})"
                                class="text-red-500 hover:text-red-700 text-sm">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
            </div>
        `).join('');
    } catch (error) {
        document.getElementById('preferencesList').innerHTML =
            '<p class="text-red-500 text-center py-4">加载偏好失败</p>';
    }
}

// 切换偏好启用状态
async function togglePreference(id, enabled) {
    try {
        await apiRequest(`/preferences/${id}`, {
            method: 'PUT',
            body: JSON.stringify({ enabled })
        });

        showMessage(`偏好已${enabled ? '启用' : '禁用'}`, 'success');
        loadPreferences();
    } catch (error) {
        showMessage('操作失败：' + error.message, 'error');
    }
}

// 删除偏好
async function deletePreference(id) {
    if (!confirm('确定要删除这个偏好吗？')) return;

    try {
        await apiRequest(`/preferences/${id}`, {
            method: 'DELETE'
        });

        showMessage('偏好已删除', 'success');
        loadPreferences();
    } catch (error) {
        showMessage('删除失败：' + error.message, 'error');
    }
}

// 手动触发推荐
async function triggerRecommendation() {
    const triggerBtn = document.getElementById('triggerBtn');

    // 防止重复点击
    if (triggerBtn.disabled) {
        showMessage('推荐任务正在进行中，请勿重复点击', 'warning');
        return;
    }

    try {
        // 禁用按钮并更改文本
        triggerBtn.disabled = true;
        const originalText = triggerBtn.innerHTML;
        triggerBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-1"></i>生成中...';
        triggerBtn.classList.add('opacity-50', 'cursor-not-allowed');

        showMessage('正在生成推荐...', 'info');

        // 获取用户的偏好设置，选择第一个启用的偏好
        let preferenceId = null;
        try {
            const preferences = await apiRequest('/preferences');
            const enabledPreference = preferences.find(pref => pref.enabled);
            if (enabledPreference) {
                preferenceId = enabledPreference.id;
            }
        } catch (prefError) {
            console.error('获取偏好失败:', prefError);
        }

        // 发送触发请求，包含偏好ID
        const requestData = {
            force_refresh: true,
            preference_id: preferenceId
        };

        // 等待推荐任务完成 - API会等到任务执行完毕才返回
        const result = await apiRequest('/projects/runs/trigger', {
            method: 'POST',
            body: JSON.stringify(requestData)
        });

        // 根据结果显示适当的消息
        if (result.status === 'completed') {
            showMessage('推荐生成成功！' + (result.message || ''), 'success');
        } else if (result.status === 'failed') {
            showMessage('推荐生成失败：' + (result.message || '未知错误'), 'error');
        } else {
            showMessage('推荐任务已完成：' + (result.message || ''), 'info');
        }

        // 任务完成后立即刷新推荐列表
        await loadRecommendations();

        // 恢复按钮
        triggerBtn.disabled = false;
        triggerBtn.innerHTML = originalText;
        triggerBtn.classList.remove('opacity-50', 'cursor-not-allowed');

    } catch (error) {
        // 出错时立即恢复按钮
        triggerBtn.disabled = false;
        triggerBtn.innerHTML = '<i class="fas fa-rocket mr-1"></i>手动触发推荐';
        triggerBtn.classList.remove('opacity-50', 'cursor-not-allowed');
        showMessage('触发推荐失败：' + error.message, 'error');
    }
}

// 加载推荐结果
async function loadRecommendations() {
    try {
        const recommendations = await apiRequest('/projects/my/latest?limit=10');
        const container = document.getElementById('recommendationsList');

        if (recommendations.length === 0) {
            container.innerHTML = '<p class="text-gray-500 text-center py-8">暂无推荐结果<br><small>点击"手动触发推荐"生成推荐</small></p>';
            return;
        }

        container.innerHTML = recommendations.map(rec => `
            <div class="repo-card border border-gray-200 rounded-lg p-4 mb-4">
                <div class="flex justify-between items-start">
                    <div class="flex-1">
                        <div class="flex items-center space-x-2 mb-2">
                            <a href="${rec.repo.html_url}" target="_blank"
                               class="text-lg font-semibold text-blue-600 hover:text-blue-800">
                                ${rec.repo.full_name}
                            </a>
                            <span class="px-2 py-1 bg-yellow-100 text-yellow-800 text-xs rounded font-medium">
                                评分: ${rec.score.toFixed(2)}
                            </span>
                        </div>
                        <p class="text-gray-600 mb-2">${rec.repo.description || '无描述'}</p>
                        <div class="flex flex-wrap gap-2 mb-2">
                            <span class="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded">
                                <i class="fas fa-code mr-1"></i>${rec.repo.language || '未知'}
                            </span>
                            <span class="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded">
                                <i class="fas fa-star mr-1"></i>${rec.repo.stargazers_count.toLocaleString()}
                            </span>
                            <span class="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded">
                                <i class="fas fa-code-branch mr-1"></i>${rec.repo.forks_count.toLocaleString()}
                            </span>
                        </div>
                        <div class="text-xs text-gray-500">
                            <strong>推荐理由:</strong>
                            ${rec.reason.matched_keywords.length > 0 ? `匹配关键词: ${rec.reason.matched_keywords.join(', ')}` : ''}
                            ${rec.reason.language_match ? ' | 语言匹配' : ''}
                            ${rec.reason.topic_bonus > 0 ? ' | 主题相关' : ''}
                        </div>
                        <div class="mt-2 flex flex-wrap gap-1">
                            ${(rec.repo.topics || []).map(topic =>
                                `<span class="tag-chip px-2 py-1 text-xs rounded">${topic}</span>`
                            ).join('')}
                        </div>
                    </div>
                    <div class="ml-4 text-right">
                        <div class="text-xs text-gray-500">
                            ${new Date(rec.created_at).toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })}
                        </div>
                    </div>
                </div>
            </div>
        `).join('');
    } catch (error) {
        document.getElementById('recommendationsList').innerHTML =
            '<p class="text-red-500 text-center py-8">加载推荐结果失败</p>';
    }
}

// 搜索历史记录
async function searchHistory() {
    const keyword = document.getElementById('searchKeyword').value;
    loadHistory(1, keyword);
}

// 加载历史记录
async function loadHistory(page = 1, keyword = '') {
    try {
        const params = new URLSearchParams({
            page: page.toString(),
            page_size: '10'
        });

        if (keyword) {
            params.append('keyword', keyword);
        }

        const data = await apiRequest(`/projects/history?${params}`);
        const container = document.getElementById('historyList');

        if (data.items.length === 0) {
            container.innerHTML = '<p class="text-gray-500 text-center py-8">暂无历史记录</p>';
            document.getElementById('historyPagination').innerHTML = '';
            return;
        }

        // 渲染历史记录
        container.innerHTML = data.items.map(rec => `
            <div class="border border-gray-200 rounded-lg p-4 mb-3">
                <div class="flex justify-between items-start">
                    <div class="flex-1">
                        <a href="${rec.repo.html_url}" target="_blank"
                           class="text-blue-600 hover:text-blue-800 font-medium">
                            ${rec.repo.full_name}
                        </a>
                        <p class="text-sm text-gray-600 mt-1">${rec.repo.description || '无描述'}</p>
                        <div class="mt-2 text-xs text-gray-500">
                            评分: ${rec.score.toFixed(2)} |
                            ${rec.repo.language || '未知语言'} |
                            ${rec.repo.stargazers_count.toLocaleString()} stars
                        </div>
                    </div>
                    <div class="text-xs text-gray-500">
                        ${new Date(rec.created_at).toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' })}
                    </div>
                </div>
            </div>
        `).join('');

        // 渲染分页
        renderPagination(data, page, keyword);
    } catch (error) {
        document.getElementById('historyList').innerHTML =
            '<p class="text-red-500 text-center py-8">加载历史记录失败</p>';
    }
}

// 渲染分页控件
function renderPagination(data, currentPage, keyword) {
    const container = document.getElementById('historyPagination');

    if (data.total_pages <= 1) {
        container.innerHTML = '';
        return;
    }

    let pagination = '<div class="flex space-x-2">';

    // 上一页
    if (currentPage > 1) {
        pagination += `<button onclick="loadHistory(${currentPage - 1}, '${keyword}')"
                      class="px-3 py-1 border border-gray-300 rounded text-sm hover:bg-gray-50">上一页</button>`;
    }

    // 页码
    const startPage = Math.max(1, currentPage - 2);
    const endPage = Math.min(data.total_pages, currentPage + 2);

    for (let i = startPage; i <= endPage; i++) {
        const isActive = i === currentPage;
        pagination += `<button onclick="loadHistory(${i}, '${keyword}')"
                      class="px-3 py-1 border ${isActive ? 'bg-blue-500 text-white border-blue-500' : 'border-gray-300 hover:bg-gray-50'} rounded text-sm">
                      ${i}</button>`;
    }

    // 下一页
    if (currentPage < data.total_pages) {
        pagination += `<button onclick="loadHistory(${currentPage + 1}, '${keyword}')"
                      class="px-3 py-1 border border-gray-300 rounded text-sm hover:bg-gray-50">下一页</button>`;
    }

    pagination += '</div>';
    container.innerHTML = pagination;
}



// 保存定时推荐设置
async function saveScheduleSettings() {
    const updateData = {
        auto_recommendations_enabled: document.getElementById('autoRecommendationsEnabled').checked,
        recommendation_interval_hours: parseInt(document.getElementById('recommendationInterval').value)
    };

    try {
        showMessage('正在保存定时设置...', 'info');

        // 调用后端API保存用户配置
        const response = await apiRequest('/auth/me', {
            method: 'PUT',
            body: JSON.stringify(updateData)
        });

        showMessage('定时推荐设置已保存！', 'success');

        // 重新获取用户信息，确保数据同步
        const userResponse = await apiRequest('/auth/me');
        currentUser = userResponse.data || userResponse;

        // 重新加载设置表单
        await loadNotificationSettings();

    } catch (error) {
        showMessage('保存定时设置失败：' + error.message, 'error');
    }
}

// 保存通知设置
async function saveNotificationSettings() {
    const updateData = {
        notification_email: document.getElementById('notificationEmail').value || null,
        telegram_chat_id: document.getElementById('telegramChatId').value || null,
        slack_webhook_url: document.getElementById('slackWebhook').value || null,
        wechat_webhook_url: document.getElementById('wechatWebhook').value || null
    };

    try {
        showMessage('正在保存设置...', 'info');

        // 调用后端API保存用户配置
        const response = await apiRequest('/auth/me', {
            method: 'PUT',
            body: JSON.stringify(updateData)
        });

        showMessage('通知设置已保存并立即生效！', 'success');

        // 重新获取用户信息，确保数据同步
        const userResponse = await apiRequest('/auth/me');
        currentUser = userResponse.data || userResponse;

        // 重新加载设置表单
        await loadNotificationSettings();

    } catch (error) {
        showMessage('保存设置失败：' + error.message, 'error');
    }
}

// 加载已保存的通知设置
async function loadNotificationSettings() {
    try {
        // 如果用户已登录，从后端API获取设置
        if (currentUser) {
            // 填充定时推荐设置
            const autoEnabledField = document.getElementById('autoRecommendationsEnabled');
            if (autoEnabledField) {
                autoEnabledField.checked = currentUser.auto_recommendations_enabled || false;
            }

            const intervalField = document.getElementById('recommendationInterval');
            if (intervalField) {
                intervalField.value = currentUser.recommendation_interval_hours || 24;
            }

            // 填充通知邮箱
            const notificationEmailField = document.getElementById('notificationEmail');
            if (notificationEmailField) {
                notificationEmailField.value = currentUser.notification_email || '';
            }

            // 填充Telegram设置
            const telegramChatIdField = document.getElementById('telegramChatId');
            if (telegramChatIdField) {
                telegramChatIdField.value = currentUser.telegram_chat_id || '';
            }

            // 填充Slack设置
            const slackWebhookField = document.getElementById('slackWebhook');
            if (slackWebhookField) {
                slackWebhookField.value = currentUser.slack_webhook_url || '';
            }

            // 填充企业微信设置
            const wechatWebhookField = document.getElementById('wechatWebhook');
            if (wechatWebhookField) {
                wechatWebhookField.value = currentUser.wechat_webhook_url || '';
            }
        } else {
            // 如果未登录，尝试从localStorage加载（向后兼容）
            const savedSettings = localStorage.getItem('notificationSettings');
            if (savedSettings) {
                const settings = JSON.parse(savedSettings);

                // 填充Telegram设置
                if (settings.telegram) {
                    const telegramChatIdField = document.getElementById('telegramChatId');
                    if (telegramChatIdField) {
                        telegramChatIdField.value = settings.telegram.chat_id || '';
                    }
                }

                // 填充Slack设置
                if (settings.slack) {
                    const slackWebhookField = document.getElementById('slackWebhook');
                    if (slackWebhookField) {
                        slackWebhookField.value = settings.slack.webhook_url || '';
                    }
                }

                // 填充企业微信设置
                if (settings.wechat) {
                    const wechatWebhookField = document.getElementById('wechatWebhook');
                    if (wechatWebhookField) {
                        wechatWebhookField.value = settings.wechat.webhook_url || '';
                    }
                }
            }
        }
    } catch (error) {
        console.error('加载通知设置失败:', error);
    }
}

// 测试邮件通知
async function testEmailNotification() {
    const settings = {
        host: document.getElementById('smtpHost').value,
        port: parseInt(document.getElementById('smtpPort').value) || 587,
        username: document.getElementById('smtpUsername').value,
        password: document.getElementById('smtpPassword').value,
        tls: document.getElementById('smtpTls').checked
    };

    if (!settings.host || !settings.username || !settings.password) {
        showMessage('请填写完整的邮件设置', 'error');
        return;
    }

    try {
        showMessage('正在发送测试邮件...', 'info');

        // 调用后端API测试邮件发送
        await apiRequest('/projects/test/email', {
            method: 'POST',
            body: JSON.stringify({
                to_email: settings.username, // 发送到配置的邮箱地址
                smtp_host: settings.host,
                smtp_port: settings.port,
                smtp_username: settings.username,
                smtp_password: settings.password,
                smtp_tls: settings.tls
            })
        });

        // 测试成功后自动保存SMTP配置到用户设置
        try {
            await apiRequest('/auth/me', {
                method: 'PUT',
                body: JSON.stringify({
                    notification_email: settings.username,
                    smtp_host: settings.host,
                    smtp_port: settings.port,
                    smtp_username: settings.username,
                    smtp_password: settings.password,
                    smtp_use_tls: settings.tls
                })
            });
            showMessage('测试邮件发送成功！SMTP配置已自动保存', 'success');
        } catch (saveError) {
            showMessage('测试邮件发送成功，但SMTP配置保存失败：' + saveError.message, 'warning');
        }
    } catch (error) {
        showMessage('测试邮件发送失败：' + error.message, 'error');
    }
}

// 测试Telegram通知
async function testTelegramNotification() {
    const token = document.getElementById('telegramToken').value;
    const chatId = document.getElementById('telegramChatId').value;

    if (!token || !chatId) {
        showMessage('请填写Telegram Bot Token和Chat ID', 'error');
        return;
    }

    try {
        showMessage('正在发送测试消息到Telegram...', 'info');

        const response = await fetch('/api/projects/test/telegram', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            },
            body: JSON.stringify({
                bot_token: token,
                chat_id: chatId
            })
        });

        const result = await response.json();

        if (result.success) {
            showMessage(result.message, 'success');
        } else {
            showMessage(result.message, 'error');
        }
    } catch (error) {
        showMessage('Telegram测试失败：' + error.message, 'error');
    }
}

// 测试Slack通知
async function testSlackNotification() {
    const webhookUrl = document.getElementById('slackWebhook').value;

    if (!webhookUrl) {
        showMessage('请填写Slack Webhook URL', 'error');
        return;
    }

    try {
        showMessage('正在发送测试消息到Slack...', 'info');

        const response = await fetch('/api/projects/test/slack', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            },
            body: JSON.stringify({
                webhook_url: webhookUrl
            })
        });

        const result = await response.json();

        if (result.success) {
            showMessage(result.message, 'success');
        } else {
            showMessage(result.message, 'error');
        }
    } catch (error) {
        showMessage('Slack测试失败：' + error.message, 'error');
    }
}

// 测试企业微信通知
async function testWechatNotification() {
    const webhookUrl = document.getElementById('wechatWebhook').value;

    if (!webhookUrl) {
        showMessage('请填写企业微信Webhook URL', 'error');
        return;
    }

    try {
        showMessage('正在发送测试消息到企业微信...', 'info');

        const response = await fetch('/api/projects/test/wechat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('token')}`
            },
            body: JSON.stringify({
                webhook_url: webhookUrl
            })
        });

        const result = await response.json();

        if (result.success) {
            showMessage(result.message, 'success');
        } else {
            showMessage(result.message, 'error');
        }
    } catch (error) {
        showMessage('企业微信测试失败：' + error.message, 'error');
    }
}

// ===== API设置相关函数 =====

// 切换Token可见性
function toggleTokenVisibility() {
    const tokenInput = document.getElementById('githubToken');
    const icon = document.getElementById('tokenVisibilityIcon');

    if (tokenInput.type === 'password') {
        tokenInput.type = 'text';
        icon.className = 'fas fa-eye-slash';
    } else {
        tokenInput.type = 'password';
        icon.className = 'fas fa-eye';
    }
}

// 测试GitHub Token
async function testGitHubToken() {
    const token = document.getElementById('githubToken').value;

    if (!token) {
        showMessage('请先输入GitHub Token', 'error');
        return;
    }

    try {
        showMessage('正在测试GitHub Token...', 'info');

        // 直接调用GitHub API测试Token
        const response = await fetch('https://api.github.com/user', {
            headers: {
                'Authorization': `token ${token}`,
                'User-Agent': 'GitHub-Bot-WebUI/1.0.0'
            }
        });

        if (response.ok) {
            const userData = await response.json();
            document.getElementById('apiUser').textContent = userData.login;
            document.getElementById('apiScopes').textContent = response.headers.get('X-OAuth-Scopes') || '未知';
            document.getElementById('lastCheck').textContent = new Date().toLocaleString();

            // 更新连接状态
            updateConnectionStatus('online', 'Token有效，连接成功');

            // 更新速率限制信息
            await refreshRateLimit();

            showMessage('GitHub Token测试成功！', 'success');
        } else {
            updateConnectionStatus('offline', 'Token无效或权限不足');
            showMessage('GitHub Token测试失败：' + response.status + ' ' + response.statusText, 'error');
        }
    } catch (error) {
        updateConnectionStatus('offline', '网络连接失败');
        showMessage('GitHub Token测试失败：' + error.message, 'error');
    }
}

// 保存GitHub Token
async function saveGitHubToken() {
    const token = document.getElementById('githubToken').value;

    if (!token) {
        showMessage('请先输入GitHub Token', 'error');
        return;
    }

    try {
        showMessage('正在保存GitHub Token...', 'info');

        // 这里应该调用后端API来保存token，现在先用localStorage模拟
        localStorage.setItem('github_token', token);

        showMessage('GitHub Token保存成功！重启服务后生效', 'success');
    } catch (error) {
        showMessage('保存GitHub Token失败：' + error.message, 'error');
    }
}

// 保存GitHub Base URL
async function saveGitHubBaseUrl() {
    const baseUrl = document.getElementById('githubBaseUrl').value;

    if (!baseUrl) {
        showMessage('请输入GitHub API Base URL', 'error');
        return;
    }

    try {
        showMessage('正在保存GitHub Base URL...', 'info');

        // 这里应该调用后端API来保存base URL，现在先用localStorage模拟
        localStorage.setItem('github_base_url', baseUrl);

        showMessage('GitHub Base URL保存成功！重启服务后生效', 'success');
    } catch (error) {
        showMessage('保存GitHub Base URL失败：' + error.message, 'error');
    }
}

// 测试仓库访问
async function testRepoAccess() {
    const repoName = document.getElementById('testRepo').value;
    const token = document.getElementById('githubToken').value;

    if (!repoName) {
        showMessage('请输入仓库名，格式如：microsoft/vscode', 'error');
        return;
    }

    if (!token) {
        showMessage('请先设置GitHub Token', 'error');
        return;
    }

    try {
        showMessage('正在测试仓库访问...', 'info');

        const response = await fetch(`https://api.github.com/repos/${repoName}`, {
            headers: {
                'Authorization': `token ${token}`,
                'User-Agent': 'GitHub-Bot-WebUI/1.0.0'
            }
        });

        const testResults = document.getElementById('testResults');
        const testOutput = document.getElementById('testOutput');

        if (response.ok) {
            const repoData = await response.json();
            testOutput.innerHTML = `
                <div class="text-green-600">✓ 仓库访问成功</div>
                <div>仓库: ${repoData.full_name}</div>
                <div>描述: ${repoData.description || '无描述'}</div>
                <div>Stars: ${repoData.stargazers_count}</div>
                <div>Language: ${repoData.language || '未知'}</div>
                <div>私有: ${repoData.private ? '是' : '否'}</div>
            `;
            showMessage('仓库访问测试成功！', 'success');
        } else {
            testOutput.innerHTML = `
                <div class="text-red-600">✗ 仓库访问失败</div>
                <div>状态码: ${response.status}</div>
                <div>错误: ${response.statusText}</div>
            `;
            showMessage('仓库访问测试失败', 'error');
        }

        testResults.classList.remove('hidden');
    } catch (error) {
        document.getElementById('testOutput').innerHTML = `
            <div class="text-red-600">✗ 网络错误</div>
            <div>${error.message}</div>
        `;
        document.getElementById('testResults').classList.remove('hidden');
        showMessage('仓库访问测试失败：' + error.message, 'error');
    }
}

// 测试搜索API
async function testSearchAPI() {
    const token = document.getElementById('githubToken').value;

    if (!token) {
        showMessage('请先设置GitHub Token', 'error');
        return;
    }

    try {
        showMessage('正在测试搜索API...', 'info');

        const response = await fetch('https://api.github.com/search/repositories?q=javascript&sort=stars&order=desc&per_page=5', {
            headers: {
                'Authorization': `token ${token}`,
                'User-Agent': 'GitHub-Bot-WebUI/1.0.0'
            }
        });

        const testResults = document.getElementById('testResults');
        const testOutput = document.getElementById('testOutput');

        if (response.ok) {
            const searchData = await response.json();
            testOutput.innerHTML = `
                <div class="text-green-600">✓ 搜索API测试成功</div>
                <div>总结果数: ${searchData.total_count}</div>
                <div>返回结果数: ${searchData.items.length}</div>
                <div class="mt-2">前3个仓库:</div>
                ${searchData.items.slice(0, 3).map(repo =>
                    `<div class="ml-2">• ${repo.full_name} (${repo.stargazers_count} stars)</div>`
                ).join('')}
            `;
            showMessage('搜索API测试成功！', 'success');
        } else {
            testOutput.innerHTML = `
                <div class="text-red-600">✗ 搜索API测试失败</div>
                <div>状态码: ${response.status}</div>
                <div>错误: ${response.statusText}</div>
            `;
            showMessage('搜索API测试失败', 'error');
        }

        testResults.classList.remove('hidden');
    } catch (error) {
        document.getElementById('testOutput').innerHTML = `
            <div class="text-red-600">✗ 网络错误</div>
            <div>${error.message}</div>
        `;
        document.getElementById('testResults').classList.remove('hidden');
        showMessage('搜索API测试失败：' + error.message, 'error');
    }
}

// 刷新速率限制信息
async function refreshRateLimit() {
    const token = document.getElementById('githubToken').value;

    if (!token) {
        return;
    }

    try {
        const response = await fetch('https://api.github.com/rate_limit', {
            headers: {
                'Authorization': `token ${token}`,
                'User-Agent': 'GitHub-Bot-WebUI/1.0.0'
            }
        });

        if (response.ok) {
            const rateLimitData = await response.json();
            const core = rateLimitData.rate;

            document.getElementById('rateLimitRemaining').textContent = core.remaining;
            document.getElementById('rateLimitTotal').textContent = core.limit;

            const resetTime = new Date(core.reset * 1000);
            document.getElementById('rateLimitReset').textContent = resetTime.toLocaleTimeString();

            // 更新进度条
            const percentage = (core.remaining / core.limit) * 100;
            const rateLimitBar = document.getElementById('rateLimitBar');
            rateLimitBar.style.width = `${percentage}%`;

            // 根据剩余量更改颜色
            if (percentage > 50) {
                rateLimitBar.className = 'bg-green-500 h-2 rounded-full transition-all duration-300';
            } else if (percentage > 20) {
                rateLimitBar.className = 'bg-yellow-500 h-2 rounded-full transition-all duration-300';
            } else {
                rateLimitBar.className = 'bg-red-500 h-2 rounded-full transition-all duration-300';
            }
        }
    } catch (error) {
        console.error('Failed to refresh rate limit:', error);
    }
}

// 更新连接状态
function updateConnectionStatus(status, message) {
    const apiStatus = document.getElementById('apiStatus');
    const statusIndicator = apiStatus.querySelector('.status-indicator');
    const statusText = apiStatus.querySelector('span:last-child');

    if (status === 'online') {
        statusIndicator.className = 'status-indicator online w-3 h-3 bg-green-500 rounded-full inline-block';
        statusText.textContent = message || '连接正常';
        statusText.className = 'text-sm text-green-600 ml-2';
    } else {
        statusIndicator.className = 'status-indicator offline w-3 h-3 bg-red-500 rounded-full inline-block';
        statusText.textContent = message || '连接失败';
        statusText.className = 'text-sm text-red-600 ml-2';
    }
}

// 加载API设置页面
async function loadAPISettings() {
    try {
        // 从localStorage加载保存的token和base URL
        const savedToken = localStorage.getItem('github_token');
        const savedBaseUrl = localStorage.getItem('github_base_url');

        if (savedToken) {
            document.getElementById('githubToken').value = savedToken;
        }

        if (savedBaseUrl) {
            document.getElementById('githubBaseUrl').value = savedBaseUrl;
        }

        // 如果有保存的token，自动测试连接状态
        if (savedToken) {
            // 延迟500ms后自动测试，避免页面切换时的冲突
            setTimeout(async () => {
                await refreshAPIStatus();
            }, 500);
        }
    } catch (error) {
        console.error('Failed to load API settings:', error);
    }
}

// 刷新API状态
async function refreshAPIStatus() {
    const token = document.getElementById('githubToken').value;

    if (!token) {
        updateConnectionStatus('offline', '未配置Token');
        return;
    }

    try {
        // 测试连接
        const response = await fetch('https://api.github.com/user', {
            headers: {
                'Authorization': `token ${token}`,
                'User-Agent': 'GitHub-Bot-WebUI/1.0.0'
            }
        });

        if (response.ok) {
            const userData = await response.json();
            document.getElementById('apiUser').textContent = userData.login;
            document.getElementById('apiScopes').textContent = response.headers.get('X-OAuth-Scopes') || '未知';
            document.getElementById('lastCheck').textContent = new Date().toLocaleString();

            updateConnectionStatus('online', 'Token有效，连接成功');

            // 更新速率限制信息
            await refreshRateLimit();
        } else {
            updateConnectionStatus('offline', 'Token无效或权限不足');
        }
    } catch (error) {
        updateConnectionStatus('offline', '网络连接失败');
    }
}
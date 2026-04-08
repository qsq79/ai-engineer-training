// 企业级安全智能助手 - 前端JavaScript

// API基础URL
const API_BASE_URL = '/api/v1';

// 页面切换
document.addEventListener('DOMContentLoaded', function() {
    // 侧边栏导航切换
    const navItems = document.querySelectorAll('.nav-item');
    const pages = document.querySelectorAll('.page');
    const pageTitle = document.getElementById('pageTitle');
    
    const pageTitles = {
        'dashboard': '仪表盘',
        'query': '智能查询',
        'agents': 'Agent管理',
        'workflows': '工作流管理',
        'sessions': '会话管理',
        'compliance': '合规检查',
        'stats': '统计分析',
        'admin': '系统管理'
    };
    
    navItems.forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();
            
            const page = this.getAttribute('data-page');
            
            // 更新导航状态
            navItems.forEach(nav => nav.classList.remove('active'));
            this.classList.add('active');
            
            // 切换页面显示
            pages.forEach(p => p.classList.remove('active'));
            document.getElementById(page + 'Page').classList.add('active');
            
            // 更新页面标题
            pageTitle.textContent = pageTitles[page];
            
            // 初始化页面数据
            initPageData(page);
        });
    });
    
    // 侧边栏折叠
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebar = document.getElementById('sidebar');
    
    sidebarToggle.addEventListener('click', function() {
        sidebar.classList.toggle('collapsed');
    });
    
    // 管理标签页切换
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const tab = this.getAttribute('data-tab');
            
            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));
            
            this.classList.add('active');
            document.getElementById(tab + 'Tab').classList.add('active');
        });
    });
    
    // 示例问题点击
    const exampleCards = document.querySelectorAll('.example-card');
    const queryInput = document.getElementById('queryInput');
    
    exampleCards.forEach(card => {
        card.addEventListener('click', function() {
            const query = this.getAttribute('data-query');
            queryInput.value = query;
        });
    });
    
    // 清空查询
    const clearQueryBtn = document.getElementById('clearQuery');
    if (clearQueryBtn) {
        clearQueryBtn.addEventListener('click', function() {
            queryInput.value = '';
            document.getElementById('queryResult').style.display = 'none';
        });
    }
    
    // 关闭结果
    const closeResultBtn = document.getElementById('closeResult');
    if (closeResultBtn) {
        closeResultBtn.addEventListener('click', function() {
            document.getElementById('queryResult').style.display = 'none';
        });
    }
    
    // 提交查询
    const submitQueryBtn = document.getElementById('submitQuery');
    if (submitQueryBtn) {
        submitQueryBtn.addEventListener('click', submitQuery);
    }
    
    // 初始化仪表盘图表
    initDashboardCharts();
});

// 初始化页面数据
function initPageData(page) {
    switch(page) {
        case 'dashboard':
            loadDashboardData();
            break;
        case 'query':
            // 查询页面不需要额外初始化
            break;
        case 'agents':
            loadAgentsData();
            break;
        case 'workflows':
            loadWorkflowsData();
            break;
        case 'sessions':
            loadSessionsData();
            break;
        case 'compliance':
            loadComplianceData();
            break;
        case 'stats':
            loadStatsData();
            initStatsCharts();
            break;
        case 'admin':
            loadAdminData();
            break;
    }
}

// 加载仪表盘数据
async function loadDashboardData() {
    try {
        const response = await fetch(API_BASE_URL + '/stats/overview');
        const data = await response.json();
        
        // 更新统计卡片数据
        if (data.summary) {
            document.querySelectorAll('.stat-card .stat-value')[0].textContent = data.summary.total_queries?.toLocaleString() || '0';
            document.querySelectorAll('.stat-card .stat-value')[1].textContent = data.summary.total_workflows?.toLocaleString() || '0';
            document.querySelectorAll('.stat-card .stat-value')[2].textContent = data.summary.total_sessions?.toLocaleString() || '0';
            document.querySelectorAll('.stat-card .stat-value')[3].textContent = '$' + (data.summary.total_cost?.toFixed(2) || '0.00');
        }
    } catch (error) {
        console.error('加载仪表盘数据失败:', error);
    }
}

// 加载Agent数据
async function loadAgentsData() {
    try {
        const response = await fetch(API_BASE_URL + '/agents/list');
        const data = await response.json();
        
        // 更新Agent卡片数据（如果需要动态加载）
        console.log('Agent数据:', data);
    } catch (error) {
        console.error('加载Agent数据失败:', error);
    }
}

// 加载工作流数据
async function loadWorkflowsData() {
    try {
        const response = await fetch(API_BASE_URL + '/workflows/list');
        const data = await response.json();
        
        // 更新工作流表格数据（如果需要动态加载）
        console.log('工作流数据:', data);
    } catch (error) {
        console.error('加载工作流数据失败:', error);
    }
}

// 加载会话数据
async function loadSessionsData() {
    try {
        const response = await fetch(API_BASE_URL + '/sessions/list');
        const data = await response.json();
        
        // 更新会话表格数据（如果需要动态加载）
        console.log('会话数据:', data);
    } catch (error) {
        console.error('加载会话数据失败:', error);
    }
}

// 加载合规数据
async function loadComplianceData() {
    try {
        const response = await fetch(API_BASE_URL + '/compliance/reports');
        const data = await response.json();
        
        // 更新合规卡片数据（如果需要动态加载）
        console.log('合规数据:', data);
    } catch (error) {
        console.error('加载合规数据失败:', error);
    }
}

// 加载统计数据
async function loadStatsData() {
    try {
        const overviewResponse = await fetch(API_BASE_URL + '/stats/overview');
        const overviewData = await overviewResponse.json();
        
        const agentsResponse = await fetch(API_BASE_URL + '/stats/agents');
        const agentsData = await agentsResponse.json();
        
        console.log('统计数据:', overviewData, agentsData);
    } catch (error) {
        console.error('加载统计数据失败:', error);
    }
}

// 加载管理员数据
async function loadAdminData() {
    try {
        const tenantsResponse = await fetch(API_BASE_URL + '/admin/tenants');
        const tenantsData = await tenantsResponse.json();
        
        const usersResponse = await fetch(API_BASE_URL + '/admin/users');
        const usersData = await usersResponse.json();
        
        console.log('租户数据:', tenantsData);
        console.log('用户数据:', usersData);
    } catch (error) {
        console.error('加载管理员数据失败:', error);
    }
}

// 提交查询
async function submitQuery() {
    const queryInput = document.getElementById('queryInput');
    const query = queryInput.value.trim();
    
    if (!query) {
        alert('请输入查询内容');
        return;
    }
    
    const submitBtn = document.getElementById('submitQuery');
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 处理中...';
    
    try {
        const response = await fetch(API_BASE_URL + '/query', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query: query,
                tenant_id: 'tenant-001',
                user_id: 'user-001'
            })
        });
        
        const data = await response.json();
        
        // 显示结果
        const resultDiv = document.getElementById('queryResult');
        const contentDiv = document.getElementById('resultContent');
        
        contentDiv.innerHTML = `
            <div class="result-intent">
                <span class="label">识别意图：</span>
                <span class="badge badge-info">${data.intent}</span>
            </div>
            <div class="result-confidence">
                <span class="label">置信度：</span>
                <span>${(data.confidence * 100).toFixed(1)}%</span>
            </div>
            <div class="result-data">
                <pre>${JSON.stringify(data.result, null, 2)}</pre>
            </div>
            ${data.suggested_followup && data.suggested_followup.length > 0 ? `
            <div class="result-suggestions">
                <span class="label">建议后续：</span>
                <ul>
                    ${data.suggested_followup.map(s => `<li>${s}</li>`).join('')}
                </ul>
            </div>
            ` : ''}
        `;
        
        resultDiv.style.display = 'block';
    } catch (error) {
        console.error('查询失败:', error);
        alert('查询失败，请稍后重试');
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = '<i class="fas fa-paper-plane"></i> 提交查询';
    }
}

// 初始化仪表盘图表
function initDashboardCharts() {
    // 查询趋势图
    const queryChartCtx = document.getElementById('queryChart');
    if (queryChartCtx) {
        new Chart(queryChartCtx, {
            type: 'line',
            data: {
                labels: ['3月8日', '3月9日', '3月10日', '3月11日', '3月12日', '3月13日', '3月14日'],
                datasets: [{
                    label: '查询数',
                    data: [1234, 1456, 1678, 1890, 2101, 2345, 2567],
                    borderColor: '#2563eb',
                    backgroundColor: 'rgba(37, 99, 235, 0.1)',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }
    
    // Agent使用分布图
    const agentChartCtx = document.getElementById('agentChart');
    if (agentChartCtx) {
        new Chart(agentChartCtx, {
            type: 'doughnut',
            data: {
                labels: ['意图识别', '日志查询', '评分解读', '威胁分析', '工作流'],
                datasets: [{
                    data: [5678, 3456, 2345, 2345, 1234],
                    backgroundColor: [
                        '#2563eb',
                        '#10b981',
                        '#f59e0b',
                        '#ec4899',
                        '#06b6d4'
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    }
}

// 初始化统计页面图表
function initStatsCharts() {
    // 统计查询趋势图
    const statsQueryChartCtx = document.getElementById('statsQueryChart');
    if (statsQueryChartCtx) {
        new Chart(statsQueryChartCtx, {
            type: 'bar',
            data: {
                labels: ['3月8日', '3月9日', '3月10日', '3月11日', '3月12日', '3月13日', '3月14日'],
                datasets: [{
                    label: '查询数',
                    data: [1234, 1456, 1678, 1890, 2101, 2345, 2567],
                    backgroundColor: '#2563eb'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }
    
    // 成本趋势图
    const statsCostChartCtx = document.getElementById('statsCostChart');
    if (statsCostChartCtx) {
        new Chart(statsCostChartCtx, {
            type: 'line',
            data: {
                labels: ['3月8日', '3月9日', '3月10日', '3月11日', '3月12日', '3月13日', '3月14日'],
                datasets: [{
                    label: '成本',
                    data: [32.45, 34.56, 36.78, 38.90, 41.23, 43.45, 45.67],
                    borderColor: '#10b981',
                    backgroundColor: 'rgba(16, 185, 129, 0.1)',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }
}

// 辅助函数：格式化日期
function formatDate(timestamp) {
    const date = new Date(timestamp * 1000);
    return date.toLocaleString('zh-CN');
}

// 辅助函数：格式化数字
function formatNumber(num) {
    return num.toLocaleString('zh-CN');
}

// 辅助函数：显示加载状态
function showLoading(element) {
    element.innerHTML = '<div class="loading"><i class="fas fa-spinner fa-spin"></i> 加载中...</div>';
}

// 辅助函数：显示错误状态
function showError(element, message) {
    element.innerHTML = `<div class="error"><i class="fas fa-exclamation-circle"></i> ${message}</div>`;
}

// 导出函数供外部调用
window.EnterpriseSecurityApp = {
    submitQuery,
    loadDashboardData,
    loadAgentsData,
    loadWorkflowsData,
    loadSessionsData,
    loadComplianceData,
    loadStatsData,
    loadAdminData
};
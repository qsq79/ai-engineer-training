// 日志查询 API 服务
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8002/api/v1';

// 创建 axios 实例
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器 - 添加 Token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器 - 处理错误
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// 查询 API
export const queryAPI = {
  /**
   * 统一查询接口
   * @param {string} query - 用户查询文本
   * @param {string} tenantId - 租户ID
   * @param {string} userId - 用户ID
   * @param {string} sessionId - 会话ID（可选）
   * @param {object} context - 上下文信息（可选）
   */
  unifiedQuery: async (query, tenantId, userId, sessionId = null, context = {}) => {
    const response = await api.post('/query', {
      query,
      tenant_id: tenantId,
      user_id: userId,
      session_id: sessionId,
      context,
    });
    return response.data;
  },
};

export default api;
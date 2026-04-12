import { Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import Login from './pages/Login';
import Register from './pages/Register';
import LogQuery from './pages/LogQuery';
import './App.css';

function App() {
  const navigate = useNavigate();
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // 检查本地存储的认证状态
    const token = localStorage.getItem('access_token');
    if (token) {
      setIsAuthenticated(true);
    }
    setLoading(false);
  }, []);

  const handleLoginSuccess = () => {
    setIsAuthenticated(true);
  };

  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user_info');
    setIsAuthenticated(false);
  };

  if (loading) {
    return (
      <div className="loading-container">
        <div className="loading-spinner"></div>
        <p>加载中...</p>
      </div>
    );
  }

  return (
    <Routes>
      <Route 
        path="/login" 
        element={
          isAuthenticated ? <Navigate to="/dashboard" replace /> : 
          <Login onLoginSuccess={handleLoginSuccess} />
        } 
      />
      <Route 
        path="/register" 
        element={
          isAuthenticated ? <Navigate to="/dashboard" replace /> : 
          <Register />
        } 
      />
      <Route
        path="/dashboard"
        element={
          isAuthenticated ? (
            <div className="dashboard">
              <header className="app-header">
                <h1>企业安全智能助手</h1>
                <button onClick={handleLogout} className="logout-btn">退出登录</button>
              </header>
              <main className="dashboard-content">
                <h2>欢迎使用企业安全智能助手</h2>
                <div className="feature-grid">
                  <div className="feature-card" onClick={() => navigate('/query')}>
                    <h3>日志查询</h3>
                    <p>快速检索系统日志，分析差异数据</p>
                  </div>
                  <div className="feature-card">
                    <h3>意图识别</h3>
                    <p>智能分析用户查询意图</p>
                  </div>
                  <div className="feature-card">
                    <h3>工作流协调</h3>
                    <p>自动化处理复杂任务</p>
                  </div>
                  <div className="feature-card">
                    <h3>威胁分析</h3>
                    <p>实时检测安全威胁</p>
                  </div>
                  <div className="feature-card">
                    <h3>合规检查</h3>
                    <p>自动检查合规性</p>
                  </div>
                  <div className="feature-card">
                    <h3>评分解读</h3>
                    <p>解读安全评分结果</p>
                  </div>
                </div>
              </main>
            </div>
          ) : (
            <Navigate to="/login" replace />
          )
        }
      />
      <Route
        path="/query"
        element={
          isAuthenticated ? <LogQuery /> : <Navigate to="/login" replace />
        }
      />
      <Route 
        path="/" 
        element={
          isAuthenticated ? <Navigate to="/dashboard" replace /> : 
          <Navigate to="/login" replace />
        } 
      />
      <Route 
        path="*" 
        element={<Navigate to="/" replace />} 
      />
    </Routes>
  );
}

export default App;

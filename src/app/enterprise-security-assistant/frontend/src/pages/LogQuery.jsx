import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { queryAPI } from '../api/query';
import './LogQuery.css';

function LogQuery() {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [history, setHistory] = useState([]);
  
  // 用户信息
  const [userInfo, setUserInfo] = useState(null);
  
  useEffect(() => {
    // 获取用户信息
    const storedUserInfo = localStorage.getItem('user_info');
    if (storedUserInfo) {
      setUserInfo(JSON.parse(storedUserInfo));
    } else {
      // 如果没有用户信息，跳转到登录
      navigate('/login');
    }
  }, [navigate]);
  
  // 示例查询
  const exampleQueries = [
    '查询2024年1月的销售额差异',
    '对比上周和本周的日志数据',
    '查看系统异常日志',
    '分析用户登录失败原因',
  ];
  
  const handleQuery = async (queryText = null) => {
    const finalQuery = queryText || query;
    if (!finalQuery.trim()) {
      setError('请输入查询内容');
      return;
    }
    
    if (!userInfo) {
      setError('用户信息不存在，请重新登录');
      navigate('/login');
      return;
    }
    
    setLoading(true);
    setError('');
    setResult(null);
    
    try {
      const response = await queryAPI.unifiedQuery(
        finalQuery,
        userInfo.tenant_id,
        userInfo.user_id,
        null,
        {}
      );
      
      setResult(response);
      
      // 添加到历史记录
      setHistory(prev => [
        {
          query: finalQuery,
          intent: response.intent,
          confidence: response.confidence,
          timestamp: new Date().toISOString(),
        },
        ...prev.slice(0, 9), // 保留最近10条
      ]);
      
    } catch (err) {
      console.error('查询失败:', err);
      setError(err.response?.data?.detail || '查询失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  };
  
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleQuery();
    }
  };
  
  const handleLogout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('user_info');
    navigate('/login');
  };
  
  const getIntentLabel = (intent) => {
    const intentMap = {
      'query_diff': '日志查询差异',
      'scoring_explanation': '评分解读',
      'threat_analysis': '威胁分析',
      'compliance_check': '合规检查',
      'knowledge_search': '知识检索',
      'general': '一般查询',
    };
    return intentMap[intent] || intent;
  };
  
  return (
    <div className="log-query-container">
      <header className="query-header">
        <div className="header-left">
          <h1>日志查询</h1>
          <span className="user-info">
            {userInfo?.username && `用户: ${userInfo.username}`}
          </span>
        </div>
        <div className="header-right">
          <button onClick={() => navigate('/dashboard')} className="nav-btn">
            返回首页
          </button>
          <button onClick={handleLogout} className="logout-btn">
            退出登录
          </button>
        </div>
      </header>
      
      <main className="query-main">
        <section className="query-input-section">
          <div className="query-input-wrapper">
            <textarea
              className="query-input"
              placeholder="请输入查询内容，例如：查询2024年1月的销售额差异..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyPress={handleKeyPress}
              rows={3}
            />
            <button 
              className="query-btn"
              onClick={() => handleQuery()}
              disabled={loading || !query.trim()}
            >
              {loading ? '查询中...' : '查询'}
            </button>
          </div>
          
          <div className="example-queries">
            <span className="example-label">示例查询：</span>
            {exampleQueries.map((eq, index) => (
              <button
                key={index}
                className="example-btn"
                onClick={() => handleQuery(eq)}
                disabled={loading}
              >
                {eq}
              </button>
            ))}
          </div>
        </section>
        
        {error && (
          <div className="error-message">
            {error}
          </div>
        )}
        
        {result && (
          <section className="result-section">
            <div className="result-header">
              <h2>查询结果</h2>
              <div className="result-meta">
                <span className="intent-badge">
                  意图: {getIntentLabel(result.intent)}
                </span>
                <span className="confidence-badge">
                  置信度: {(result.confidence * 100).toFixed(1)}%
                </span>
              </div>
            </div>
            
            <div className="result-content">
              {result.result && typeof result.result === 'object' ? (
                <pre className="result-json">
                  {JSON.stringify(result.result, null, 2)}
                </pre>
              ) : (
                <p>{result.result}</p>
              )}
            </div>
            
            {result.suggested_followup && result.suggested_followup.length > 0 && (
              <div className="suggested-followup">
                <h3>建议的后续查询：</h3>
                <div className="followup-list">
                  {result.suggested_followup.map((item, index) => (
                    <button
                      key={index}
                      className="followup-btn"
                      onClick={() => {
                        setQuery(item);
                        handleQuery(item);
                      }}
                    >
                      {item}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </section>
        )}
        
        {history.length > 0 && (
          <section className="history-section">
            <h2>查询历史</h2>
            <div className="history-list">
              {history.map((item, index) => (
                <div key={index} className="history-item">
                  <div className="history-query">{item.query}</div>
                  <div className="history-meta">
                    <span className="history-intent">
                      {getIntentLabel(item.intent)}
                    </span>
                    <span className="history-confidence">
                      {(item.confidence * 100).toFixed(1)}%
                    </span>
                    <span className="history-time">
                      {new Date(item.timestamp).toLocaleString()}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

export default LogQuery;
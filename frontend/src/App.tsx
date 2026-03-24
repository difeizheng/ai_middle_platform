import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';

// 页面组件
import Layout from './pages/Layout';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import ModelManagement from './pages/ModelManagement';
import KnowledgeManagement from './pages/KnowledgeManagement';
import ApplicationManagement from './pages/ApplicationManagement';
import LogQuery from './pages/LogQuery';
import SkillsMarket from './pages/SkillsMarket';
import BillingManagement from './pages/BillingManagement';  // 计费管理
import QuotaManagement from './pages/QuotaManagement';  // 配额管理
import AlertManagement from './pages/AlertManagement';  // 告警中心

// 受保护路由
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem('token');
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

function App() {
  return (
    <ConfigProvider locale={zhCN}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Dashboard />} />
            <Route path="models" element={<ModelManagement />} />
            <Route path="knowledge" element={<KnowledgeManagement />} />
            <Route path="applications" element={<ApplicationManagement />} />
            <Route path="skills" element={<SkillsMarket />} />
            <Route path="logs" element={<LogQuery />} />
            <Route path="billing" element={<BillingManagement />} />
            <Route path="quota" element={<QuotaManagement />} />
            <Route path="alerts" element={<AlertManagement />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  );
}

export default App;

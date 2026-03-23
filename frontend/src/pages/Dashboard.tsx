/**
 * 控制台首页
 */
import React, { useEffect, useState } from 'react';
import { Card, Row, Col, Statistic, Progress, Table, Tag } from 'antd';
import {
  ApiOutlined,
  DatabaseOutlined,
  AppstoreOutlined,
  CheckCircleOutlined,
} from '@ant-design/icons';
import { request } from '@/utils/request';

interface Stats {
  total_calls: number;
  success_calls: number;
  avg_latency_ms: number;
  total_tokens: number;
}

const Dashboard: React.FC = () => {
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await request.get('/logs/stats?days=7');
        setStats(response.data);
      } catch (error) {
        console.error('获取统计失败:', error);
      } finally {
        setLoading(false);
      }
    };
    fetchStats();
  }, []);

  const columns = [
    {
      title: '端点',
      dataIndex: 'endpoint',
      key: 'endpoint',
    },
    {
      title: '调用次数',
      dataIndex: 'calls',
      key: 'calls',
    },
    {
      title: '平均延迟',
      dataIndex: 'avg_latency',
      key: 'avg_latency',
      render: (latency: number) => `${latency.toFixed(2)} ms`,
    },
    {
      title: '成功率',
      dataIndex: 'success_rate',
      key: 'success_rate',
      render: (rate: number) => (
        <Progress
          percent={rate}
          strokeColor={rate > 95 ? '#52c41a' : '#faad14'}
          size="small"
        />
      ),
    },
    {
      title: '状态',
      key: 'status',
      render: () => <Tag icon={<CheckCircleOutlined />} color="success">正常</Tag>,
    },
  ];

  const apiData = [
    { key: 1, endpoint: '/api/v1/inference/chat', calls: 1234, avg_latency: 245.5, success_rate: 99.2 },
    { key: 2, endpoint: '/api/v1/inference/embeddings', calls: 567, avg_latency: 89.3, success_rate: 98.5 },
    { key: 3, endpoint: '/api/v1/knowledge/search', calls: 890, avg_latency: 156.8, success_rate: 97.8 },
  ];

  return (
    <div>
      <h2 style={{ marginBottom: 24 }}>控制台</h2>

      {/* 统计卡片 */}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card loading={loading}>
            <Statistic
              title="7 日调用次数"
              value={stats?.total_calls || 0}
              prefix={<ApiOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card loading={loading}>
            <Statistic
              title="成功率"
              value={(stats?.success_calls || 0) / (stats?.total_calls || 1) * 100}
              precision={2}
              suffix="%"
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card loading={loading}>
            <Statistic
              title="平均延迟"
              value={stats?.avg_latency_ms || 0}
              precision={2}
              suffix="ms"
              prefix={<DatabaseOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card loading={loading}>
            <Statistic
              title="Token 使用量"
              value={stats?.total_tokens || 0}
              prefix={<AppstoreOutlined />}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
      </Row>

      {/* API 调用统计 */}
      <Card title="API 调用统计" style={{ marginTop: 16 }}>
        <Table columns={columns} dataSource={apiData} pagination={false} />
      </Card>
    </div>
  );
};

export default Dashboard;

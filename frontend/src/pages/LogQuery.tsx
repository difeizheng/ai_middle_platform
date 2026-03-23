/**
 * 日志查询页面
 */
import React, { useEffect, useState } from 'react';
import { Card, Table, DatePicker, Select, Input, Button, Space, Tag } from 'antd';
import { SearchOutlined, ReloadOutlined } from '@ant-design/icons';
import { request } from '@/utils/request';
import dayjs from 'dayjs';

const { RangePicker } = DatePicker;

interface APILog {
  id: number;
  trace_id: string;
  request_id: string;
  method: string;
  path: string;
  endpoint: string;
  response_status: number;
  latency_ms: number;
  model_name: string;
  tokens_used: number;
  is_success: boolean;
  created_at: string;
}

const LogQuery: React.FC = () => {
  const [logs, setLogs] = useState<APILog[]>([]);
  const [loading, setLoading] = useState(true);
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs] | null>(null);
  const [endpoint, setEndpoint] = useState<string>('');

  const fetchLogs = async () => {
    setLoading(true);
    try {
      let url = '/logs/api-calls?limit=100';
      if (dateRange) {
        const days = dateRange[1].diff(dateRange[0], 'day');
        url += `&days=${days || 1}`;
      }
      if (endpoint) {
        url += `&endpoint=${endpoint}`;
      }
      const response = await request.get(url);
      setLogs(response.data.logs || []);
    } catch (error) {
      console.error('获取日志失败:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, []);

  const columns = [
    {
      title: '时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
    },
    {
      title: '方法',
      dataIndex: 'method',
      key: 'method',
      width: 80,
      render: (method: string) => (
        <Tag color={method === 'GET' ? 'green' : 'blue'}>{method}</Tag>
      ),
    },
    {
      title: '端点',
      dataIndex: 'endpoint',
      key: 'endpoint',
      ellipsis: true,
    },
    {
      title: '状态',
      dataIndex: 'response_status',
      key: 'response_status',
      width: 80,
      render: (status: number) => (
        <Tag color={status >= 200 && status < 300 ? 'green' : 'red'}>{status}</Tag>
      ),
    },
    {
      title: '延迟',
      dataIndex: 'latency_ms',
      key: 'latency_ms',
      width: 100,
      render: (latency: number) => `${latency.toFixed(2)} ms`,
    },
    {
      title: '模型',
      dataIndex: 'model_name',
      key: 'model_name',
      width: 120,
    },
    {
      title: 'Token',
      dataIndex: 'tokens_used',
      key: 'tokens_used',
      width: 80,
    },
  ];

  return (
    <div>
      <Card title="日志查询">
        {/* 筛选区域 */}
        <Space style={{ marginBottom: 16 }}>
          <RangePicker
            value={dateRange}
            onChange={(dates) => setDateRange(dates as [dayjs.Dayjs, dayjs.Dayjs] | null)}
          />
          <Select
            style={{ width: 200 }}
            placeholder="选择端点"
            value={endpoint}
            onChange={setEndpoint}
            allowClear
          >
            <Select.Option value="/inference/chat">聊天补全</Select.Option>
            <Select.Option value="/inference/embeddings">向量化</Select.Option>
            <Select.Option value="/knowledge/search">知识检索</Select.Option>
          </Select>
          <Button type="primary" icon={<SearchOutlined />} onClick={fetchLogs}>
            查询
          </Button>
          <Button icon={<ReloadOutlined />} onClick={fetchLogs}>
            刷新
          </Button>
        </Space>

        {/* 日志表格 */}
        <Table
          columns={columns}
          dataSource={logs}
          loading={loading}
          rowKey="id"
          pagination={{ pageSize: 20 }}
        />
      </Card>
    </div>
  );
};

export default LogQuery;

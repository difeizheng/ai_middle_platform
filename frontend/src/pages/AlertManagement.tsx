/**
 * 告警中心管理页面
 * 支持余额预警、配额预警、成本预警管理
 */
import React, { useState, useEffect } from 'react';
import {
  Table,
  Card,
  Button,
  Tag,
  Space,
  Modal,
  Form,
  Input,
  InputNumber,
  Select,
  message,
  Tabs,
  Statistic,
  Row,
  Col,
  DatePicker,
  Switch,
  Descriptions,
} from 'antd';
import {
  AlertOutlined,
  BellOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  PlusOutlined,
  SettingOutlined,
  RefreshOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';

const { RangePicker } = DatePicker;
const { TextArea } = Input;
const { Option } = Select;
const { TabPane } = Tabs;

// 告警类型
interface AlertChannel {
  id: number;
  name: string;
  channel_type: string;
  display_name: string;
  config: Record<string, any>;
  is_active: boolean;
  created_at: string;
}

// 告警订阅
interface AlertSubscription {
  id: number;
  user_id: number;
  alert_type: string;
  resource_type: string;
  resource_id: string;
  channel_ids: number[];
  is_enabled: boolean;
  custom_threshold?: number;
  created_at: string;
}

// 预警记录
interface WarningAlert {
  id: number;
  alert_type: string;
  alert_subtype: string;
  resource_type: string;
  resource_id: string;
  user_id: number;
  current_value: number;
  threshold_value: number;
  unit: string;
  severity: string;
  status: string;
  message: string;
  notified_channels: string[];
  notified_at?: string;
  created_at: string;
  resolved_at?: string;
}

// 告警统计
interface AlertStats {
  total: number;
  by_status: Record<string, number>;
  by_type: Record<string, number>;
  by_severity: Record<string, number>;
}

const AlertManagement: React.FC = () => {
  const [activeTab, setActiveTab] = useState<string>('warnings');
  const [loading, setLoading] = useState(false);
  const [channels, setChannels] = useState<AlertChannel[]>([]);
  const [subscriptions, setSubscriptions] = useState<AlertSubscription[]>([]);
  const [warnings, setWarnings] = useState<WarningAlert[]>([]);
  const [stats, setStats] = useState<AlertStats | null>(null);
  const [total, setTotal] = useState(0);
  const [channelModalVisible, setChannelModalVisible] = useState(false);
  const [subscriptionModalVisible, setSubscriptionModalVisible] = useState(false);
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [selectedAlert, setSelectedAlert] = useState<WarningAlert | null>(null);
  const [form] = Form.useForm();
  const [subscriptionForm] = Form.useForm();
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs] | null>(null);

  // 告警类型映射
  const alertTypeMap: Record<string, { text: string; color: string }> = {
    balance: { text: '余额预警', color: 'orange' },
    quota: { text: '配额预警', color: 'blue' },
    cost: { text: '成本预警', color: 'purple' },
  };

  // 严重级别映射
  const severityMap: Record<string, { text: string; color: string }> = {
    info: { text: '提示', color: 'blue' },
    warning: { text: '警告', color: 'orange' },
    error: { text: '错误', color: 'red' },
    critical: { text: '严重', color: 'magenta' },
  };

  // 状态映射
  const statusMap: Record<string, { text: string; color: string }> = {
    pending: { text: '待处理', color: 'orange' },
    sent: { text: '已通知', color: 'blue' },
    acknowledged: { text: '已确认', color: 'cyan' },
    resolved: { text: '已解决', color: 'green' },
  };

  // 加载告警渠道
  const loadChannels = async () => {
    try {
      const response = await fetch('/api/v1/alert/channels', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });
      const data = await response.json();
      if (data.success) {
        setChannels(data.data);
      }
    } catch (error) {
      console.error('加载告警渠道失败:', error);
    }
  };

  // 加载告警订阅
  const loadSubscriptions = async () => {
    try {
      const response = await fetch('/api/v1/alert/subscriptions', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });
      const data = await response.json();
      if (data.success) {
        setSubscriptions(data.data);
      }
    } catch (error) {
      console.error('加载告警订阅失败:', error);
    }
  };

  // 加载预警记录
  const loadWarnings = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      params.set('limit', '50');
      params.set('offset', '0');

      if (dateRange) {
        params.set('start_date', dateRange[0].toISOString());
        params.set('end_date', dateRange[1].toISOString());
      }

      const response = await fetch(`/api/v1/alert/warnings?${params.toString()}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });
      const data = await response.json();
      if (data.success) {
        setWarnings(data.data);
        setTotal(data.pagination?.total || data.data.length);
      }
    } catch (error) {
      console.error('加载预警记录失败:', error);
      message.error('加载预警记录失败');
    } finally {
      setLoading(false);
    }
  };

  // 加载告警统计
  const loadStats = async () => {
    try {
      const response = await fetch('/api/v1/alert/stats?days=7', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });
      const data = await response.json();
      if (data.success) {
        setStats(data.data);
      }
    } catch (error) {
      console.error('加载告警统计失败:', error);
    }
  };

  // 运行预警检查
  const runWarningCheck = async () => {
    try {
      const response = await fetch('/api/v1/alert/check', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify({ check_type: 'all' }),
      });
      const data = await response.json();
      if (data.success) {
        message.success(data.message);
        loadWarnings();
        loadStats();
      }
    } catch (error) {
      console.error('运行预警检查失败:', error);
      message.error('运行预警检查失败');
    }
  };

  // 确认预警
  const acknowledgeAlert = async (alertId: number) => {
    try {
      const response = await fetch(`/api/v1/alert/warnings/${alertId}/acknowledge`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });
      const data = await response.json();
      if (data.success) {
        message.success('预警已确认');
        loadWarnings();
        loadStats();
      }
    } catch (error) {
      console.error('确认预警失败:', error);
      message.error('确认预警失败');
    }
  };

  // 解决预警
  const resolveAlert = async (alertId: number) => {
    try {
      const response = await fetch(`/api/v1/alert/warnings/${alertId}/resolve`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });
      const data = await response.json();
      if (data.success) {
        message.success('预警已解决');
        loadWarnings();
        loadStats();
      }
    } catch (error) {
      console.error('解决预警失败:', error);
      message.error('解决预警失败');
    }
  };

  // 创建告警渠道
  const createChannel = async (values: any) => {
    try {
      const response = await fetch('/api/v1/alert/channels', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify(values),
      });
      const data = await response.json();
      if (data.success) {
        message.success('告警渠道创建成功');
        setChannelModalVisible(false);
        form.resetFields();
        loadChannels();
      }
    } catch (error) {
      console.error('创建告警渠道失败:', error);
      message.error('创建告警渠道失败');
    }
  };

  // 创建告警订阅
  const createSubscription = async (values: any) => {
    try {
      const response = await fetch('/api/v1/alert/subscriptions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify({
          ...values,
          channel_ids: values.channel_ids || [],
        }),
      });
      const data = await response.json();
      if (data.success) {
        message.success('告警订阅创建成功');
        setSubscriptionModalVisible(false);
        subscriptionForm.resetFields();
        loadSubscriptions();
      }
    } catch (error) {
      console.error('创建告警订阅失败:', error);
      message.error('创建告警订阅失败');
    }
  };

  // 切换订阅启用状态
  const toggleSubscription = async (subscriptionId: number, isEnabled: boolean) => {
    try {
      const response = await fetch(`/api/v1/alert/subscriptions/${subscriptionId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify({ is_enabled: isEnabled }),
      });
      const data = await response.json();
      if (data.success) {
        message.success(isEnabled ? '订阅已启用' : '订阅已禁用');
        loadSubscriptions();
      }
    } catch (error) {
      console.error('更新订阅失败:', error);
      message.error('更新订阅失败');
    }
  };

  useEffect(() => {
    loadChannels();
    loadSubscriptions();
    loadWarnings();
    loadStats();
  }, []);

  // 预警记录表格列
  const warningColumns: ColumnsType<WarningAlert> = [
    {
      title: '告警类型',
      dataIndex: 'alert_type',
      key: 'alert_type',
      width: 120,
      render: (type: string) => (
        <Tag color={alertTypeMap[type]?.color || 'default'}>
          {alertTypeMap[type]?.text || type}
        </Tag>
      ),
    },
    {
      title: '严重级别',
      dataIndex: 'severity',
      key: 'severity',
      width: 100,
      render: (severity: string) => (
        <Tag color={severityMap[severity]?.color || 'default'}>
          {severityMap[severity]?.text || severity}
        </Tag>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => (
        <Tag color={statusMap[status]?.color || 'default'}>
          {statusMap[status]?.text || status}
        </Tag>
      ),
    },
    {
      title: '资源',
      key: 'resource',
      width: 150,
      render: (_, record) => (
        <div>
          <div>{record.resource_type}</div>
          <div style={{ fontSize: 12, color: '#999' }}>{record.resource_id}</div>
        </div>
      ),
    },
    {
      title: '当前值 / 阈值',
      key: 'values',
      width: 150,
      render: (_, record) => (
        <div>
          <div>{record.current_value} {record.unit}</div>
          <div style={{ fontSize: 12, color: '#999' }}>阈值：{record.threshold_value}</div>
        </div>
      ),
    },
    {
      title: '消息',
      dataIndex: 'message',
      key: 'message',
      ellipsis: true,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (date: string) => dayjs(date).format('YYYY-MM-DD HH:mm:ss'),
    },
    {
      title: '操作',
      key: 'action',
      width: 200,
      render: (_, record) => (
        <Space>
          <Button
            size="small"
            onClick={() => {
              setSelectedAlert(record);
              setDetailModalVisible(true);
            }}
          >
            详情
          </Button>
          {record.status === 'pending' && (
            <Button
              size="small"
              icon={<CheckCircleOutlined />}
              onClick={() => acknowledgeAlert(record.id)}
            >
              确认
            </Button>
          )}
          {record.status !== 'resolved' && (
            <Button
              size="small"
              type="primary"
              icon={<CheckCircleOutlined />}
              onClick={() => resolveAlert(record.id)}
            >
              解决
            </Button>
          )}
        </Space>
      ),
    },
  ];

  // 告警渠道表格列
  const channelColumns: ColumnsType<AlertChannel> = [
    {
      title: '渠道名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '显示名称',
      dataIndex: 'display_name',
      key: 'display_name',
    },
    {
      title: '类型',
      dataIndex: 'channel_type',
      key: 'channel_type',
      render: (type: string) => type.toUpperCase(),
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (active: boolean) => (
        <Tag color={active ? 'green' : 'red'}>{active ? '启用' : '禁用'}</Tag>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (date: string) => dayjs(date).format('YYYY-MM-DD HH:mm:ss'),
    },
  ];

  // 告警订阅表格列
  const subscriptionColumns: ColumnsType<AlertSubscription> = [
    {
      title: '告警类型',
      dataIndex: 'alert_type',
      key: 'alert_type',
      render: (type: string) => (
        <Tag color={alertTypeMap[type]?.color || 'default'}>
          {alertTypeMap[type]?.text || type}
        </Tag>
      ),
    },
    {
      title: '资源',
      key: 'resource',
      render: (_, record) => (
        <div>
          <div>{record.resource_type || '全局'}</div>
          {record.resource_id && (
            <div style={{ fontSize: 12, color: '#999' }}>{record.resource_id}</div>
          )}
        </div>
      ),
    },
    {
      title: '通知渠道',
      dataIndex: 'channel_ids',
      key: 'channel_ids',
      render: (ids: number[]) => {
        const names = ids.map(id => {
          const ch = channels.find(c => c.id === id);
          return ch?.display_name || id.toString();
        });
        return names.join(', ');
      },
    },
    {
      title: '自定义阈值',
      dataIndex: 'custom_threshold',
      key: 'custom_threshold',
      render: (value?: number) => value ? `${value}%` : '-',
    },
    {
      title: '状态',
      dataIndex: 'is_enabled',
      key: 'is_enabled',
      render: (enabled: boolean, record: AlertSubscription) => (
        <Switch
          checked={enabled}
          onChange={(checked) => toggleSubscription(record.id, checked)}
          checkedChildren="启用"
          unCheckedChildren="禁用"
        />
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (date: string) => dayjs(date).format('YYYY-MM-DD HH:mm:ss'),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      {/* 统计卡片 */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="总预警数"
              value={stats?.total || 0}
              prefix={<AlertOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="待处理"
              value={stats?.by_status?.pending || 0}
              prefix={<BellOutlined />}
              valueStyle={{ color: '#fa8c16' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="已确认"
              value={stats?.by_status?.acknowledged || 0}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#13c2c2' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="已解决"
              value={stats?.by_status?.resolved || 0}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 主内容 */}
      <Card>
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          tabBarExtraContent={
            <Space>
              {activeTab === 'warnings' && (
                <>
                  <RangePicker
                    value={dateRange}
                    onChange={(dates) => setDateRange(dates as any)}
                    onOk={() => loadWarnings()}
                  />
                  <Button icon={<RefreshOutlined />} onClick={runWarningCheck}>
                    运行检查
                  </Button>
                  <Button icon={<RefreshOutlined />} onClick={loadWarnings}>
                    刷新
                  </Button>
                </>
              )}
              {activeTab === 'channels' && (
                <Button type="primary" icon={<PlusOutlined />} onClick={() => setChannelModalVisible(true)}>
                  新增渠道
                </Button>
              )}
              {activeTab === 'subscriptions' && (
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={() => setSubscriptionModalVisible(true)}
                >
                  新增订阅
                </Button>
              )}
            </Space>
          }
        >
          {/* 预警记录 */}
          <TabPane tab="预警记录" key="warnings">
            <Table
              columns={warningColumns}
              dataSource={warnings}
              rowKey="id"
              loading={loading}
              pagination={{
                showSizeChanger: true,
                showTotal: (total) => `共 ${total} 条`,
              }}
            />
          </TabPane>

          {/* 告警渠道 */}
          <TabPane tab="通知渠道" key="channels">
            <Table
              columns={channelColumns}
              dataSource={channels}
              rowKey="id"
              pagination={false}
            />
          </TabPane>

          {/* 告警订阅 */}
          <TabPane tab="告警订阅" key="subscriptions">
            <Table
              columns={subscriptionColumns}
              dataSource={subscriptions}
              rowKey="id"
              pagination={false}
            />
          </TabPane>
        </Tabs>
      </Card>

      {/* 告警渠道创建弹窗 */}
      <Modal
        title="创建告警渠道"
        open={channelModalVisible}
        onCancel={() => setChannelModalVisible(false)}
        footer={null}
      >
        <Form form={form} layout="vertical" onFinish={createChannel}>
          <Form.Item
            name="name"
            label="渠道名称"
            rules={[{ required: true, message: '请输入渠道名称' }]}
          >
            <Input placeholder="例如：admin-email" />
          </Form.Item>
          <Form.Item
            name="display_name"
            label="显示名称"
            rules={[{ required: true, message: '请输入显示名称' }]}
          >
            <Input placeholder="例如：管理员邮箱" />
          </Form.Item>
          <Form.Item
            name="channel_type"
            label="渠道类型"
            rules={[{ required: true, message: '请选择渠道类型' }]}
          >
            <Select placeholder="请选择">
              <Option value="email">邮件</Option>
              <Option value="sms">短信</Option>
              <Option value="webhook">Webhook</Option>
              <Option value="slack">Slack</Option>
            </Select>
          </Form.Item>
          <Form.Item
            name="config"
            label="渠道配置"
            tooltip="JSON 格式，例如邮件渠道：{'recipient_email': 'admin@example.com'}"
          >
            <TextArea rows={4} placeholder='{"recipient_email": "admin@example.com"}' />
          </Form.Item>
          <Form.Item
            name="is_active"
            label="启用状态"
            valuePropName="checked"
            initialValue={true}
          >
            <Switch checkedChildren="启用" unCheckedChildren="禁用" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit">
              创建
            </Button>
          </Form.Item>
        </Form>
      </Modal>

      {/* 告警订阅创建弹窗 */}
      <Modal
        title="创建告警订阅"
        open={subscriptionModalVisible}
        onCancel={() => setSubscriptionModalVisible(false)}
        footer={null}
      >
        <Form form={subscriptionForm} layout="vertical" onFinish={createSubscription}>
          <Form.Item
            name="alert_type"
            label="告警类型"
            rules={[{ required: true, message: '请选择告警类型' }]}
          >
            <Select placeholder="请选择">
              <Option value="balance">余额预警</Option>
              <Option value="quota">配额预警</Option>
              <Option value="cost">成本预警</Option>
            </Select>
          </Form.Item>
          <Form.Item
            name="resource_type"
            label="资源类型"
          >
            <Select placeholder="可选" allowClear>
              <Option value="account">账户</Option>
              <Option value="app">应用</Option>
              <Option value="api_key">API Key</Option>
            </Select>
          </Form.Item>
          <Form.Item
            name="resource_id"
            label="资源 ID"
            tooltip="不填表示全局订阅"
          >
            <Input placeholder="用户 ID/应用 ID/APIKey ID" />
          </Form.Item>
          <Form.Item
            name="channel_ids"
            label="通知渠道"
          >
            <Select mode="multiple" placeholder="选择通知渠道">
              {channels.map(ch => (
                <Option key={ch.id} value={ch.id}>{ch.display_name}</Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item
            name="custom_threshold"
            label="自定义阈值 (%)"
            tooltip="可选，覆盖系统默认阈值"
          >
            <InputNumber min={1} max={100} placeholder="80" style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit">
              创建
            </Button>
          </Form.Item>
        </Form>
      </Modal>

      {/* 预警详情弹窗 */}
      <Modal
        title="预警详情"
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setDetailModalVisible(false)}>
            关闭
          </Button>,
          selectedAlert?.status === 'pending' && (
            <Button
              key="acknowledge"
              icon={<CheckCircleOutlined />}
              onClick={() => {
                acknowledgeAlert(selectedAlert!.id);
                setDetailModalVisible(false);
              }}
            >
              确认
            </Button>
          ),
          selectedAlert && selectedAlert.status !== 'resolved' && (
            <Button
              key="resolve"
              type="primary"
              icon={<CheckCircleOutlined />}
              onClick={() => {
                resolveAlert(selectedAlert!.id);
                setDetailModalVisible(false);
              }}
            >
              解决
            </Button>
          ),
        ]}
      >
        {selectedAlert && (
          <Descriptions column={1}>
            <Descriptions.Item label="告警类型">
              <Tag color={alertTypeMap[selectedAlert.alert_type]?.color}>
                {alertTypeMap[selectedAlert.alert_type]?.text}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="子类型">{selectedAlert.alert_subtype}</Descriptions.Item>
            <Descriptions.Item label="严重级别">
              <Tag color={severityMap[selectedAlert.severity]?.color}>
                {severityMap[selectedAlert.severity]?.text}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="状态">
              <Tag color={statusMap[selectedAlert.status]?.color}>
                {statusMap[selectedAlert.status]?.text}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="资源类型">{selectedAlert.resource_type}</Descriptions.Item>
            <Descriptions.Item label="资源 ID">{selectedAlert.resource_id}</Descriptions.Item>
            <Descriptions.Item label="当前值">{selectedAlert.current_value} {selectedAlert.unit}</Descriptions.Item>
            <Descriptions.Item label="阈值">{selectedAlert.threshold_value} {selectedAlert.unit}</Descriptions.Item>
            <Descriptions.Item label="消息">{selectedAlert.message}</Descriptions.Item>
            <Descriptions.Item label="通知渠道">
              {selectedAlert.notified_channels?.join(', ') || '-'}
            </Descriptions.Item>
            <Descriptions.Item label="创建时间">
              {dayjs(selectedAlert.created_at).format('YYYY-MM-DD HH:mm:ss')}
            </Descriptions.Item>
            {selectedAlert.notified_at && (
              <Descriptions.Item label="通知时间">
                {dayjs(selectedAlert.notified_at).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
            )}
            {selectedAlert.resolved_at && (
              <Descriptions.Item label="解决时间">
                {dayjs(selectedAlert.resolved_at).format('YYYY-MM-DD HH:mm:ss')}
              </Descriptions.Item>
            )}
          </Descriptions>
        )}
      </Modal>
    </div>
  );
};

export default AlertManagement;

/**
 * 配额管理页面
 * 包含配额列表、创建、编辑、使用情况查询等功能
 */
import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Modal,
  Form,
  Input,
  Select,
  InputNumber,
  message,
  Switch,
  Tag,
  Descriptions,
  Typography,
  Row,
  Col,
  Statistic,
  Progress,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  ReloadOutlined,
  DashboardOutlined,
} from '@ant-design/icons';

const { Title } = Typography;
const { TextArea } = Input;

// 配额类型选项
const QUOTA_TYPES = [
  { value: 'qps', label: 'QPS (每秒请求数)' },
  { value: 'daily_calls', label: '日调用次数' },
  { value: 'token_usage', label: 'Token 用量' },
  { value: 'concurrent', label: '并发数' },
];

// 资源类型选项
const RESOURCE_TYPES = [
  { value: 'model_call', label: '模型调用' },
  { value: 'knowledge_base', label: '知识库' },
  { value: 'agent', label: '智能体' },
  { value: 'skill', label: 'Skill' },
  { value: 'all', label: '全部' },
];

// 周期类型选项
const PERIOD_TYPES = [
  { value: 'hourly', label: '每小时' },
  { value: 'daily', label: '每天' },
  { value: 'weekly', label: '每周' },
  { value: 'monthly', label: '每月' },
  { value: 'none', label: '不重置' },
];

// 超额处理策略
const OVER_LIMIT_ACTIONS = [
  { value: 'reject', label: '拒绝' },
  { value: 'allow', label: '允许' },
  { value: 'log', label: '仅记录' },
];

// 配额层级
const SCOPE_TYPES = [
  { value: 'user', label: '用户级' },
  { value: 'app', label: '应用级' },
  { value: 'api_key', label: 'API Key 级' },
];

const QuotaManagement: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [quotas, setQuotas] = useState<any[]>([]);
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [editModalVisible, setEditModalVisible] = useState(false);
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [currentQuota, setCurrentQuota] = useState<any>(null);
  const [form] = Form.useForm();
  const [editForm] = Form.useForm();

  // 加载配额列表
  const loadQuotas = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/quota/quotas', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });
      const data = await response.json();
      if (data.success) {
        setQuotas(data.data || []);
      }
    } catch (error) {
      console.error('加载配额列表失败:', error);
      message.error('加载配额列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadQuotas();
  }, []);

  // 处理创建配额
  const handleCreate = async (values: any) => {
    try {
      const response = await fetch('/api/v1/quota/quotas', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify(values),
      });
      const data = await response.json();
      if (data.success) {
        message.success('配额创建成功');
        setCreateModalVisible(false);
        form.resetFields();
        loadQuotas();
      } else {
        message.error(data.message || '创建失败');
      }
    } catch (error) {
      message.error('创建失败，请重试');
    }
  };

  // 处理更新配额
  const handleUpdate = async (values: any) => {
    try {
      const response = await fetch(`/api/v1/quota/quotas/${currentQuota.id}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify(values),
      });
      const data = await response.json();
      if (data.success) {
        message.success('配额更新成功');
        setEditModalVisible(false);
        editForm.resetFields();
        loadQuotas();
      } else {
        message.error(data.message || '更新失败');
      }
    } catch (error) {
      message.error('更新失败，请重试');
    }
  };

  // 处理删除配额
  const handleDelete = async (quota: any) => {
    Modal.confirm({
      title: '确认删除',
      content: `确定要删除配额 "${quota.name}" 吗？`,
      onOk: async () => {
        try {
          const response = await fetch(`/api/v1/quota/quotas/${quota.id}`, {
            method: 'DELETE',
            headers: {
              'Authorization': `Bearer ${localStorage.getItem('token')}`,
            },
          });
          const data = await response.json();
          if (data.success) {
            message.success('删除成功');
            loadQuotas();
          } else {
            message.error(data.message || '删除失败');
          }
        } catch (error) {
          message.error('删除失败，请重试');
        }
      },
    });
  };

  // 处理重置配额
  const handleReset = async (quota: any) => {
    Modal.confirm({
      title: '确认重置',
      content: `确定要重置配额 "${quota.name}" 的使用量吗？`,
      onOk: async () => {
        try {
          const response = await fetch(`/api/v1/quota/quotas/${quota.id}/reset`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'Authorization': `Bearer ${localStorage.getItem('token')}`,
            },
            body: JSON.stringify({
              scope_id: quota.scope_id,
              scope_type: quota.scope_type,
            }),
          });
          const data = await response.json();
          if (data.success) {
            message.success('重置成功');
            loadQuotas();
          } else {
            message.error(data.message || '重置失败');
          }
        } catch (error) {
          message.error('重置失败，请重试');
        }
      },
    });
  };

  // 打开编辑弹窗
  const openEditModal = (quota: any) => {
    setCurrentQuota(quota);
    editForm.setFieldsValue({
      name: quota.name,
      description: quota.description,
      quota_type: quota.quota_type,
      resource_type: quota.resource_type,
      limit_value: quota.limit_value,
      unit: quota.unit,
      period_type: quota.period_type,
      reset_time: quota.reset_time,
      over_limit_action: quota.over_limit_action,
      over_limit_rate: quota.over_limit_rate,
      is_active: quota.is_active,
    });
    setEditModalVisible(true);
  };

  // 打开详情弹窗
  const openDetailModal = (quota: any) => {
    setCurrentQuota(quota);
    setDetailModalVisible(true);
  };

  // 表格列定义
  const columns = [
    {
      title: '配额名称',
      dataIndex: 'name',
      key: 'name',
      fixed: 'left' as const,
    },
    {
      title: '配额类型',
      dataIndex: 'quota_type',
      key: 'quota_type',
      render: (type: string) => {
        const typeMap: Record<string, string> = {
          qps: 'QPS',
          daily_calls: '日调用',
          token_usage: 'Token 用量',
          concurrent: '并发数',
        };
        return typeMap[type] || type;
      },
    },
    {
      title: '资源类型',
      dataIndex: 'resource_type',
      key: 'resource_type',
      render: (type: string) => {
        const typeMap: Record<string, string> = {
          model_call: '模型调用',
          knowledge_base: '知识库',
          agent: '智能体',
          skill: 'Skill',
          all: '全部',
        };
        return typeMap[type] || type;
      },
    },
    {
      title: '限制值',
      dataIndex: 'limit_value',
      key: 'limit_value',
      render: (value: number, record: any) => `${value} ${record.unit}`,
    },
    {
      title: '周期类型',
      dataIndex: 'period_type',
      key: 'period_type',
      render: (type: string) => {
        const typeMap: Record<string, string> = {
          hourly: '每小时',
          daily: '每天',
          weekly: '每周',
          monthly: '每月',
          none: '不重置',
        };
        return typeMap[type] || type;
      },
    },
    {
      title: '重置时间',
      dataIndex: 'reset_time',
      key: 'reset_time',
    },
    {
      title: '超额处理',
      dataIndex: 'over_limit_action',
      key: 'over_limit_action',
      render: (action: string) => {
        const actionMap: Record<string, { text: string; color: string }> = {
          reject: { text: '拒绝', color: 'red' },
          allow: { text: '允许', color: 'green' },
          log: { text: '记录', color: 'blue' },
        };
        const config = actionMap[action] || { text: action, color: 'default' };
        return <Tag color={config.color}>{config.text}</Tag>;
      },
    },
    {
      title: '配额层级',
      dataIndex: 'scope_type',
      key: 'scope_type',
      render: (type: string) => {
        const typeMap: Record<string, string> = {
          user: '用户级',
          app: '应用级',
          api_key: 'API Key 级',
        };
        return typeMap[type] || type;
      },
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (active: boolean) => (
        <Tag color={active ? 'green' : 'default'}>{active ? '生效' : '停用'}</Tag>
      ),
    },
    {
      title: '操作',
      key: 'action',
      fixed: 'right' as const,
      render: (_: any, record: any) => (
        <>
          <Button type="link" onClick={() => openDetailModal(record)}>
            详情
          </Button>
          <Button type="link" onClick={() => openEditModal(record)}>
            编辑
          </Button>
          <Button type="link" danger onClick={() => handleDelete(record)}>
            删除
          </Button>
          <Button type="link" onClick={() => handleReset(record)}>
            重置
          </Button>
        </>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 24 }}>
        <Title level={2}>配额管理</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateModalVisible(true)}>
          创建配额
        </Button>
      </div>

      {/* 配额概览统计 */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="配额总数"
              value={quotas.length}
              prefix={<DashboardOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="生效中"
              value={quotas.filter(q => q.is_active).length}
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="QPS 配额"
              value={quotas.filter(q => q.quota_type === 'qps').length}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="日调用配额"
              value={quotas.filter(q => q.quota_type === 'daily_calls').length}
            />
          </Card>
        </Col>
      </Row>

      {/* 配额列表 */}
      <Card title="配额列表">
        <Table
          columns={columns}
          dataSource={quotas}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 20, showSizeChanger: true }}
          scroll={{ x: 1400 }}
        />
      </Card>

      {/* 创建配额弹窗 */}
      <Modal
        title="创建配额"
        open={createModalVisible}
        onCancel={() => setCreateModalVisible(false)}
        footer={null}
        width={700}
      >
        <Form form={form} layout="vertical" onFinish={handleCreate}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="name"
                label="配额名称"
                rules={[{ required: true, message: '请输入配额名称' }]}
              >
                <Input placeholder="例如：每日模型调用配额" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="quota_type"
                label="配额类型"
                rules={[{ required: true, message: '请选择配额类型' }]}
              >
                <Select placeholder="请选择配额类型">
                  {QUOTA_TYPES.map(item => (
                    <Select.Option key={item.value} value={item.value}>{item.label}</Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="resource_type"
                label="资源类型"
                rules={[{ required: true, message: '请选择资源类型' }]}
                initialValue="model_call"
              >
                <Select placeholder="请选择资源类型">
                  {RESOURCE_TYPES.map(item => (
                    <Select.Option key={item.value} value={item.value}>{item.label}</Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="scope_type"
                label="配额层级"
                rules={[{ required: true, message: '请选择配额层级' }]}
                initialValue="user"
              >
                <Select placeholder="请选择配额层级">
                  {SCOPE_TYPES.map(item => (
                    <Select.Option key={item.value} value={item.value}>{item.label}</Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="limit_value"
                label="限制值"
                rules={[{ required: true, message: '请输入限制值' }]}
              >
                <InputNumber style={{ width: '100%' }} min={1} placeholder="例如：1000" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="unit"
                label="单位"
                rules={[{ required: true, message: '请输入单位' }]}
                initialValue="calls"
              >
                <Input placeholder="例如：calls, tokens, requests" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="period_type"
                label="周期类型"
                rules={[{ required: true, message: '请选择周期类型' }]}
                initialValue="daily"
              >
                <Select placeholder="请选择周期类型">
                  {PERIOD_TYPES.map(item => (
                    <Select.Option key={item.value} value={item.value}>{item.label}</Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="reset_time"
                label="重置时间"
                tooltip="每天自动重置的时间，格式：HH:MM"
              >
                <Input placeholder="例如：00:00" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="over_limit_action"
                label="超额处理策略"
                rules={[{ required: true, message: '请选择超额处理策略' }]}
                initialValue="reject"
              >
                <Select placeholder="请选择超额处理策略">
                  {OVER_LIMIT_ACTIONS.map(item => (
                    <Select.Option key={item.value} value={item.value}>{item.label}</Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="over_limit_rate"
                label="超额费率系数"
                tooltip="超额部分的费率倍数，1 表示正常费率"
                initialValue={1}
              >
                <InputNumber style={{ width: '100%' }} min={0} step={0.1} />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="description"
            label="描述"
          >
            <TextArea rows={3} placeholder="请输入配额描述" />
          </Form.Item>

          <Form.Item
            name="is_active"
            label="是否生效"
            initialValue={true}
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>

          <Form.Item>
            <Button type="primary" htmlType="submit" block>
              创建配额
            </Button>
          </Form.Item>
        </Form>
      </Modal>

      {/* 编辑配额弹窗 */}
      <Modal
        title="编辑配额"
        open={editModalVisible}
        onCancel={() => setEditModalVisible(false)}
        footer={null}
        width={700}
      >
        <Form form={editForm} layout="vertical" onFinish={handleUpdate}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="name"
                label="配额名称"
                rules={[{ required: true, message: '请输入配额名称' }]}
              >
                <Input placeholder="请输入配额名称" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="quota_type"
                label="配额类型"
              >
                <Select disabled>
                  {QUOTA_TYPES.map(item => (
                    <Select.Option key={item.value} value={item.value}>{item.label}</Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="limit_value"
                label="限制值"
              >
                <InputNumber style={{ width: '100%' }} min={1} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="unit"
                label="单位"
              >
                <Input />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="period_type"
                label="周期类型"
              >
                <Select>
                  {PERIOD_TYPES.map(item => (
                    <Select.Option key={item.value} value={item.value}>{item.label}</Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="reset_time"
                label="重置时间"
              >
                <Input />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="over_limit_action"
                label="超额处理策略"
              >
                <Select>
                  {OVER_LIMIT_ACTIONS.map(item => (
                    <Select.Option key={item.value} value={item.value}>{item.label}</Select.Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="over_limit_rate"
                label="超额费率系数"
              >
                <InputNumber style={{ width: '100%' }} min={0} step={0.1} />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="description"
            label="描述"
          >
            <TextArea rows={3} />
          </Form.Item>

          <Form.Item
            name="is_active"
            label="是否生效"
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>

          <Form.Item>
            <Button type="primary" htmlType="submit" block>
              保存修改
            </Button>
          </Form.Item>
        </Form>
      </Modal>

      {/* 配额详情弹窗 */}
      <Modal
        title="配额详情"
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        footer={null}
        width={700}
      >
        {currentQuota && (
          <Descriptions column={2} bordered>
            <Descriptions.Item label="配额名称">{currentQuota.name}</Descriptions.Item>
            <Descriptions.Item label="配额类型">{currentQuota.quota_type}</Descriptions.Item>
            <Descriptions.Item label="资源类型">{currentQuota.resource_type}</Descriptions.Item>
            <Descriptions.Item label="限制值">{currentQuota.limit_value} {currentQuota.unit}</Descriptions.Item>
            <Descriptions.Item label="周期类型">{currentQuota.period_type}</Descriptions.Item>
            <Descriptions.Item label="重置时间">{currentQuota.reset_time || '-'}</Descriptions.Item>
            <Descriptions.Item label="超额处理">{currentQuota.over_limit_action}</Descriptions.Item>
            <Descriptions.Item label="超额费率">{currentQuota.over_limit_rate}x</Descriptions.Item>
            <Descriptions.Item label="配额层级">{currentQuota.scope_type}</Descriptions.Item>
            <Descriptions.Item label="层级 ID">{currentQuota.scope_id || '-'}</Descriptions.Item>
            <Descriptions.Item label="状态">
              <Tag color={currentQuota.is_active ? 'green' : 'default'}>
                {currentQuota.is_active ? '生效' : '停用'}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="描述" span={2}>{currentQuota.description || '-'}</Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </div>
  );
};

export default QuotaManagement;

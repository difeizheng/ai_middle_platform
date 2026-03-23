/**
 * 应用管理页面
 */
import React, { useEffect, useState } from 'react';
import { Card, Table, Button, Tag, Space, Modal, Form, Input, Select, message, CopyOutlined } from 'antd';
import { PlusOutlined, KeyOutlined, EyeOutlined } from '@ant-design/icons';
import { request } from '@/utils/request';

interface Application {
  id: number;
  name: string;
  description: string;
  app_type: string;
  is_active: boolean;
  total_calls: number;
}

const ApplicationManagement: React.FC = () => {
  const [applications, setApplications] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalVisible, setModalVisible] = useState(false);
  const [form] = Form.useForm();

  const fetchApplications = async () => {
    try {
      const response = await request.get('/applications');
      setApplications(response.data.applications || []);
    } catch (error) {
      console.error('获取应用列表失败:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchApplications();
  }, []);

  const handleCreate = () => {
    form.resetFields();
    setModalVisible(true);
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      await request.post('/applications', values);
      message.success('创建成功');
      setModalVisible(false);
      fetchApplications();
    } catch (error) {
      console.error('创建失败:', error);
    }
  };

  const columns = [
    {
      title: '应用名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '类型',
      dataIndex: 'app_type',
      key: 'app_type',
      render: (type: string) => {
        const colorMap: Record<string, string> = {
          web: 'blue',
          mobile: 'green',
          api: 'orange',
          internal: 'default',
        };
        return <Tag color={colorMap[type] || 'default'}>{type}</Tag>;
      },
    },
    {
      title: '调用次数',
      dataIndex: 'total_calls',
      key: 'total_calls',
    },
    {
      title: '状态',
      key: 'status',
      render: (_: unknown, record: Application) => (
        <Tag color={record.is_active ? 'green' : 'red'}>
          {record.is_active ? '启用' : '禁用'}
        </Tag>
      ),
    },
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, record: Application) => (
        <Space>
          <Button type="link" icon={<KeyOutlined />}>
            查看 API Key
          </Button>
          <Button type="link" icon={<EyeOutlined />}>
            详情
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Card
        title="应用管理"
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
            创建应用
          </Button>
        }
      >
        <Table columns={columns} dataSource={applications} loading={loading} rowKey="id" />
      </Card>

      {/* 创建应用模态框 */}
      <Modal
        title="创建应用"
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => setModalVisible(false)}
        width={500}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label="应用名称"
            rules={[{ required: true, message: '请输入应用名称' }]}
          >
            <Input placeholder="例如：信贷系统 AI 助手" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={3} placeholder="描述应用的用途" />
          </Form.Item>
          <Form.Item
            name="app_type"
            label="应用类型"
            rules={[{ required: true, message: '请选择应用类型' }]}
          >
            <Select>
              <Select.Option value="web">Web 应用</Select.Option>
              <Select.Option value="mobile">移动应用</Select.Option>
              <Select.Option value="api">API 服务</Select.Option>
              <Select.Option value="internal">内部系统</Select.Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ApplicationManagement;

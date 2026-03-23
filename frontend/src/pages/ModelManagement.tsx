/**
 * 模型管理页面
 */
import React, { useEffect, useState } from 'react';
import { Card, Table, Button, Tag, Space, Modal, Form, Input, InputNumber, Select, message, Switch } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, ApiOutlined } from '@ant-design/icons';
import { request } from '@/utils/request';

interface Model {
  id: number;
  name: string;
  display_name: string;
  model_type: string;
  provider: string;
  is_active: boolean;
  is_default: boolean;
  avg_latency_ms: number;
}

const ModelManagement: React.FC = () => {
  const [models, setModels] = useState<Model[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingModel, setEditingModel] = useState<Model | null>(null);
  const [form] = Form.useForm();

  const fetchModels = async () => {
    try {
      const response = await request.get('/models');
      setModels(response.data.models || []);
    } catch (error) {
      console.error('获取模型列表失败:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchModels();
  }, []);

  const handleAdd = () => {
    setEditingModel(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEdit = (record: Model) => {
    setEditingModel(record);
    form.setFieldsValue({
      name: record.name,
      display_name: record.display_name,
      model_type: record.model_type,
      provider: record.provider,
      base_url: record.base_url,
      max_context_length: record.max_context_length,
      max_tokens: record.max_tokens,
    });
    setModalVisible(true);
  };

  const handleDelete = (record: Model) => {
    Modal.confirm({
      title: '确认删除',
      content: `确定要删除模型 "${record.name}" 吗？`,
      onOk: async () => {
        try {
          await request.delete(`/models/${record.id}`);
          message.success('删除成功');
          fetchModels();
        } catch (error) {
          console.error('删除失败:', error);
        }
      },
    });
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      if (editingModel) {
        await request.put(`/models/${editingModel.id}`, values);
        message.success('更新成功');
      } else {
        await request.post('/models', values);
        message.success('创建成功');
      }
      setModalVisible(false);
      fetchModels();
    } catch (error) {
      console.error('操作失败:', error);
    }
  };

  const columns = [
    {
      title: '模型名称',
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
      dataIndex: 'model_type',
      key: 'model_type',
      render: (type: string) => {
        const colorMap: Record<string, string> = {
          llm: 'blue',
          embedding: 'green',
          rerank: 'orange',
          vision: 'purple',
        };
        return <Tag color={colorMap[type] || 'default'}>{type}</Tag>;
      },
    },
    {
      title: '提供商',
      dataIndex: 'provider',
      key: 'provider',
    },
    {
      title: '状态',
      key: 'status',
      render: (_: unknown, record: Model) => (
        <Space>
          {record.is_default && <Tag color="gold">默认</Tag>}
          <Tag color={record.is_active ? 'green' : 'red'}>
            {record.is_active ? '启用' : '禁用'}
          </Tag>
        </Space>
      ),
    },
    {
      title: '平均延迟',
      dataIndex: 'avg_latency_ms',
      key: 'avg_latency_ms',
      render: (latency: number) => `${latency.toFixed(2)} ms`,
    },
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, record: Model) => (
        <Space>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          <Button
            type="link"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDelete(record)}
          >
            删除
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Card
        title="模型管理"
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
            添加模型
          </Button>
        }
      >
        <Table columns={columns} dataSource={models} loading={loading} rowKey="id" />
      </Card>

      {/* 添加/编辑模态框 */}
      <Modal
        title={editingModel ? '编辑模型' : '添加模型'}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => setModalVisible(false)}
        width={600}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label="模型名称"
            rules={[{ required: true, message: '请输入模型名称' }]}
          >
            <Input placeholder="例如：qwen-72b" disabled={!!editingModel} />
          </Form.Item>
          <Form.Item name="display_name" label="显示名称">
            <Input placeholder="例如：通义千问 72B" />
          </Form.Item>
          <Form.Item
            name="model_type"
            label="模型类型"
            rules={[{ required: true, message: '请选择模型类型' }]}
          >
            <Select>
              <Select.Option value="llm">LLM (大语言模型)</Select.Option>
              <Select.Option value="embedding">Embedding (向量化)</Select.Option>
              <Select.Option value="rerank">Rerank (重排序)</Select.Option>
              <Select.Option value="vision">Vision (视觉)</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item
            name="provider"
            label="提供商"
            rules={[{ required: true, message: '请选择提供商' }]}
          >
            <Select>
              <Select.Option value="openai">OpenAI 兼容</Select.Option>
              <Select.Option value="vllm">vLLM</Select.Option>
              <Select.Option value="local">本地部署</Select.Option>
              <Select.Option value="deepseek">DeepSeek</Select.Option>
              <Select.Option value="zhipu">智谱 AI</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="base_url" label="API 地址">
            <Input placeholder="http://localhost:8000/v1" />
          </Form.Item>
          <Form.Item name="max_context_length" label="最大上下文长度">
            <InputNumber min={1024} max={131072} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="max_tokens" label="最大输出长度">
            <InputNumber min={256} max={32768} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ModelManagement;

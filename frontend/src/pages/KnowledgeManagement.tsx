/**
 * 知识管理页面
 */
import React, { useEffect, useState } from 'react';
import { Card, Table, Button, Tag, Space, Modal, Form, Input, message, Upload, Progress } from 'antd';
import { PlusOutlined, UploadOutlined, SearchOutlined, FileTextOutlined } from '@ant-design/icons';
import { request } from '@/utils/request';
import type { UploadProps } from 'antd';

interface KnowledgeBase {
  id: number;
  name: string;
  description: string;
  document_count: number;
  chunk_count: number;
}

const KnowledgeManagement: React.FC = () => {
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalVisible, setModalVisible] = useState(false);
  const [form] = Form.useForm();

  const fetchKnowledgeBases = async () => {
    try {
      const response = await request.get('/knowledge/bases');
      setKnowledgeBases(response.data.knowledge_bases || []);
    } catch (error) {
      console.error('获取知识库列表失败:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchKnowledgeBases();
  }, []);

  const handleCreate = () => {
    form.resetFields();
    setModalVisible(true);
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      await request.post('/knowledge/bases', values);
      message.success('创建成功');
      setModalVisible(false);
      fetchKnowledgeBases();
    } catch (error) {
      console.error('创建失败:', error);
    }
  };

  const uploadProps: UploadProps = {
    name: 'files',
    action: '/api/v1/knowledge/bases/1/documents/upload',
    headers: {
      Authorization: `Bearer ${localStorage.getItem('token')}`,
    },
    multiple: true,
    accept: '.pdf,.docx,.xlsx,.pptx,.txt,.md',
    onChange(info) {
      if (info.file.status !== 'uploading') {
        console.log(info.file, info.fileList);
      }
      if (info.file.status === 'done') {
        message.success(`${info.file.name} 上传成功`);
      } else if (info.file.status === 'error') {
        message.error(`${info.file.name} 上传失败`);
      }
    },
  };

  const columns = [
    {
      title: '知识库名称',
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
      title: '文档数量',
      dataIndex: 'document_count',
      key: 'document_count',
    },
    {
      title: '分片数量',
      dataIndex: 'chunk_count',
      key: 'chunk_count',
    },
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, record: KnowledgeBase) => (
        <Space>
          <Button type="link" icon={<UploadOutlined />}>
            上传文档
          </Button>
          <Button type="link" icon={<SearchOutlined />}>
            检索测试
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Card
        title="知识管理"
        extra={
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
            创建知识库
          </Button>
        }
      >
        <Table columns={columns} dataSource={knowledgeBases} loading={loading} rowKey="id" />
      </Card>

      {/* 创建知识库模态框 */}
      <Modal
        title="创建知识库"
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => setModalVisible(false)}
        width={500}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label="知识库名称"
            rules={[{ required: true, message: '请输入知识库名称' }]}
          >
            <Input placeholder="例如：公司制度知识库" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={3} placeholder="描述知识库的用途和内容" />
          </Form.Item>
          <Form.Item name="embedding_model" label="Embedding 模型">
            <Select defaultValue="bge-large-zh-v1.5">
              <Select.Option value="bge-large-zh-v1.5">BGE Large Chinese</Select.Option>
              <Select.Option value="text2vec">Text2Vec</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="chunk_size" label="分片大小">
            <Input defaultValue={500} suffix="tokens" />
          </Form.Item>
          <Form.Item name="chunk_overlap" label="分片重叠">
            <Input defaultValue={50} suffix="tokens" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default KnowledgeManagement;

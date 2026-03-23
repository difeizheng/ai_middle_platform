/**
 * Skills 市场页面
 */
import React, { useEffect, useState } from 'react';
import { Card, Table, Button, Tag, Space, Modal, Form, Input, Select, message, Tabs, Descriptions, Statistic } from 'antd';
import { PlusOutlined, PlayCircleOutlined, UninstallOutlined, EyeOutlined, CodeOutlined } from '@ant-design/icons';
import { request } from '@/utils/request';

interface Skill {
  id: string;
  name: string;
  version: string;
  description: string;
  category: string;
  author: string;
  status: 'active' | 'inactive' | 'installed';
}

interface SkillRegistry {
  id: string;
  name: string;
  version: string;
  description: string;
  category: string;
  author: string;
  config_schema: Record<string, any>;
}

const SkillsMarket: React.FC = () => {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [registry, setRegistry] = useState<SkillRegistry[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalVisible, setModalVisible] = useState(false);
  const [executeModalVisible, setExecuteModalVisible] = useState(false);
  const [selectedSkill, setSelectedSkill] = useState<SkillRegistry | null>(null);
  const [form] = Form.useForm();
  const [executeForm] = Form.useForm();

  const fetchSkills = async () => {
    try {
      const response = await request.get('/skills/skills/registry');
      setRegistry(response.data.data || []);
    } catch (error) {
      console.error('获取 Skills 注册表失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchInstalledSkills = async () => {
    try {
      const response = await request.get('/skills/skills/installed');
      setSkills(response.data.data || []);
    } catch (error) {
      console.error('获取已安装 Skills 失败:', error);
    }
  };

  useEffect(() => {
    Promise.all([fetchSkills(), fetchInstalledSkills()]);
  }, []);

  const handleInstall = (skill: SkillRegistry) => {
    setSelectedSkill(skill);
    form.setFieldsValue({
      skill_id: skill.id,
      version: skill.version,
    });
    setModalVisible(true);
  };

  const handleInstallSubmit = async () => {
    try {
      const values = await form.validateFields();
      await request.post('/skills/skills/install', values);
      message.success(`安装 ${values.skill_id} 成功`);
      setModalVisible(false);
      fetchInstalledSkills();
    } catch (error) {
      console.error('安装失败:', error);
    }
  };

  const handleUninstall = async (skill: Skill) => {
    Modal.confirm({
      title: '确认卸载',
      content: `确定要卸载 ${skill.name} 吗？`,
      onOk: async () => {
        try {
          await request.delete(`/skills/skills/${skill.id}/uninstall`);
          message.success('卸载成功');
          fetchInstalledSkills();
        } catch (error) {
          console.error('卸载失败:', error);
          message.error('卸载失败');
        }
      },
    });
  };

  const handleExecute = (skill: SkillRegistry) => {
    setSelectedSkill(skill);
    executeForm.resetFields();
    setExecuteModalVisible(true);
  };

  const handleExecuteSubmit = async () => {
    try {
      const values = await executeForm.validateFields();
      const response = await request.post(`/skills/skills/${selectedSkill?.name}/execute`, values);
      message.success('执行成功');
      setExecuteModalVisible(false);

      // 显示执行结果
      Modal.info({
        title: '执行结果',
        content: <pre>{JSON.stringify(response.data, null, 2)}</pre>,
        width: 600,
      });
    } catch (error) {
      console.error('执行失败:', error);
      message.error('执行失败');
    }
  };

  // 已安装 Skills 表格列
  const installedColumns = [
    {
      title: 'Skill 名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string) => <strong>{name}</strong>,
    },
    {
      title: '版本',
      dataIndex: 'version',
      key: 'version',
      render: (version: string) => <Tag color="blue">{version}</Tag>,
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '状态',
      key: 'status',
      render: (_: unknown, record: Skill) => (
        <Tag color={record.status === 'active' ? 'green' : 'default'}>
          {record.status === 'active' ? '已激活' : '未激活'}
        </Tag>
      ),
    },
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, record: Skill) => (
        <Space>
          <Button
            type="link"
            icon={<PlayCircleOutlined />}
            onClick={() => handleExecute(registry.find(s => s.name === record.name) || record)}
          >
            执行
          </Button>
          <Button
            type="link"
            danger
            icon={<UninstallOutlined />}
            onClick={() => handleUninstall(record)}
          >
            卸载
          </Button>
        </Space>
      ),
    },
  ];

  // Skills 注册表表格列
  const registryColumns = [
    {
      title: 'Skill 名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string) => <strong>{name}</strong>,
    },
    {
      title: '版本',
      dataIndex: 'version',
      key: 'version',
      render: (version: string) => <Tag color="blue">{version}</Tag>,
    },
    {
      title: '分类',
      dataIndex: 'category',
      key: 'category',
      render: (category: string) => {
        const colorMap: Record<string, string> = {
          builtin: 'green',
          analysis: 'blue',
          tool: 'orange',
          extension: 'purple',
        };
        return <Tag color={colorMap[category] || 'default'}>{category}</Tag>;
      },
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '作者',
      dataIndex: 'author',
      key: 'author',
    },
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, record: SkillRegistry) => (
        <Space>
          <Button
            type="link"
            icon={<EyeOutlined />}
            onClick={() => {
              setSelectedSkill(record);
              Modal.info({
                title: 'Skill 详情',
                content: (
                  <Descriptions column={1} bordered>
                    <Descriptions.Item label="名称">{record.name}</Descriptions.Item>
                    <Descriptions.Item label="版本">{record.version}</Descriptions.Item>
                    <Descriptions.Item label="分类">{record.category}</Descriptions.Item>
                    <Descriptions.Item label="作者">{record.author}</Descriptions.Item>
                    <Descriptions.Item label="描述">{record.description}</Descriptions.Item>
                    <Descriptions.Item label="配置 Schema">
                      <pre>{JSON.stringify(record.config_schema, null, 2)}</pre>
                    </Descriptions.Item>
                  </Descriptions>
                ),
                width: 600,
              });
            }}
          >
            详情
          </Button>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => handleInstall(record)}
          >
            安装
          </Button>
        </Space>
      ),
    },
  ];

  const tabItems = [
    {
      key: 'installed',
      label: '已安装 Skills',
      children: (
        <Table
          columns={installedColumns}
          dataSource={skills}
          loading={loading}
          rowKey="id"
          pagination={false}
        />
      ),
    },
    {
      key: 'registry',
      label: 'Skills 注册表',
      children: (
        <Table
          columns={registryColumns}
          dataSource={registry}
          loading={loading}
          rowKey="id"
          pagination={false}
        />
      ),
    },
  ];

  return (
    <div>
      <Card
        title="Skills 市场"
        extra={
          <Space>
            <Statistic title="已安装" value={skills.length} />
            <Statistic title="可用" value={registry.length} />
          </Space>
        }
      >
        <Tabs items={tabItems} defaultActiveKey="installed" />
      </Card>

      {/* 安装 Skill 模态框 */}
      <Modal
        title={`安装 ${selectedSkill?.name || 'Skill'}`}
        open={modalVisible}
        onOk={handleInstallSubmit}
        onCancel={() => setModalVisible(false)}
        width={500}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="skill_id"
            label="Skill ID"
            rules={[{ required: true, message: '请输入 Skill ID' }]}
          >
            <Input disabled />
          </Form.Item>
          <Form.Item
            name="version"
            label="版本"
            rules={[{ required: true, message: '请输入版本号' }]}
          >
            <Input placeholder="例如：1.0.0" />
          </Form.Item>
          <Form.Item name="config" label="配置">
            <Input.TextArea
              rows={6}
              placeholder='JSON 格式配置，例如：{"threshold": 0.8}'
            />
          </Form.Item>
        </Form>
      </Modal>

      {/* 执行 Skill 模态框 */}
      <Modal
        title={`执行 ${selectedSkill?.name || 'Skill'}`}
        open={executeModalVisible}
        onOk={handleExecuteSubmit}
        onCancel={() => setExecuteModalVisible(false)}
        width={600}
      >
        <Form form={executeForm} layout="vertical">
          <Form.Item
            name="params"
            label="执行参数"
            rules={[{ required: true, message: '请输入执行参数' }]}
          >
            <Input.TextArea
              rows={8}
              placeholder='JSON 格式参数，例如：{"data": [...], "operation": "statistic"}'
            />
          </Form.Item>
          <Form.Item name="timeout" label="超时时间 (秒)" initialValue={30}>
            <Input type="number" placeholder="30" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default SkillsMarket;

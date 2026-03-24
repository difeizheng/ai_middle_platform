/**
 * 计费管理页面
 * 包含账户余额、充值、计费记录、账单管理等功能
 */
import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Button,
  Table,
  Tag,
  Modal,
  Form,
  InputNumber,
  Select,
  Radio,
  message,
  Spin,
  Typography,
  Divider,
  Descriptions,
  Tabs,
} from 'antd';
import {
  WalletOutlined,
  RechargeOutlined,
  FileTextOutlined,
  BillOutlined,
  DollarOutlined,
  TrendUpOutlined,
} from '@ant-design/icons';

const { Title } = Typography;
const { TextArea } = Input;

// 计费管理页面组件
const BillingManagement: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [accountInfo, setAccountInfo] = useState<any>(null);
  const [billingRecords, setBillingRecords] = useState<any[]>([]);
  const [monthlyBills, setMonthlyBills] = useState<any[]>([]);
  const [invoices, setInvoices] = useState<any[]>([]);
  const [rechargeModalVisible, setRechargeModalVisible] = useState(false);
  const [invoiceModalVisible, setInvoiceModalVisible] = useState(false);
  const [form] = Form.useForm();
  const [invoiceForm] = Form.useForm();

  // 加载账户信息
  const loadAccountInfo = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/billing/account', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });
      const data = await response.json();
      if (data.success) {
        setAccountInfo(data.data);
      }
    } catch (error) {
      console.error('加载账户信息失败:', error);
    } finally {
      setLoading(false);
    }
  };

  // 加载计费记录
  const loadBillingRecords = async () => {
    try {
      const response = await fetch('/api/v1/billing/account/records?page=1&page_size=10', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });
      const data = await response.json();
      if (data.success) {
        setBillingRecords(data.data.items || []);
      }
    } catch (error) {
      console.error('加载计费记录失败:', error);
    }
  };

  // 加载月度账单
  const loadMonthlyBills = async () => {
    try {
      const response = await fetch('/api/v1/bills/monthly?page=1&page_size=10', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });
      const data = await response.json();
      if (data.success) {
        setMonthlyBills(data.data.items || []);
      }
    } catch (error) {
      console.error('加载月度账单失败:', error);
    }
  };

  // 加载发票列表
  const loadInvoices = async () => {
    try {
      const response = await fetch('/api/v1/bills/invoices?page=1&page_size=10', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });
      const data = await response.json();
      if (data.success) {
        setInvoices(data.data.items || []);
      }
    } catch (error) {
      console.error('加载发票列表失败:', error);
    }
  };

  useEffect(() => {
    loadAccountInfo();
    loadBillingRecords();
    loadMonthlyBills();
    loadInvoices();
  }, []);

  // 处理充值
  const handleRecharge = async (values: any) => {
    try {
      const response = await fetch('/api/v1/payment/create', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify({
          amount: values.amount,
          channel_id: values.channel_id,
          subject: 'AI 中台充值',
        }),
      });
      const data = await response.json();
      if (data.success) {
        message.success('订单创建成功，正在跳转支付...');
        setRechargeModalVisible(false);
        form.resetFields();
        // 跳转支付
        if (data.data.pay_url) {
          window.open(data.data.pay_url, '_blank');
        }
        loadAccountInfo();
      } else {
        message.error(data.message || '充值失败');
      }
    } catch (error) {
      message.error('充值失败，请重试');
    }
  };

  // 处理发票申请
  const handleInvoiceRequest = async (values: any) => {
    try {
      const response = await fetch('/api/v1/bills/invoices/request', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify(values),
      });
      const data = await response.json();
      if (data.success) {
        message.success('发票申请已提交');
        setInvoiceModalVisible(false);
        invoiceForm.resetFields();
        loadInvoices();
      } else {
        message.error(data.message || '申请失败');
      }
    } catch (error) {
      message.error('申请失败，请重试');
    }
  };

  // 计费记录表格列
  const recordsColumns = [
    {
      title: '时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (text: string) => new Date(text).toLocaleString(),
    },
    {
      title: '类型',
      dataIndex: 'record_type',
      key: 'record_type',
      render: (type: string) => {
        const typeMap: Record<string, { text: string; color: string }> = {
          charge: { text: '充值', color: 'green' },
          consume: { text: '消费', color: 'blue' },
          refund: { text: '退款', color: 'orange' },
        };
        const config = typeMap[type] || { text: type, color: 'default' };
        return <Tag color={config.color}>{config.text}</Tag>;
      },
    },
    {
      title: '金额',
      dataIndex: 'amount',
      key: 'amount',
      render: (amount: number, record: any) => (
        <span style={{ color: record.record_type === 'consume' ? '#ff4d4f' : '#52c41a' }}>
          {record.record_type === 'consume' ? '-' : '+'}¥{parseFloat(amount).toFixed(2)}
        </span>
      ),
    },
    {
      title: '余额',
      dataIndex: 'balance_after',
      key: 'balance_after',
      render: (amount: number) => `¥${parseFloat(amount).toFixed(2)}`,
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
        };
        return typeMap[type] || type;
      },
    },
    {
      title: 'Token 用量',
      dataIndex: 'tokens_used',
      key: 'tokens_used',
      render: (tokens: number) => tokens?.toLocaleString() || '-',
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
  ];

  // 月度账单表格列
  const billsColumns = [
    {
      title: '账单月份',
      dataIndex: 'billing_month',
      key: 'billing_month',
    },
    {
      title: '账单金额',
      dataIndex: 'total_amount',
      key: 'total_amount',
      render: (amount: number) => `¥${parseFloat(amount).toFixed(2)}`,
    },
    {
      title: '已支付',
      dataIndex: 'paid_amount',
      key: 'paid_amount',
      render: (amount: number) => `¥${parseFloat(amount).toFixed(2)}`,
    },
    {
      title: '未支付',
      dataIndex: 'unpaid_amount',
      key: 'unpaid_amount',
      render: (amount: number) => `¥${parseFloat(amount).toFixed(2)}`,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const statusMap: Record<string, { text: string; color: string }> = {
          unpaid: { text: '未支付', color: 'red' },
          paid: { text: '已支付', color: 'green' },
          overdue: { text: '逾期', color: 'volcano' },
          cancelled: { text: '已取消', color: 'default' },
        };
        const config = statusMap[status] || { text: status, color: 'default' };
        return <Tag color={config.color}>{config.text}</Tag>;
      },
    },
    {
      title: '支付截止日',
      dataIndex: 'payment_deadline',
      key: 'payment_deadline',
      render: (text: string) => text ? new Date(text).toLocaleDateString() : '-',
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: any) => (
        <>
          {record.status === 'unpaid' && (
            <Button type="link" onClick={() => handlePayBill(record)}>
              支付
            </Button>
          )}
          <Button type="link" onClick={() => handleViewBillDetail(record)}>
            详情
          </Button>
          {record.status === 'paid' && (
            <Button type="link" onClick={() => handleRequestInvoice(record)}>
              开票
            </Button>
          )}
        </>
      ),
    },
  ];

  // 发票表格列
  const invoicesColumns = [
    {
      title: '发票号码',
      dataIndex: 'invoice_no',
      key: 'invoice_no',
    },
    {
      title: '发票抬头',
      dataIndex: 'title',
      key: 'title',
    },
    {
      title: '类型',
      dataIndex: 'invoice_type',
      key: 'invoice_type',
      render: (type: string) => type === 'electronic' ? '电子发票' : '纸质发票',
    },
    {
      title: '金额',
      dataIndex: 'amount',
      key: 'amount',
      render: (amount: number) => `¥${parseFloat(amount).toFixed(2)}`,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => {
        const statusMap: Record<string, { text: string; color: string }> = {
          pending: { text: '待开具', color: 'default' },
          processing: { text: '开具中', color: 'processing' },
          issued: { text: '已开具', color: 'success' },
          delivered: { text: '已交付', color: 'blue' },
          rejected: { text: '已拒绝', color: 'error' },
        };
        const config = statusMap[status] || { text: status, color: 'default' };
        return <Tag color={config.color}>{config.text}</Tag>;
      },
    },
    {
      title: '申请时间',
      dataIndex: 'application_time',
      key: 'application_time',
      render: (text: string) => new Date(text).toLocaleString(),
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: any) => (
        <Button type="link" onClick={() => handleViewInvoiceDetail(record)}>
          详情
        </Button>
      ),
    },
  ];

  const handlePayBill = (bill: any) => {
    message.info(`支付账单：${bill.bill_no}`);
    // TODO: 实现支付逻辑
  };

  const handleViewBillDetail = (bill: any) => {
    Modal.info({
      title: `账单详情 - ${bill.bill_no}`,
      width: 600,
      content: (
        <Descriptions column={2} bordered>
          <Descriptions.Item label="账单月份">{bill.billing_month}</Descriptions.Item>
          <Descriptions.Item label="账单状态">
            <Tag>{bill.status}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="账单总额">¥{parseFloat(bill.total_amount).toFixed(2)}</Descriptions.Item>
          <Descriptions.Item label="已支付金额">¥{parseFloat(bill.paid_amount).toFixed(2)}</Descriptions.Item>
          <Descriptions.Item label="未支付金额">¥{parseFloat(bill.unpaid_amount).toFixed(2)}</Descriptions.Item>
          <Descriptions.Item label="模型调用">¥{parseFloat(bill.model_call_amount).toFixed(2)}</Descriptions.Item>
          <Descriptions.Item label="知识库">¥{parseFloat(bill.knowledge_base_amount).toFixed(2)}</Descriptions.Item>
          <Descriptions.Item label="智能体">¥{parseFloat(bill.agent_amount).toFixed(2)}</Descriptions.Item>
          <Descriptions.Item label="Skill">¥{parseFloat(bill.skill_amount).toFixed(2)}</Descriptions.Item>
          <Descriptions.Item label="Token 用量">{bill.total_tokens?.toLocaleString()}</Descriptions.Item>
          <Descriptions.Item label="调用次数">{bill.total_calls?.toLocaleString()}</Descriptions.Item>
        </Descriptions>
      ),
    });
  };

  const handleRequestInvoice = (bill: any) => {
    invoiceForm.setFieldsValue({
      bill_ids: [bill.id],
      amount: bill.unpaid_amount,
    });
    setInvoiceModalVisible(true);
  };

  const handleViewInvoiceDetail = (invoice: any) => {
    Modal.info({
      title: '发票详情',
      width: 600,
      content: (
        <Descriptions column={2} bordered>
          <Descriptions.Item label="发票号码">{invoice.invoice_no}</Descriptions.Item>
          <Descriptions.Item label="发票代码">{invoice.invoice_code}</Descriptions.Item>
          <Descriptions.Item label="发票抬头">{invoice.title}</Descriptions.Item>
          <Descriptions.Item label="纳税人识别号">{invoice.tax_id}</Descriptions.Item>
          <Descriptions.Item label="发票类型">{invoice.invoice_type === 'electronic' ? '电子发票' : '纸质发票'}</Descriptions.Item>
          <Descriptions.Item label="发票金额">¥{parseFloat(invoice.amount).toFixed(2)}</Descriptions.Item>
          <Descriptions.Item label="状态"><Tag>{invoice.status}</Tag></Descriptions.Item>
          <Descriptions.Item label="收票人">{invoice.receiver_name}</Descriptions.Item>
          <Descriptions.Item label="收票邮箱">{invoice.receiver_email}</Descriptions.Item>
          <Descriptions.Item label="申请时间">{new Date(invoice.application_time).toLocaleString()}</Descriptions.Item>
          {invoice.issued_time && (
            <Descriptions.Item label="开具时间">{new Date(invoice.issued_time).toLocaleString()}</Descriptions.Item>
          )}
        </Descriptions>
      ),
    });
  };

  if (loading) {
    return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />;
  }

  return (
    <div>
      <Title level={2}>计费管理</Title>

      {/* 账户概览 */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={8}>
          <Card>
            <Statistic
              title="账户余额"
              value={accountInfo?.balance || 0}
              precision={2}
              prefix="¥"
              valueStyle={{ color: '#3f8600' }}
              prefix={<WalletOutlined />}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="累计充值"
              value={accountInfo?.total_recharge || 0}
              precision={2}
              prefix="¥"
              valueStyle={{ color: '#1890ff' }}
              prefix={<RechargeOutlined />}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card>
            <Statistic
              title="累计消费"
              value={accountInfo?.total_consumption || 0}
              precision={2}
              prefix="¥"
              valueStyle={{ color: '#cf1322' }}
              prefix={<DollarOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* 快捷操作 */}
      <Card style={{ marginBottom: 24 }} title="快捷操作">
        <div style={{ display: 'flex', gap: 16 }}>
          <Button type="primary" icon={<RechargeOutlined />} onClick={() => setRechargeModalVisible(true)}>
            账户充值
          </Button>
          <Button icon={<FileTextOutlined />} onClick={() => setInvoiceModalVisible(true)}>
            申请开票
          </Button>
          <Button icon={<BillOutlined />} onClick={loadMonthlyBills}>
            刷新账单
          </Button>
        </div>
      </Card>

      {/* 月度账单和计费记录 */}
      <Tabs
        items={[
          {
            key: 'bills',
            label: '月度账单',
            children: (
              <Table
                columns={billsColumns}
                dataSource={monthlyBills}
                rowKey="id"
                pagination={{ pageSize: 10 }}
              />
            ),
          },
          {
            key: 'records',
            label: '计费记录',
            children: (
              <Table
                columns={recordsColumns}
                dataSource={billingRecords}
                rowKey="id"
                pagination={{ pageSize: 10 }}
              />
            ),
          },
          {
            key: 'invoices',
            label: '发票管理',
            children: (
              <Table
                columns={invoicesColumns}
                dataSource={invoices}
                rowKey="id"
                pagination={{ pageSize: 10 }}
              />
            ),
          },
        ]}
      />

      {/* 充值模态框 */}
      <Modal
        title="账户充值"
        open={rechargeModalVisible}
        onCancel={() => setRechargeModalVisible(false)}
        footer={null}
      >
        <Form form={form} layout="vertical" onFinish={handleRecharge}>
          <Form.Item
            name="amount"
            label="充值金额"
            rules={[{ required: true, message: '请输入充值金额' }]}
          >
            <InputNumber
              style={{ width: '100%' }}
              min={1}
              max={999999}
              precision={2}
              prefix="¥"
              placeholder="请输入充值金额"
            />
          </Form.Item>
          <Form.Item
            name="channel_id"
            label="支付方式"
            rules={[{ required: true, message: '请选择支付方式' }]}
          >
            <Select placeholder="请选择支付方式">
              <Select.Option value="alipay">支付宝</Select.Option>
              <Select.Option value="wechat">微信支付</Select.Option>
              <Select.Option value="unionpay">银联支付</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" block>
              确认充值
            </Button>
          </Form.Item>
        </Form>
      </Modal>

      {/* 发票申请模态框 */}
      <Modal
        title="申请开票"
        open={invoiceModalVisible}
        onCancel={() => setInvoiceModalVisible(false)}
        footer={null}
      >
        <Form form={invoiceForm} layout="vertical" onFinish={handleInvoiceRequest}>
          <Form.Item name="bill_ids" hidden>
            <Input type="hidden" />
          </Form.Item>
          <Form.Item
            name="invoice_type"
            label="发票类型"
            rules={[{ required: true, message: '请选择发票类型' }]}
            initialValue="electronic"
          >
            <Radio.Group>
              <Radio value="electronic">电子发票</Radio>
              <Radio value="paper">纸质发票</Radio>
            </Radio.Group>
          </Form.Item>
          <Form.Item
            name="amount"
            label="开票金额"
            rules={[{ required: true, message: '请输入开票金额' }]}
          >
            <InputNumber
              style={{ width: '100%' }}
              min={0.01}
              precision={2}
              prefix="¥"
              placeholder="请输入开票金额"
            />
          </Form.Item>
          <Form.Item
            name="title"
            label="发票抬头"
            rules={[{ required: true, message: '请输入发票抬头' }]}
          >
            <Input placeholder="请输入发票抬头" />
          </Form.Item>
          <Form.Item
            name="tax_id"
            label="纳税人识别号"
            rules={[{ required: true, message: '请输入纳税人识别号' }]}
          >
            <Input placeholder="请输入纳税人识别号" />
          </Form.Item>
          <Form.Item
            name="receiver_email"
            label="收票邮箱"
            rules={[{ required: true, type: 'email', message: '请输入有效的邮箱地址' }]}
          >
            <Input placeholder="请输入收票邮箱" />
          </Form.Item>
          <Form.Item
            name="receiver_phone"
            label="收票电话"
          >
            <Input placeholder="请输入收票电话" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" block>
              提交申请
            </Button>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default BillingManagement;

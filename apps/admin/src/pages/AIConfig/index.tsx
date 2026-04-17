import { useState } from 'react';
import {
  Table,
  Button,
  Tag,
  Space,
  Modal,
  Form,
  Input,
  Select,
  InputNumber,
  Typography,
  Popconfirm,
  message,
  Alert,
} from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, EyeInvisibleOutlined, EyeOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';

const { Text, Title } = Typography;
const { Option } = Select;

interface AiModel {
  id: string;
  name: string;
  provider: string;
  model_id: string;
  api_key_masked: string;
  input_price: number;
  output_price: number;
  is_active: boolean;
}

interface SceneDefault {
  scene: string;
  scene_label: string;
  model_id: string;
}

const MOCK_MODELS: AiModel[] = [
  { id: 'm1', name: 'Gemini 2.5', provider: 'OpenRouter', model_id: 'google/gemini-2.5', api_key_masked: '****xxxx', input_price: 0.01, output_price: 0.03, is_active: true },
  { id: 'm2', name: 'DeepSeek V3', provider: 'OpenRouter', model_id: 'deepseek/deepseek-v3', api_key_masked: '****yyyy', input_price: 0.008, output_price: 0.024, is_active: true },
  { id: 'm3', name: 'GLM-5', provider: 'OpenRouter', model_id: 'zhipuai/glm-5', api_key_masked: '****zzzz', input_price: 0.012, output_price: 0.036, is_active: true },
];

const MOCK_SCENE_DEFAULTS: SceneDefault[] = [
  { scene: 'intelligence', scene_label: '情报摘要', model_id: 'm1' },
  { scene: 'email_generation', scene_label: '邮件生成', model_id: 'm2' },
  { scene: 'data_analysis', scene_label: '数据分析', model_id: 'm1' },
  { scene: 'scoring_llm', scene_label: '评分LLM辅助', model_id: 'm2' },
];

const BILLING_RULES = [
  { scene: '情报摘要', attribution: '均摊（所有租户共担）' },
  { scene: '邮件生成', attribution: '租户自负' },
  { scene: '评分LLM辅助', attribution: '租户自负' },
  { scene: '数据分析', attribution: '平台承担' },
];

export function Component() {
  const [models] = useState<AiModel[]>(MOCK_MODELS);
  const [sceneDefaults, setSceneDefaults] = useState<SceneDefault[]>(MOCK_SCENE_DEFAULTS);
  const [modelModalOpen, setModelModalOpen] = useState(false);
  const [editingModel, setEditingModel] = useState<AiModel | null>(null);
  const [showKey, setShowKey] = useState<Record<string, boolean>>({});
  const [form] = Form.useForm();

  const openEdit = (model?: AiModel) => {
    setEditingModel(model ?? null);
    form.setFieldsValue(model ?? {});
    setModelModalOpen(true);
  };

  const handleSaveModel = () => {
    form.validateFields().then(() => {
      message.success(editingModel ? '模型已更新' : '模型已添加');
      setModelModalOpen(false);
      form.resetFields();
    });
  };

  const updateSceneDefault = (scene: string, model_id: string) => {
    setSceneDefaults((prev) => prev.map((s) => s.scene === scene ? { ...s, model_id } : s));
    message.success('场景默认模型已更新');
  };

  const modelColumns: ColumnsType<AiModel> = [
    { title: '模型名称', dataIndex: 'name', render: (v) => <Text strong>{v}</Text> },
    { title: '路由方式', dataIndex: 'provider', render: (v) => <Tag color="purple">{v}</Tag> },
    { title: 'Model ID', dataIndex: 'model_id', render: (v) => <Text code style={{ fontSize: 12 }}>{v}</Text> },
    {
      title: 'API Key', dataIndex: 'api_key_masked', width: 140,
      render: (v, r) => (
        <Space size={4}>
          <Text style={{ fontFamily: 'monospace' }}>{showKey[r.id] ? 'sk-...' : v}</Text>
          <Button
            type="text"
            size="small"
            icon={showKey[r.id] ? <EyeInvisibleOutlined /> : <EyeOutlined />}
            onClick={() => setShowKey((prev) => ({ ...prev, [r.id]: !prev[r.id] }))}
          />
        </Space>
      ),
    },
    {
      title: '单价（元/千token）', width: 180,
      render: (_, r) => <Text style={{ fontSize: 12 }}>输入 ¥{r.input_price} / 输出 ¥{r.output_price}</Text>,
    },
    {
      title: '操作', width: 120,
      render: (_, record) => (
        <Space>
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => openEdit(record)}>编辑</Button>
          <Popconfirm title="确认删除该模型？" onConfirm={() => message.success('已删除')}>
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <Space direction="vertical" style={{ width: '100%' }} size={24}>
      {/* 模型管理 */}
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <Title level={5} style={{ margin: 0 }}>模型管理</Title>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => openEdit()}>添加模型</Button>
        </div>
        <Table rowKey="id" columns={modelColumns} dataSource={models} size="middle" pagination={false} />
      </div>

      {/* 场景配置：默认模型 + 费用归属合并 */}
      <div>
        <Title level={5} style={{ marginBottom: 12 }}>场景配置</Title>
        <Table
          rowKey="scene"
          dataSource={sceneDefaults}
          size="middle"
          pagination={false}
          columns={[
            {
              title: '场景',
              dataIndex: 'scene_label',
              width: 140,
            },
            {
              title: '默认模型',
              width: 220,
              render: (_, r) => (
                <Select
                  value={r.model_id}
                  style={{ width: 200 }}
                  onChange={(val) => updateSceneDefault(r.scene, val)}
                >
                  {models.map((m) => (
                    <Option key={m.id} value={m.id}>{m.name}</Option>
                  ))}
                </Select>
              ),
            },
            {
              title: '费用归属',
              render: (_, r) => {
                const billing = BILLING_RULES.find((b) => b.scene === r.scene_label);
                return <Text type="secondary" style={{ fontSize: 12 }}>{billing?.attribution ?? '—'}</Text>;
              },
            },
          ]}
        />
        <Alert
          type="info"
          showIcon
          message="修改单价后立即生效，将影响后续所有AI调用的扣费计算"
          style={{ marginTop: 12 }}
        />
      </div>

      {/* 添加/编辑模型弹窗 */}
      <Modal
        title={editingModel ? '编辑模型' : '添加模型'}
        open={modelModalOpen}
        onOk={handleSaveModel}
        onCancel={() => { setModelModalOpen(false); form.resetFields(); }}
        okText="保存"
        width={520}
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item name="name" label="模型显示名称" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="model_id" label="OpenRouter Model ID" rules={[{ required: true }]}>
            <Input placeholder="google/gemini-2.5" />
          </Form.Item>
          <Form.Item name="api_key" label="API Key" rules={[{ required: !editingModel }]}>
            <Input.Password placeholder={editingModel ? '留空则不修改' : '请输入 API Key'} />
          </Form.Item>
          <Form.Item label="计费单价（元/千token）" required>
            <Space>
              <Form.Item name="input_price" noStyle rules={[{ required: true }]}>
                <InputNumber prefix="输入 ¥" min={0} step={0.001} style={{ width: 150 }} />
              </Form.Item>
              <Form.Item name="output_price" noStyle rules={[{ required: true }]}>
                <InputNumber prefix="输出 ¥" min={0} step={0.001} style={{ width: 150 }} />
              </Form.Item>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </Space>
  );
}

Component.displayName = 'AIConfigPage';

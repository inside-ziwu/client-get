import { useEffect, useState } from 'react';
import {
  Button,
  Form,
  Input,
  Modal,
  Popconfirm,
  Select,
  Space,
  Switch,
  Table,
  Tag,
  Typography,
  message,
} from 'antd';
import { DeleteOutlined, EditOutlined, PlusOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { adminApi } from '../../lib/api';
import type {
  AiModel as ApiAiModel,
  AiSceneDefault as ApiAiSceneDefault,
  AiPricingResponse,
} from '@shared/api';

const { Text, Title } = Typography;

type ModelFormValues = {
  display_name: string;
  provider: string;
  model_id: string;
  is_active: boolean;
};

const EMPTY_MODEL: ModelFormValues = {
  display_name: '',
  provider: '',
  model_id: '',
  is_active: true,
};

const SCENE_LABELS: Record<string, string> = {
  scoring: '客户评分',
  email_generation: '邮件生成',
  intelligence_summary: '情报摘要',
  data_analysis: '数据分析',
  general: '通用',
};

export function Component() {
  const [models, setModels] = useState<ApiAiModel[]>([]);
  const [sceneDefaults, setSceneDefaults] = useState<ApiAiSceneDefault[]>([]);
  const [loading, setLoading] = useState(false);
  const [modelDrawerOpen, setModelDrawerOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editingModel, setEditingModel] = useState<ApiAiModel | null>(null);
  const [form] = Form.useForm<ModelFormValues>();

  const load = async () => {
    setLoading(true);
    try {
      const response = await adminApi.aiConfig.getPricing();
      const data = response.data.data as AiPricingResponse;
      setModels(data.models ?? []);
      setSceneDefaults(data.scene_defaults ?? []);
    } catch {
      message.error('加载 AI 配置失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const openCreate = () => {
    setEditingModel(null);
    form.setFieldsValue(EMPTY_MODEL);
    setModelDrawerOpen(true);
  };

  const openEdit = (record: ApiAiModel) => {
    setEditingModel(record);
    form.setFieldsValue({
      display_name: record.display_name,
      provider: record.provider,
      model_id: record.model_id,
      is_active: record.is_active,
    });
    setModelDrawerOpen(true);
  };

  const saveModel = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);
      const payload = {
        display_name: values.display_name.trim(),
        provider: values.provider.trim(),
        model_id: values.model_id.trim(),
        is_active: values.is_active,
      };

      if (editingModel) {
        await adminApi.aiConfig.updateModel(editingModel.id, payload);
        message.success('模型已更新');
      } else {
        await adminApi.aiConfig.createModel(payload);
        message.success('模型已创建');
      }

      setModelDrawerOpen(false);
      setEditingModel(null);
      form.resetFields();
      await load();
    } catch (error: unknown) {
      console.error('[AIConfig] saveModel error', error);
      const axiosDetail = (error as { response?: { data?: { detail?: unknown; message?: string } } })?.response?.data;
      const detail = axiosDetail?.message ?? (typeof axiosDetail?.detail === 'string' ? axiosDetail.detail : undefined) ?? (error as Error)?.message ?? '未知错误';
      message.error(`保存失败：${detail}`);
    } finally {
      setSaving(false);
    }
  };

  const deleteModel = async (id: string) => {
    try {
      await adminApi.aiConfig.deleteModel(id);
      message.success('模型已删除');
      await load();
    } catch {
      message.error('删除失败');
    }
  };

  const updateSceneDefault = async (scene: string, modelId: string) => {
    const next = sceneDefaults.map((item) => (
      item.scene === scene ? { ...item, model_id: modelId } : item
    ));

    setSceneDefaults(next);

    try {
      await adminApi.aiConfig.updateSceneDefaults(next);
      message.success('场景默认模型已更新');
    } catch (error) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const detail = (error as any)?.response?.data?.error?.message ?? (error as any)?.message ?? '未知错误';
      message.error(`场景默认模型更新失败：${detail}`);
      await load();
    }
  };

  const modelColumns: ColumnsType<ApiAiModel> = [
    { title: '名称', dataIndex: 'display_name', render: (value) => <Text strong>{value}</Text> },
    { title: 'Provider', dataIndex: 'provider', width: 140, render: (value) => <Tag color="purple">{value}</Tag> },
    { title: 'Model ID', dataIndex: 'model_id', render: (value) => <Text code>{value}</Text> },
    {
      title: '启用',
      dataIndex: 'is_active',
      width: 90,
      render: (value, record) => (
        <Switch
          checked={Boolean(value)}
          size="small"
          onChange={async (checked) => {
            try {
              await adminApi.aiConfig.updateModel(record.id, { is_active: checked });
              message.success('状态已更新');
              await load();
            } catch {
              message.error('状态更新失败');
            }
          }}
        />
      ),
    },
    {
      title: '操作',
      width: 160,
      render: (_, record) => (
        <Space>
          <Button type="link" icon={<EditOutlined />} onClick={() => openEdit(record)}>
            编辑
          </Button>
          <Popconfirm title="确认删除该模型？" onConfirm={() => void deleteModel(record.id)}>
            <Button type="link" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const sceneColumns: ColumnsType<ApiAiSceneDefault> = [
    {
      title: '场景',
      dataIndex: 'scene',
      width: 180,
      render: (value) => SCENE_LABELS[value as string] ?? value,
    },
    {
      title: '默认模型',
      render: (_, record) => (
        <Select
          value={record.model_id}
          style={{ width: 260 }}
          onChange={(value) => void updateSceneDefault(record.scene, value)}
        >
          {models.map((model) => (
            <Select.Option key={model.id} value={model.id}>
              {model.display_name}
            </Select.Option>
          ))}
        </Select>
      ),
    },
  ];

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <Title level={5} style={{ margin: 0 }}>
            AI 配置
          </Title>
          <Text type="secondary">模型、价格和场景默认值都直接写入后端。</Text>
        </div>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
          添加模型
        </Button>
      </div>

      <Table rowKey="id" columns={modelColumns} dataSource={models} loading={loading} pagination={false} />

      <div>
        <Title level={5} style={{ marginBottom: 12 }}>
          场景默认模型
        </Title>
        <Table rowKey={(record) => record.id ?? record.scene} columns={sceneColumns} dataSource={sceneDefaults} pagination={false} />
      </div>

      <Modal
        title={editingModel ? '编辑模型' : '添加模型'}
        open={modelDrawerOpen}
        onOk={() => void saveModel()}
        onCancel={() => {
          setModelDrawerOpen(false);
          setEditingModel(null);
          form.resetFields();
        }}
        okText="保存"
        confirmLoading={saving}
        width={620}
      >
        <Form form={form} layout="vertical" initialValues={EMPTY_MODEL}>
          <Form.Item name="display_name" label="显示名称" rules={[{ required: true, message: '请输入显示名称' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="provider" label="Provider" rules={[{ required: true, message: '请输入 Provider' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="model_id" label="Model ID" rules={[{ required: true, message: '请输入 Model ID' }]}>
            <Input placeholder="openrouter/google/gemini-2.5" />
          </Form.Item>
          <Form.Item name="is_active" label="启用" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </Space>
  );
}

Component.displayName = 'AIConfigPage';

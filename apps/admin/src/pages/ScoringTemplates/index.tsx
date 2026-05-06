import { useEffect, useState } from 'react';
import {
  Button,
  Card,
  Descriptions,
  Drawer,
  Form,
  Input,
  InputNumber,
  Modal,
  Popconfirm,
  Progress,
  Space,
  Switch,
  Table,
  Tag,
  Tooltip,
  Typography,
  message,
} from 'antd';
import { DeleteOutlined, EditOutlined, EyeOutlined, PlusOutlined, QuestionCircleOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { adminApi } from '../../lib/api';
import { formatDateTime } from '../../lib/format';
import type { ScoringTemplate as ApiScoringTemplate } from '@shared/api';

const { Text, Title } = Typography;

type GradeThresholds = { S: number; A: number; B: number; C: number; D: number };

type TemplateFormValues = {
  name: string;
  industry?: string;
  description?: string;
  dimensions_json: string;
  grade_S: number;
  grade_A: number;
  grade_B: number;
  grade_C: number;
  grade_D: number;
  is_active: boolean;
};

const DEFAULT_THRESHOLDS: GradeThresholds = { S: 90, A: 80, B: 60, C: 40, D: 0 };

const EMPTY_TEMPLATE: TemplateFormValues = {
  name: '',
  industry: '',
  description: '',
  dimensions_json: '[]',
  grade_S: DEFAULT_THRESHOLDS.S,
  grade_A: DEFAULT_THRESHOLDS.A,
  grade_B: DEFAULT_THRESHOLDS.B,
  grade_C: DEFAULT_THRESHOLDS.C,
  grade_D: DEFAULT_THRESHOLDS.D,
  is_active: true,
};

const EXAMPLE_DIMENSIONS = [
  {
    id: 'company_type',
    name: '工厂性质',
    type: 'rule',
    weight: 20,
    rules: [
      { condition: 'manufacturer', score: 100 },
      { condition: 'default', score: 50 },
    ],
  },
  {
    id: 'product_match',
    name: '产品匹配度',
    type: 'llm',
    weight: 30,
    prompt_template: '根据公司资料判断与租户行业的匹配度，返回 score 和 reasoning。',
    expected_json_schema: { score: 'number', reasoning: 'string' },
  },
];

function formatJson(value: unknown) {
  return JSON.stringify(value ?? [], null, 2);
}

function parseJson(text: string) {
  const trimmed = text.trim();
  if (!trimmed) return [];
  return JSON.parse(trimmed);
}

function thresholdsFromValues(values: TemplateFormValues): GradeThresholds {
  return {
    S: values.grade_S,
    A: values.grade_A,
    B: values.grade_B,
    C: values.grade_C,
    D: values.grade_D,
  };
}

export function Component() {
  const [items, setItems] = useState<ApiScoringTemplate[]>([]);
  const [loading, setLoading] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState<ApiScoringTemplate | null>(null);
  const [previewRecord, setPreviewRecord] = useState<ApiScoringTemplate | null>(null);
  const [form] = Form.useForm<TemplateFormValues>();

  const load = async () => {
    setLoading(true);
    try {
      const response = await adminApi.scoringTemplates.list();
      setItems(response.data.data);
    } catch (error) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const detail = (error as any)?.response?.data?.detail ?? (error as any)?.message ?? '未知错误';
      message.error(`加载评分模板失败：${detail}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const openCreate = () => {
    setEditing(null);
    form.setFieldsValue(EMPTY_TEMPLATE);
    setDrawerOpen(true);
  };

  const openEdit = async (record: ApiScoringTemplate) => {
    setEditing(record);
    try {
      const response = await adminApi.scoringTemplates.detail(record.id);
      const template = response.data.data;
      const gt = (template.grade_thresholds ?? DEFAULT_THRESHOLDS) as GradeThresholds;
      form.setFieldsValue({
        name: template.name,
        industry: template.industry ?? '',
        description: template.description ?? '',
        dimensions_json: formatJson(template.dimensions ?? []),
        grade_S: gt.S ?? DEFAULT_THRESHOLDS.S,
        grade_A: gt.A ?? DEFAULT_THRESHOLDS.A,
        grade_B: gt.B ?? DEFAULT_THRESHOLDS.B,
        grade_C: gt.C ?? DEFAULT_THRESHOLDS.C,
        grade_D: gt.D ?? DEFAULT_THRESHOLDS.D,
        is_active: template.is_active ?? true,
      });
      setDrawerOpen(true);
    } catch (error) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const detail = (error as any)?.response?.data?.detail ?? (error as any)?.message ?? '未知错误';
      message.error(`模板详情加载失败：${detail}`);
      setEditing(null);
    }
  };

  const openPreview = async (record: ApiScoringTemplate) => {
    try {
      const response = await adminApi.scoringTemplates.detail(record.id);
      setPreviewRecord(response.data.data);
    } catch {
      setPreviewRecord(record);
    }
  };

  const save = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);
      const payload = {
        name: values.name.trim(),
        industry: values.industry?.trim() || undefined,
        description: values.description?.trim() || undefined,
        dimensions: parseJson(values.dimensions_json),
        grade_thresholds: thresholdsFromValues(values),
        is_active: values.is_active,
      };

      if (editing) {
        await adminApi.scoringTemplates.update(editing.id, payload);
        message.success('评分模板已更新');
      } else {
        await adminApi.scoringTemplates.create(payload);
        message.success('评分模板已创建');
      }

      setDrawerOpen(false);
      setEditing(null);
      form.resetFields();
      await load();
    } catch (error) {
      if (error instanceof SyntaxError) {
        message.error('JSON 格式不正确');
        return;
      }

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const detail = (error as any)?.response?.data?.detail ?? (error as any)?.message ?? '未知错误';
      message.error(`保存失败：${detail}`);
    } finally {
      setSaving(false);
    }
  };

  const deleteTemplate = async (id: string) => {
    try {
      await adminApi.scoringTemplates.delete(id);
      setItems((prev) => prev.filter((item) => item.id !== id));
      message.success('评分模板已删除');
    } catch {
      message.error('删除失败');
    }
  };

  const columns: ColumnsType<ApiScoringTemplate> = [
    { title: '名称', dataIndex: 'name', render: (value) => <Text strong>{value}</Text> },
    { title: '行业', dataIndex: 'industry', width: 140, render: (value) => value ? <Tag color="blue">{value}</Tag> : '—' },
    { title: '维度数', width: 100, render: (_, record) => `${record.dimensions?.length ?? 0} 个` },
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
              await adminApi.scoringTemplates.update(record.id, { is_active: checked });
              message.success('状态已更新');
              await load();
            } catch {
              message.error('状态更新失败');
            }
          }}
        />
      ),
    },
    { title: '更新时间', dataIndex: 'updated_at', width: 180, render: (v) => formatDateTime(v as string) },
    {
      title: '操作',
      width: 200,
      render: (_, record) => (
        <Space>
          <Button type="link" icon={<EyeOutlined />} onClick={() => void openPreview(record)}>
            预览
          </Button>
          <Button type="link" icon={<EditOutlined />} onClick={() => void openEdit(record)}>
            编辑
          </Button>
          <Popconfirm title="确认删除该评分模板？" onConfirm={() => void deleteTemplate(record.id)}>
            <Button type="link" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <Title level={5} style={{ margin: 0 }}>
            评分模板
          </Title>
          <Text type="secondary">模板列表、启停都来自真实接口。</Text>
        </div>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
          新建模板
        </Button>
      </div>

      <Table rowKey="id" columns={columns} dataSource={items} loading={loading} pagination={false} />

      <Drawer
        title={editing ? `编辑评分模板 - ${editing.name}` : '新建评分模板'}
        width={720}
        open={drawerOpen}
        onClose={() => {
          setDrawerOpen(false);
          setEditing(null);
          form.resetFields();
        }}
        extra={<Button type="primary" loading={saving} onClick={() => void save()}>保存</Button>}
      >
        <Form form={form} layout="vertical" initialValues={EMPTY_TEMPLATE}>
          <Form.Item name="name" label="模板名称" rules={[{ required: true, message: '请输入模板名称' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="industry" label="行业">
            <Input placeholder="PCB" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} />
          </Form.Item>

          <Form.Item
            label={
              <Space size={4}>
                <span>等级阈值</span>
                <Tooltip title="分数 ≥ 阈值时判定为该等级，从高到低依次比较。D 通常为 0（兜底）。">
                  <QuestionCircleOutlined style={{ color: '#999' }} />
                </Tooltip>
              </Space>
            }
          >
            <Space wrap>
              {(['S', 'A', 'B', 'C', 'D'] as const).map((grade) => (
                <Form.Item key={grade} name={`grade_${grade}`} label={grade} style={{ marginBottom: 0 }}>
                  <InputNumber min={0} max={100} style={{ width: 80 }} />
                </Form.Item>
              ))}
            </Space>
          </Form.Item>

          <Form.Item
            name="dimensions_json"
            label={
              <Space size={4}>
                <span>评分维度 JSON</span>
                <Button
                  size="small"
                  type="link"
                  style={{ padding: 0 }}
                  onClick={() => form.setFieldValue('dimensions_json', formatJson(EXAMPLE_DIMENSIONS))}
                >
                  填入示例
                </Button>
              </Space>
            }
            rules={[{ required: true, message: '请输入维度 JSON' }]}
          >
            <Input.TextArea rows={10} placeholder='[{"id":"company_type","name":"工厂性质","type":"rule","weight":20,"rules":[...]}]' />
          </Form.Item>

          <Form.Item name="is_active" label="启用" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Drawer>

      {/* Preview Modal */}
      <Modal
        title={previewRecord ? `评分模板预览 — ${previewRecord.name}` : '评分模板预览'}
        open={previewRecord !== null}
        onCancel={() => setPreviewRecord(null)}
        footer={<Button onClick={() => setPreviewRecord(null)}>关闭</Button>}
        width={760}
      >
        {previewRecord && (
          <Space direction="vertical" style={{ width: '100%' }} size="large">
            {/* 基本信息 */}
            <Descriptions bordered size="small" column={2}>
              <Descriptions.Item label="行业">{previewRecord.industry ?? '通用'}</Descriptions.Item>
              <Descriptions.Item label="维度数">{previewRecord.dimensions?.length ?? 0} 个</Descriptions.Item>
              {previewRecord.description && (
                <Descriptions.Item label="描述" span={2}>{previewRecord.description}</Descriptions.Item>
              )}
            </Descriptions>

            {/* 等级阈值 */}
            {previewRecord.grade_thresholds && (
              <div>
                <Text strong style={{ display: 'block', marginBottom: 8 }}>等级阈值</Text>
                <Space size="large">
                  {(['S', 'A', 'B', 'C', 'D'] as const).map((grade) => {
                    const score = (previewRecord.grade_thresholds as Record<string, number>)[grade];
                    const colorMap: Record<string, string> = { S: 'gold', A: 'green', B: 'blue', C: 'orange', D: 'default' };
                    return score !== undefined ? (
                      <div key={grade} style={{ textAlign: 'center' }}>
                        <Tag color={colorMap[grade]} style={{ fontSize: 16, padding: '4px 12px', marginBottom: 4 }}>{grade}</Tag>
                        <div><Text type="secondary" style={{ fontSize: 12 }}>≥ {score} 分</Text></div>
                      </div>
                    ) : null;
                  })}
                </Space>
              </div>
            )}

            {/* 评分维度 */}
            <div>
              <Text strong style={{ display: 'block', marginBottom: 8 }}>评分维度</Text>
              <Space direction="vertical" style={{ width: '100%' }} size="small">
                {(previewRecord.dimensions ?? []).map((dim: Record<string, unknown>, idx: number) => (
                  <Card
                    key={idx}
                    size="small"
                    title={
                      <Space>
                        <Text strong>{dim.name as string ?? `维度 ${idx + 1}`}</Text>
                        <Tag color={dim.type === 'llm' ? 'purple' : 'cyan'}>{dim.type as string ?? '—'}</Tag>
                      </Space>
                    }
                    extra={
                      <Space>
                        <Text type="secondary">权重</Text>
                        <Progress
                          type="circle"
                          size={36}
                          percent={dim.weight as number ?? 0}
                          format={(p) => `${p}`}
                        />
                      </Space>
                    }
                  >
                    {dim.type === 'rule' && Array.isArray(dim.rules) && (
                      <Space direction="vertical" size={2} style={{ width: '100%' }}>
                        {(dim.rules as Array<Record<string, unknown>>).map((rule, ri) => (
                          <div key={ri} style={{ display: 'flex', justifyContent: 'space-between' }}>
                            <Text code>{rule.condition as string}</Text>
                            <Tag color="blue">{rule.score as number} 分</Tag>
                          </div>
                        ))}
                      </Space>
                    )}
                    {dim.type === 'llm' && (
                      <Space direction="vertical" size={4} style={{ width: '100%' }}>
                        {Boolean(dim.prompt_template) && (
                          <Text type="secondary" style={{ fontSize: 12 }}>
                            <b>Prompt：</b>{String(dim.prompt_template)}
                          </Text>
                        )}
                        {Boolean(dim.expected_json_schema) && (
                          <Text type="secondary" style={{ fontSize: 12 }}>
                            <b>返回结构：</b>{Object.keys(dim.expected_json_schema as object).join(', ')}
                          </Text>
                        )}
                      </Space>
                    )}
                  </Card>
                ))}
              </Space>
            </div>
          </Space>
        )}
      </Modal>
    </>
  );
}

Component.displayName = 'ScoringTemplatesPage';

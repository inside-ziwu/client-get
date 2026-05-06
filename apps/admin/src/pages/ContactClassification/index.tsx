import { useState } from 'react';
import {
  Button,
  Card,
  Col,
  Empty,
  Form,
  Input,
  InputNumber,
  List,
  Modal,
  Popconfirm,
  Row,
  Space,
  Switch,
  Tag,
  Typography,
  message,
} from 'antd';
import {
  DeleteOutlined,
  PlusOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type { ClassificationCategory, ClassificationLevel } from '@shared/api';
import { queryKeys } from '@shared/api';
import { adminApi } from '../../lib/api';

const { Title, Text } = Typography;

// ── 等级新建表单 ──────────────────────────────────────────────────────────────

function CreateLevelModal({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const [form] = Form.useForm();
  const queryClient = useQueryClient();

  const createMutation = useMutation({
    mutationFn: (values: { name: string; display_name: string; sort_order: number; is_sendable: boolean }) =>
      adminApi.contactClassification.createLevel(values),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.admin.contactClassification.levels() });
      message.success('等级已创建');
      form.resetFields();
      onClose();
    },
    onError: () => message.error('创建失败，请重试'),
  });

  return (
    <Modal
      title="新建等级"
      open={open}
      onCancel={onClose}
      onOk={() => form.submit()}
      confirmLoading={createMutation.isPending}
      destroyOnClose
    >
      <Form
        form={form}
        layout="vertical"
        initialValues={{ sort_order: 0, is_sendable: true }}
        onFinish={(values) => createMutation.mutate(values)}
      >
        <Form.Item name="name" label="名称（英文标识）" rules={[{ required: true }]}>
          <Input placeholder="如：C" />
        </Form.Item>
        <Form.Item name="display_name" label="显示名" rules={[{ required: true }]}>
          <Input placeholder="如：C级（其他）" />
        </Form.Item>
        <Form.Item name="sort_order" label="排序权重（数字越大越靠前）">
          <InputNumber style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="is_sendable" label="可发送" valuePropName="checked">
          <Switch />
        </Form.Item>
      </Form>
    </Modal>
  );
}

// ── 类别新建表单 ──────────────────────────────────────────────────────────────

function CreateCategoryModal({
  open,
  levelId,
  onClose,
}: {
  open: boolean;
  levelId: string;
  onClose: () => void;
}) {
  const [form] = Form.useForm();
  const queryClient = useQueryClient();

  const createMutation = useMutation({
    mutationFn: (values: { name: string; display_name: string; sort_order: number }) =>
      adminApi.contactClassification.createCategory({ ...values, level_id: levelId }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.admin.contactClassification.levels() });
      message.success('类别已创建');
      form.resetFields();
      onClose();
    },
    onError: () => message.error('创建失败，请重试'),
  });

  return (
    <Modal
      title="新建类别"
      open={open}
      onCancel={onClose}
      onOk={() => form.submit()}
      confirmLoading={createMutation.isPending}
      destroyOnClose
    >
      <Form
        form={form}
        layout="vertical"
        initialValues={{ sort_order: 0 }}
        onFinish={(values) => createMutation.mutate(values)}
      >
        <Form.Item name="name" label="名称（英文标识）" rules={[{ required: true }]}>
          <Input placeholder="如：manager" />
        </Form.Item>
        <Form.Item name="display_name" label="显示名" rules={[{ required: true }]}>
          <Input placeholder="如：管理层" />
        </Form.Item>
        <Form.Item name="sort_order" label="排序权重">
          <InputNumber style={{ width: '100%' }} />
        </Form.Item>
      </Form>
    </Modal>
  );
}

// ── 关键词批量添加表单 ────────────────────────────────────────────────────────

function AddKeywordsModal({
  open,
  categoryId,
  onClose,
}: {
  open: boolean;
  categoryId: string;
  onClose: () => void;
}) {
  const [form] = Form.useForm();
  const queryClient = useQueryClient();

  const addMutation = useMutation({
    mutationFn: (values: { keywords_text: string }) => {
      const keywords = values.keywords_text
        .split(/[\n,，、\s]+/)
        .map((kw) => kw.trim().toLowerCase())
        .filter(Boolean);
      return adminApi.contactClassification.addKeywords({ category_id: categoryId, keywords });
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.admin.contactClassification.levels() });
      message.success('关键词已添加');
      form.resetFields();
      onClose();
    },
    onError: () => message.error('添加失败，请重试'),
  });

  return (
    <Modal
      title="批量添加关键词"
      open={open}
      onCancel={onClose}
      onOk={() => form.submit()}
      confirmLoading={addMutation.isPending}
      destroyOnClose
    >
      <Form form={form} layout="vertical" onFinish={(values) => addMutation.mutate(values)}>
        <Form.Item
          name="keywords_text"
          label="关键词（每行一个，或用逗号/空格分隔，自动转小写）"
          rules={[{ required: true, message: '请输入至少一个关键词' }]}
        >
          <Input.TextArea
            rows={6}
            placeholder={'ceo\nowner\nfounder\n或：ceo, owner, founder'}
          />
        </Form.Item>
      </Form>
    </Modal>
  );
}

// ── 主页面 ────────────────────────────────────────────────────────────────────

export function Component() {
  const queryClient = useQueryClient();

  // 当前选中状态
  const [selectedLevel, setSelectedLevel] = useState<ClassificationLevel | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<ClassificationCategory | null>(null);

  // 弹窗状态
  const [createLevelOpen, setCreateLevelOpen] = useState(false);
  const [createCategoryOpen, setCreateCategoryOpen] = useState(false);
  const [addKeywordsOpen, setAddKeywordsOpen] = useState(false);

  const { data: levels = [], isLoading, refetch } = useQuery({
    queryKey: queryKeys.admin.contactClassification.levels(),
    queryFn: async () => (await adminApi.contactClassification.listLevels()).data.data,
  });

  // 每次 levels 刷新后同步选中状态
  const syncedLevel = levels.find((l) => l.id === selectedLevel?.id) ?? null;
  const syncedCategory = syncedLevel?.categories?.find((c) => c.id === selectedCategory?.id) ?? null;

  const invalidateLevels = () =>
    queryClient.invalidateQueries({ queryKey: queryKeys.admin.contactClassification.levels() });

  // 等级：更新 is_sendable
  const updateLevelMutation = useMutation({
    mutationFn: ({ id, is_sendable }: { id: string; is_sendable: boolean }) =>
      adminApi.contactClassification.updateLevel(id, { is_sendable }),
    onSuccess: invalidateLevels,
    onError: () => message.error('更新失败'),
  });

  // 等级：删除
  const deleteLevelMutation = useMutation({
    mutationFn: (id: string) => adminApi.contactClassification.deleteLevel(id),
    onSuccess: async () => {
      await invalidateLevels();
      if (selectedLevel?.id === deleteLevelMutation.variables) {
        setSelectedLevel(null);
        setSelectedCategory(null);
      }
      message.success('等级已删除');
    },
    onError: () => message.error('删除失败'),
  });

  // 类别：删除
  const deleteCategoryMutation = useMutation({
    mutationFn: (id: string) => adminApi.contactClassification.deleteCategory(id),
    onSuccess: async () => {
      await invalidateLevels();
      if (selectedCategory?.id === deleteCategoryMutation.variables) {
        setSelectedCategory(null);
      }
      message.success('类别已删除');
    },
    onError: () => message.error('删除失败'),
  });

  // 关键词：删除
  const deleteKeywordMutation = useMutation({
    mutationFn: (id: string) => adminApi.contactClassification.deleteKeyword(id),
    onSuccess: async () => {
      await invalidateLevels();
      message.success('关键词已删除');
    },
    onError: () => message.error('删除失败'),
  });

  const colStyle = { height: 'calc(100vh - 120px)', overflow: 'auto' };

  return (
    <>
      <Space style={{ marginBottom: 16 }} align="center">
        <Title level={4} style={{ margin: 0 }}>联系人职位分类管理</Title>
        <Button icon={<ReloadOutlined />} size="small" onClick={() => refetch()}>刷新</Button>
      </Space>

      <Row gutter={16} style={{ flexWrap: 'nowrap' }}>
        {/* 左列：等级列表 */}
        <Col flex="240px">
          <Card
            size="small"
            title="等级"
            style={colStyle}
            extra={
              <Button
                size="small"
                icon={<PlusOutlined />}
                onClick={() => setCreateLevelOpen(true)}
              >
                新建
              </Button>
            }
          >
            {levels.length === 0 && !isLoading && <Empty description="暂无等级" />}
            <List
              loading={isLoading}
              dataSource={levels}
              rowKey="id"
              renderItem={(level) => (
                <List.Item
                  style={{
                    cursor: 'pointer',
                    background: syncedLevel?.id === level.id ? '#e6f7ff' : undefined,
                    padding: '8px 12px',
                    borderRadius: 4,
                    marginBottom: 4,
                  }}
                  onClick={() => {
                    setSelectedLevel(level);
                    setSelectedCategory(null);
                  }}
                >
                  <Space style={{ width: '100%', justifyContent: 'space-between' }} align="start">
                    <Space direction="vertical" size={2}>
                      <Text strong>{level.display_name}</Text>
                      <Space size={4}>
                        <Tag color={level.is_sendable ? 'green' : 'red'} style={{ fontSize: 11 }}>
                          {level.is_sendable ? '可发送' : '不发送'}
                        </Tag>
                        <Text type="secondary" style={{ fontSize: 11 }}>排序 {level.sort_order}</Text>
                      </Space>
                    </Space>
                    <Space size={4} onClick={(e) => e.stopPropagation()}>
                      <Switch
                        size="small"
                        checked={level.is_sendable}
                        loading={
                          updateLevelMutation.isPending &&
                          (updateLevelMutation.variables as { id: string })?.id === level.id
                        }
                        onChange={(checked) =>
                          updateLevelMutation.mutate({ id: level.id, is_sendable: checked })
                        }
                      />
                      <Popconfirm
                        title={`删除「${level.display_name}」？将同时删除其所有类别和关键词。`}
                        onConfirm={() => deleteLevelMutation.mutate(level.id)}
                        okText="确认"
                        cancelText="取消"
                      >
                        <Button
                          size="small"
                          danger
                          icon={<DeleteOutlined />}
                          loading={deleteLevelMutation.isPending && deleteLevelMutation.variables === level.id}
                        />
                      </Popconfirm>
                    </Space>
                  </Space>
                </List.Item>
              )}
            />
          </Card>
        </Col>

        {/* 中列：类别列表 */}
        <Col flex="240px">
          <Card
            size="small"
            title={syncedLevel ? `「${syncedLevel.display_name}」类别` : '类别'}
            style={colStyle}
            extra={
              syncedLevel && (
                <Button
                  size="small"
                  icon={<PlusOutlined />}
                  onClick={() => setCreateCategoryOpen(true)}
                >
                  新建
                </Button>
              )
            }
          >
            {!syncedLevel ? (
              <Empty description="请先选择等级" />
            ) : (syncedLevel.categories?.length ?? 0) === 0 ? (
              <Empty description="暂无类别" />
            ) : (
              <List
                dataSource={syncedLevel.categories ?? []}
                rowKey="id"
                renderItem={(cat) => (
                  <List.Item
                    style={{
                      cursor: 'pointer',
                      background: syncedCategory?.id === cat.id ? '#e6f7ff' : undefined,
                      padding: '8px 12px',
                      borderRadius: 4,
                      marginBottom: 4,
                    }}
                    onClick={() => setSelectedCategory(cat)}
                  >
                    <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                      <Space direction="vertical" size={2}>
                        <Text strong>{cat.display_name}</Text>
                        <Text type="secondary" style={{ fontSize: 11 }}>
                          {cat.keywords?.length ?? 0} 个关键词
                        </Text>
                      </Space>
                      <Popconfirm
                        title={`删除「${cat.display_name}」？将同时删除其关键词。`}
                        onConfirm={() => deleteCategoryMutation.mutate(cat.id)}
                        okText="确认"
                        cancelText="取消"
                      >
                        <Button
                          size="small"
                          danger
                          icon={<DeleteOutlined />}
                          onClick={(e) => e.stopPropagation()}
                          loading={deleteCategoryMutation.isPending && deleteCategoryMutation.variables === cat.id}
                        />
                      </Popconfirm>
                    </Space>
                  </List.Item>
                )}
              />
            )}
          </Card>
        </Col>

        {/* 右列：关键词列表 */}
        <Col flex="1">
          <Card
            size="small"
            title={syncedCategory ? `「${syncedCategory.display_name}」关键词` : '关键词'}
            style={colStyle}
            extra={
              syncedCategory && (
                <Button
                  size="small"
                  icon={<PlusOutlined />}
                  onClick={() => setAddKeywordsOpen(true)}
                >
                  批量添加
                </Button>
              )
            }
          >
            {!syncedCategory ? (
              <Empty description="请先选择类别" />
            ) : (syncedCategory.keyword_ids?.length ?? 0) === 0 ? (
              <Empty description="暂无关键词" />
            ) : (
              <Space size={8} wrap>
                {(syncedCategory.keyword_ids ?? []).map((item) => (
                  <Tag
                    key={item.id}
                    closable
                    onClose={(e) => {
                      e.preventDefault();
                      deleteKeywordMutation.mutate(item.id);
                    }}
                    color="blue"
                    style={{ fontSize: 13 }}
                  >
                    {item.keyword}
                  </Tag>
                ))}
              </Space>
            )}
          </Card>
        </Col>
      </Row>

      {/* 弹窗 */}
      <CreateLevelModal open={createLevelOpen} onClose={() => setCreateLevelOpen(false)} />

      {syncedLevel && (
        <CreateCategoryModal
          open={createCategoryOpen}
          levelId={syncedLevel.id}
          onClose={() => setCreateCategoryOpen(false)}
        />
      )}

      {syncedCategory && (
        <AddKeywordsModal
          open={addKeywordsOpen}
          categoryId={syncedCategory.id}
          onClose={() => setAddKeywordsOpen(false)}
        />
      )}
    </>
  );
}

Component.displayName = 'ContactClassificationPage';

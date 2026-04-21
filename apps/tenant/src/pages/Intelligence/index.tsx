import { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Empty,
  Form,
  Input,
  InputNumber,
  Select,
  Space,
  Switch,
  Tag,
  Typography,
  message,
} from 'antd';
import { LinkOutlined, StarOutlined } from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type { BillingBalance } from '@shared/types';
import { queryKeys, type IntelligenceArticle, type IntelligenceSubscription } from '@shared/api';
import { tenantApi } from '../../lib/api';

const { Text, Title, Paragraph } = Typography;

type SubscriptionValues = {
  industry_tags: string;
  min_relevance: number;
  notify_enabled: boolean;
};

function readText(record: object, keys: string[]) {
  const source = record as Record<string, unknown>;
  for (const key of keys) {
    const value = source[key];
    if (typeof value === 'string' && value.trim()) {
      return value;
    }
  }
  return '—';
}

export function Component() {
  const queryClient = useQueryClient();
  const [activeCategory, setActiveCategory] = useState<string>('all');
  const [keyword, setKeyword] = useState('');
  const [form] = Form.useForm<SubscriptionValues>();

  const articlesQuery = useQuery<IntelligenceArticle[]>({
    queryKey: queryKeys.intelligence.list({ limit: 100 }),
    queryFn: async () => (await tenantApi.intelligence.list({ limit: 100 })).data.data,
  });

  const subscriptionsQuery = useQuery<IntelligenceSubscription[]>({
    queryKey: queryKeys.intelligence.subscriptions(),
    queryFn: async () => (await tenantApi.intelligence.getSubscriptions()).data.data,
  });

  const balanceQuery = useQuery({
    queryKey: ['tenant', 'billing', 'balance', 'intelligence'],
    queryFn: async () => (await tenantApi.billing.balance()).data.data as BillingBalance,
  });

  const markMutation = useMutation({
    mutationFn: async ({ id, action }: { id: string; action: 'read' | 'star' | 'archive' }) => {
      if (action === 'read') return tenantApi.intelligence.markRead(id);
      if (action === 'star') return tenantApi.intelligence.star(id);
      return tenantApi.intelligence.archive(id);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.intelligence.all() });
    },
    onError: () => message.error('文章状态更新失败'),
  });

  const subscriptionMutation = useMutation({
    mutationFn: (values: SubscriptionValues) =>
      tenantApi.intelligence.putSubscriptions({
        industry_tags: values.industry_tags.split(',').map((item) => item.trim()).filter(Boolean),
        min_relevance: values.min_relevance,
        notify_enabled: values.notify_enabled,
      }),
    onSuccess: async () => {
      message.success('订阅设置已保存');
      await queryClient.invalidateQueries({ queryKey: queryKeys.intelligence.subscriptions() });
    },
    onError: () => message.error('订阅设置保存失败'),
  });

  const articles = articlesQuery.data ?? [];
  const categories = Array.from(new Set(articles.map((item) => readText(item, ['ai_category'])))).filter((item) => item !== '—');
  const filteredArticles = useMemo(() => {
    return articles.filter((item) => {
      const category = readText(item, ['ai_category']);
      const text = `${readText(item, ['title'])} ${readText(item, ['content_summary'])}`.toLowerCase();
      if (activeCategory !== 'all' && category !== activeCategory) {
        return false;
      }
      if (keyword && !text.includes(keyword.toLowerCase())) {
        return false;
      }
      return true;
    });
  }, [articles, activeCategory, keyword]);

  const subscription = subscriptionsQuery.data?.[0] ?? null;
  const balance = balanceQuery.data?.balance ?? balanceQuery.data?.amount ?? 0;

  useEffect(() => {
    form.setFieldsValue({
      industry_tags: subscription?.industry_tags?.join(', ') ?? '',
      min_relevance: subscription?.min_relevance ?? 0.5,
      notify_enabled: subscription?.notify_enabled ?? true,
    });
  }, [form, subscription]);

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      <Space style={{ justifyContent: 'space-between', width: '100%' }}>
        <div>
          <Title level={5} style={{ margin: 0 }}>情报中心</Title>
          <Paragraph type="secondary" style={{ marginBottom: 0 }}>
            文章、阅读状态和订阅规则全部来自真实后端。
          </Paragraph>
        </div>
        <Text type="secondary">AI 余额：{balance}</Text>
      </Space>

      {articlesQuery.isError && <Alert type="error" showIcon message="情报数据加载失败" />}

      <Card size="small">
        <Space wrap>
          <Select
            value={activeCategory}
            onChange={setActiveCategory}
            style={{ width: 200 }}
            options={[{ label: '全部分类', value: 'all' }, ...categories.map((item) => ({ label: item, value: item }))]}
          />
          <Input value={keyword} onChange={(event) => setKeyword(event.target.value)} placeholder="搜索标题或摘要" style={{ width: 260 }} />
        </Space>
      </Card>

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 16, alignItems: 'start' }}>
        <Card size="small" title={`文章列表 (${filteredArticles.length})`}>
          {filteredArticles.length === 0 ? (
            <Empty description="暂无符合条件的情报文章" />
          ) : (
            <Space direction="vertical" style={{ width: '100%' }} size="large">
              {filteredArticles.map((article) => {
                const articleId = article.article_id;
                const tags = article.ai_tags ?? [];
                const publicationStatus = readText(article as unknown as Record<string, unknown>, ['publication_status', 'status']);
                return (
                  <div key={`${articleId}-${article.publication_id}`} style={{ borderBottom: '1px solid #f0f0f0', paddingBottom: 16 }}>
                    <Space wrap style={{ marginBottom: 8 }}>
                      <Tag color="blue">{article.ai_category ?? '—'}</Tag>
                      <Tag>{publicationStatus}</Tag>
                      <Text type="secondary">{article.published_at ?? article.article_created_at}</Text>
                    </Space>
                    <div>
                      <Text strong style={{ fontSize: 15 }}>{article.title}</Text>
                    </div>
                    <Paragraph type="secondary" style={{ marginTop: 8, marginBottom: 8 }}>
                      {article.content_summary ?? '—'}
                    </Paragraph>
                    <Space wrap style={{ marginBottom: 8 }}>
                      {tags.map((tag) => <Tag key={tag}>{tag}</Tag>)}
                    </Space>
                    <Space wrap>
                      <Button size="small" onClick={() => markMutation.mutate({ id: articleId, action: 'read' })}>
                        标记已读
                      </Button>
                      <Button size="small" icon={<StarOutlined />} onClick={() => markMutation.mutate({ id: articleId, action: 'star' })}>
                        收藏
                      </Button>
                      <Button size="small" danger onClick={() => markMutation.mutate({ id: articleId, action: 'archive' })}>
                        归档
                      </Button>
                      {article.url && (
                        <Button size="small" icon={<LinkOutlined />} href={article.url} target="_blank">
                          原文
                        </Button>
                      )}
                    </Space>
                  </div>
                );
              })}
            </Space>
          )}
        </Card>

        <Card size="small" title="订阅设置">
          <Form
            form={form}
            layout="vertical"
          >
            <Form.Item name="industry_tags" label="行业标签">
              <Input.TextArea rows={4} placeholder="pcb, electronics, germany" />
            </Form.Item>
            <Form.Item name="min_relevance" label="最低相关度">
              <InputNumber min={0} max={1} step={0.1} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="notify_enabled" label="开启通知" valuePropName="checked">
              <Switch />
            </Form.Item>
            <Button
              type="primary"
              loading={subscriptionMutation.isPending}
              onClick={async () => subscriptionMutation.mutate(await form.validateFields())}
            >
              保存订阅
            </Button>
          </Form>
        </Card>
      </div>
    </Space>
  );
}

Component.displayName = 'IntelligencePage';

import { useState } from 'react';
import {
  Button,
  Descriptions,
  Drawer,
  Form,
  Input,
  Space,
  Table,
  Tabs,
  Tag,
  Typography,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { useQuery } from '@tanstack/react-query';
import { adminApi } from '../../lib/api';

const { Text } = Typography;
const PAGE_SIZE = 20;

type RawTable = 'waimaotong' | 'tendata' | 'lixiaoyun';
type ArchiveTabKey = RawTable | 'clean';

interface RawCompanyRow {
  id: string;
  source_id?: string;
  tid?: string;
  name: string;
  country?: string;
  domain?: string | null;
  task_id?: string | null;
  created_at: string;
  raw_payload: Record<string, unknown>;
}

interface CleanCompanyRow {
  id: string;
  name_normalized: string;
  name_display: string;
  country_iso3: string | null;
  domain: string | null;
  sources: string[];
  created_at: string;
}

interface PageData<T> {
  data: T[];
  pagination: {
    cursor: string | null;
    has_more: boolean;
    total?: number;
  };
}

type FilterValues = {
  keyword?: string;
  country?: string;
};

function emptyPage<T>(): PageData<T> {
  return {
    data: [],
    pagination: {
      cursor: null,
      has_more: false,
      total: 0,
    },
  };
}

function isNotFound(error: unknown) {
  return (error as { response?: { status?: number } }).response?.status === 404;
}

function formatDateTime(value: string | null | undefined) {
  return value ? new Date(value).toLocaleString('zh-CN', { hour12: false }) : '—';
}

function cleanFilters(values: FilterValues) {
  return {
    keyword: values.keyword?.trim() || undefined,
    country: values.country?.trim() || undefined,
  };
}

function RawArchiveTab({ activeTab, table }: { activeTab: ArchiveTabKey; table: RawTable }) {
  const [form] = Form.useForm<FilterValues>();
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState<FilterValues>({});
  const [selected, setSelected] = useState<RawCompanyRow | null>(null);

  const query = useQuery({
    queryKey: ['admin', 'archive', table, page, filters.keyword, filters.country],
    queryFn: async () => {
      try {
        return (await adminApi.collection.listRawCompanies(table, {
          page,
          page_size: PAGE_SIZE,
          keyword: filters.keyword,
          country: filters.country,
        })).data as PageData<RawCompanyRow>;
      } catch (error) {
        if (isNotFound(error)) {
          return emptyPage<RawCompanyRow>();
        }
        throw error;
      }
    },
    enabled: activeTab === table,
  });

  const pageData = query.data ?? emptyPage<RawCompanyRow>();
  const columns: ColumnsType<RawCompanyRow> = [
    { title: '名称', dataIndex: 'name', ellipsis: true, render: (value: string) => <Text strong>{value}</Text> },
    { title: '国家', dataIndex: 'country', width: 120, render: (value?: string) => value || '—' },
    { title: '域名', dataIndex: 'domain', width: 180, render: (value: string | null | undefined) => value || '—' },
    {
      title: '来源 ID',
      key: 'source_id',
      width: 180,
      render: (_, record) => record.source_id ?? record.tid ?? '—',
    },
    { title: '创建时间', dataIndex: 'created_at', width: 180, render: (value: string) => formatDateTime(value) },
    {
      title: '操作',
      key: 'action',
      width: 90,
      render: (_, record) => (
        <Button
          type="link"
          onClick={(event) => {
            event.stopPropagation();
            setSelected(record);
          }}
        >
          详情
        </Button>
      ),
    },
  ];

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Form
        form={form}
        layout="inline"
        onFinish={(values) => {
          setFilters(cleanFilters(values));
          setPage(1);
        }}
      >
        <Form.Item name="keyword" label="关键词">
          <Input.Search allowClear enterButton="搜索" placeholder="公司名或关键词" onSearch={() => form.submit()} />
        </Form.Item>
        <Form.Item name="country" label="国家">
          <Input allowClear placeholder="US / China" />
        </Form.Item>
      </Form>

      <Table<RawCompanyRow>
        columns={columns}
        dataSource={pageData.data}
        loading={query.isFetching}
        rowKey="id"
        onRow={(record) => ({ onClick: () => setSelected(record) })}
        pagination={{
          current: page,
          pageSize: PAGE_SIZE,
          total: pageData.pagination.total,
          onChange: setPage,
          showSizeChanger: false,
        }}
      />

      <Drawer
        title={selected ? `${selected.name} 原始详情` : '原始详情'}
        open={Boolean(selected)}
        onClose={() => setSelected(null)}
        width={720}
      >
        {selected && (
          <pre style={{ whiteSpace: 'pre-wrap', margin: 0 }}>
            {JSON.stringify(selected.raw_payload, null, 2)}
          </pre>
        )}
      </Drawer>
    </Space>
  );
}

function CleanArchiveTab({ activeTab }: { activeTab: ArchiveTabKey }) {
  const [form] = Form.useForm<FilterValues>();
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState<FilterValues>({});
  const [selected, setSelected] = useState<CleanCompanyRow | null>(null);

  const query = useQuery({
    queryKey: ['admin', 'archive', 'clean', page, filters.keyword],
    queryFn: async () => {
      try {
        return (await adminApi.collection.listCleanCompanies({
          page,
          page_size: PAGE_SIZE,
          keyword: filters.keyword,
        })).data as PageData<CleanCompanyRow>;
      } catch (error) {
        if (isNotFound(error)) {
          return emptyPage<CleanCompanyRow>();
        }
        throw error;
      }
    },
    enabled: activeTab === 'clean',
  });

  const pageData = query.data ?? emptyPage<CleanCompanyRow>();
  const columns: ColumnsType<CleanCompanyRow> = [
    { title: '名称', dataIndex: 'name_display', ellipsis: true, render: (value: string) => <Text strong>{value}</Text> },
    { title: '域名', dataIndex: 'domain', width: 180, render: (value: string | null) => value || '—' },
    {
      title: '来源',
      dataIndex: 'sources',
      width: 220,
      render: (sources: string[]) => (
        <Space size={4} wrap>
          {sources.map((source) => <Tag key={source}>{source}</Tag>)}
        </Space>
      ),
    },
    { title: '创建时间', dataIndex: 'created_at', width: 180, render: (value: string) => formatDateTime(value) },
    {
      title: '操作',
      key: 'action',
      width: 90,
      render: (_, record) => (
        <Button
          type="link"
          onClick={(event) => {
            event.stopPropagation();
            setSelected(record);
          }}
        >
          详情
        </Button>
      ),
    },
  ];

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Form
        form={form}
        layout="inline"
        onFinish={(values) => {
          setFilters({ keyword: values.keyword?.trim() || undefined });
          setPage(1);
        }}
      >
        <Form.Item name="keyword" label="关键词">
          <Input.Search allowClear enterButton="搜索" placeholder="公司名或关键词" onSearch={() => form.submit()} />
        </Form.Item>
      </Form>

      <Table<CleanCompanyRow>
        columns={columns}
        dataSource={pageData.data}
        loading={query.isFetching}
        rowKey="id"
        onRow={(record) => ({ onClick: () => setSelected(record) })}
        pagination={{
          current: page,
          pageSize: PAGE_SIZE,
          total: pageData.pagination.total,
          onChange: setPage,
          showSizeChanger: false,
        }}
      />

      <Drawer
        title={selected ? `${selected.name_display} 清洗详情` : '清洗详情'}
        open={Boolean(selected)}
        onClose={() => setSelected(null)}
        width={720}
      >
        {selected && (
          <Descriptions bordered column={1} size="small">
            <Descriptions.Item label="展示名称">{selected.name_display}</Descriptions.Item>
            <Descriptions.Item label="标准名称">{selected.name_normalized}</Descriptions.Item>
            <Descriptions.Item label="国家">{selected.country_iso3 ?? '—'}</Descriptions.Item>
            <Descriptions.Item label="域名">{selected.domain ?? '—'}</Descriptions.Item>
            <Descriptions.Item label="来源">
              <Space size={4} wrap>
                {selected.sources.map((source) => <Tag key={source}>{source}</Tag>)}
              </Space>
            </Descriptions.Item>
            <Descriptions.Item label="创建时间">{formatDateTime(selected.created_at)}</Descriptions.Item>
          </Descriptions>
        )}
      </Drawer>
    </Space>
  );
}

export function Component() {
  const [activeTab, setActiveTab] = useState<ArchiveTabKey>('waimaotong');

  return (
    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
      <Typography.Title level={4} style={{ margin: 0 }}>数据归档</Typography.Title>
      <Tabs
        activeKey={activeTab}
        onChange={(key) => setActiveTab(key as ArchiveTabKey)}
        items={[
          { key: 'waimaotong', label: '外贸通原始', children: <RawArchiveTab activeTab={activeTab} table="waimaotong" /> },
          { key: 'tendata', label: '腾道原始', children: <RawArchiveTab activeTab={activeTab} table="tendata" /> },
          { key: 'lixiaoyun', label: '励销云原始', children: <RawArchiveTab activeTab={activeTab} table="lixiaoyun" /> },
          { key: 'clean', label: '清洗公司', children: <CleanArchiveTab activeTab={activeTab} /> },
        ]}
      />
    </Space>
  );
}

Component.displayName = 'CollectionArchivePage';

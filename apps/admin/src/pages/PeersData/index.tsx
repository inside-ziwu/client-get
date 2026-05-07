import { useState } from 'react';
import {
  Button,
  Checkbox,
  DatePicker,
  Descriptions,
  Drawer,
  Form,
  Input,
  Select,
  Table,
  Tag,
  Typography,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { useQuery } from '@tanstack/react-query';
import { adminApi } from '../../lib/api';

const { Text, Title } = Typography;
const { RangePicker } = DatePicker;
const PAGE_SIZE = 20;

interface LixiaoyunRow {
  id: string;
  name: string;
  domain?: string | null;
  task_id?: string | null;
  created_at: string;
  raw_payload: Record<string, unknown>;
}

interface PageData {
  data: LixiaoyunRow[];
  pagination: { cursor: string | null; has_more: boolean; total?: number };
}

type FilterValues = {
  name?: string;
  keyword_filter?: string;
  found_date?: [unknown, unknown];
  reg_capital?: string;
  employee_scale?: string;
  contacts_count?: string;
  has_name_en?: boolean;
  has_domain?: boolean;
};

function pick(payload: Record<string, unknown>, ...keys: string[]): string {
  for (const k of keys) {
    const v = payload[k];
    if (v != null && v !== '') return String(v);
  }
  return '—';
}

function formatDateTime(value: string | null | undefined) {
  return value ? new Date(value).toLocaleString('zh-CN', { hour12: false }) : '—';
}

function emptyPage(): PageData {
  return { data: [], pagination: { cursor: null, has_more: false, total: 0 } };
}

export function Component() {
  const [form] = Form.useForm<FilterValues>();
  const [page, setPage] = useState(1);
  const [nameFilter, setNameFilter] = useState<string | undefined>();
  const [selected, setSelected] = useState<LixiaoyunRow | null>(null);

  const query = useQuery({
    queryKey: ['admin', 'peers', page, nameFilter],
    queryFn: async () => {
      try {
        return (
          await adminApi.collection.listRawCompanies('lixiaoyun', {
            page,
            page_size: PAGE_SIZE,
            keyword: nameFilter,
          })
        ).data as PageData;
      } catch {
        return emptyPage();
      }
    },
  });

  const pageData = query.data ?? emptyPage();

  const onSearch = (values: FilterValues) => {
    setNameFilter(values.name?.trim() || undefined);
    setPage(1);
  };

  const onReset = () => {
    form.resetFields();
    setNameFilter(undefined);
    setPage(1);
  };

  const columns: ColumnsType<LixiaoyunRow> = [
    {
      title: '中文名',
      key: 'name_cn',
      ellipsis: true,
      width: 200,
      render: (_, row) => {
        const cn = pick(row.raw_payload, 'name_cn', 'name_zh') || row.name;
        return <Text strong style={{ fontSize: 12 }}>{cn}</Text>;
      },
    },
    {
      title: '英文名',
      key: 'name_en',
      ellipsis: true,
      width: 160,
      render: (_, row) => (
        <Text type="secondary" style={{ fontSize: 12 }}>
          {pick(row.raw_payload, 'name_en', 'name_english')}
        </Text>
      ),
    },
    {
      title: '员工规模',
      key: 'employee_scale',
      width: 110,
      render: (_, row) => pick(row.raw_payload, 'employee_scale', 'staff_num'),
    },
    {
      title: '注册资金',
      key: 'reg_capital',
      width: 100,
      render: (_, row) => pick(row.raw_payload, 'reg_capital', 'registered_capital'),
    },
    {
      title: '成立时间',
      key: 'established',
      width: 110,
      render: (_, row) => pick(row.raw_payload, 'established_date', 'found_date', 'reg_date'),
    },
    {
      title: '注册地址',
      key: 'address',
      ellipsis: true,
      width: 160,
      render: (_, row) => (
        <Text type="secondary" style={{ fontSize: 12 }}>
          {pick(row.raw_payload, 'address', 'reg_address', 'location')}
        </Text>
      ),
    },
    {
      title: '网址',
      key: 'domain',
      width: 130,
      render: (_, row) => {
        const d = row.domain ?? pick(row.raw_payload, 'website', 'domain');
        return d && d !== '—'
          ? <Text style={{ fontSize: 12, color: '#1677ff' }}>{d}</Text>
          : <Text type="secondary">—</Text>;
      },
    },
    {
      title: '联系人',
      key: 'contacts',
      width: 72,
      align: 'center' as const,
      render: (_, row) => {
        const cnt = Number(pick(row.raw_payload, 'contacts_count', 'contact_num') || 0);
        const n = isNaN(cnt) ? 0 : cnt;
        return <Tag color={n > 0 ? 'green' : 'default'}>{n}</Tag>;
      },
    },
    {
      title: '关键词',
      key: 'keyword',
      width: 140,
      render: (_, row) => {
        const kw = pick(row.raw_payload, 'keyword', 'search_keyword', 'query');
        return kw && kw !== '—'
          ? <Tag color="blue" style={{ fontSize: 11 }}>{kw}</Tag>
          : <Text type="secondary">—</Text>;
      },
    },
    {
      title: '采集时间',
      key: 'created_at',
      width: 150,
      render: (_, row) => (
        <Text type="secondary" style={{ fontSize: 11, whiteSpace: 'nowrap' }}>
          {formatDateTime(row.created_at)}
        </Text>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 72,
      render: (_, row) => (
        <Button size="small" onClick={(e) => { e.stopPropagation(); setSelected(row); }}>
          详情
        </Button>
      ),
    },
  ];

  const p = selected?.raw_payload ?? {};
  const contacts = Array.isArray(p['contacts']) ? (p['contacts'] as Record<string, unknown>[]) : [];

  return (
    <>
      <div style={{ marginBottom: 12 }}>
        <Title level={4} style={{ margin: 0 }}>同行公司</Title>
        <Text type="secondary" style={{ fontSize: 13 }}>励销云采集的中国同行公司原始记录</Text>
      </div>

      {/* 筛选区 */}
      <div style={{ background: '#fff', borderRadius: 6, padding: '12px 16px 14px', marginBottom: 12, boxShadow: '0 1px 2px rgba(0,0,0,.06)' }}>
        <Form form={form} onFinish={onSearch}>
          {/* 第一行 */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 10 }}>
            <Form.Item name="name" style={{ margin: 0 }}>
              <Input placeholder="公司名（中文/英文）搜索" style={{ width: 220 }} allowClear />
            </Form.Item>
            <Form.Item name="keyword_filter" style={{ margin: 0 }}>
              <Select placeholder="全部关键词" style={{ width: 160 }} allowClear options={[]} />
            </Form.Item>
            <Text style={{ fontSize: 13, color: '#595959', whiteSpace: 'nowrap' }}>成立时间</Text>
            <Form.Item name="found_date" style={{ margin: 0 }}>
              <RangePicker style={{ width: 240 }} />
            </Form.Item>
          </div>
          {/* 第二行 */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            <Form.Item name="reg_capital" style={{ margin: 0 }}>
              <Select
                placeholder="注册资金（不限）"
                style={{ width: 150 }}
                allowClear
                options={[
                  { label: '< 100 万', value: 'lt100' },
                  { label: '100 – 500 万', value: '100_500' },
                  { label: '500 – 2000 万', value: '500_2000' },
                  { label: '2000 万 – 1 亿', value: '2000_1e' },
                  { label: '> 1 亿', value: 'gt1e' },
                ]}
              />
            </Form.Item>
            <Form.Item name="employee_scale" style={{ margin: 0 }}>
              <Select
                placeholder="员工规模（不限）"
                style={{ width: 150 }}
                allowClear
                options={[
                  { label: '< 10 人', value: 'lt10' },
                  { label: '10 – 50 人', value: '10_50' },
                  { label: '50 – 200 人', value: '50_200' },
                  { label: '200 – 1000 人', value: '200_1000' },
                  { label: '> 1000 人', value: 'gt1000' },
                ]}
              />
            </Form.Item>
            <Form.Item name="contacts_count" style={{ margin: 0 }}>
              <Select
                placeholder="联系人数（不限）"
                style={{ width: 150 }}
                allowClear
                options={[
                  { label: '0（无）', value: '0' },
                  { label: '1 – 3', value: '1_3' },
                  { label: '4 – 10', value: '4_10' },
                  { label: '> 10', value: 'gt10' },
                ]}
              />
            </Form.Item>
            <Form.Item name="has_name_en" valuePropName="checked" style={{ margin: 0 }}>
              <Checkbox>有英文名</Checkbox>
            </Form.Item>
            <Form.Item name="has_domain" valuePropName="checked" style={{ margin: 0 }}>
              <Checkbox>有域名</Checkbox>
            </Form.Item>
            <div style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>
              <Button type="primary" htmlType="submit">查询</Button>
              <Button onClick={onReset}>重置</Button>
            </div>
          </div>
        </Form>
      </div>

      <Table<LixiaoyunRow>
        columns={columns}
        dataSource={pageData.data}
        loading={query.isFetching}
        rowKey="id"
        size="small"
        scroll={{ x: 1300 }}
        onRow={(row) => ({ onClick: () => setSelected(row) })}
        pagination={{
          current: page,
          pageSize: PAGE_SIZE,
          total: pageData.pagination.total,
          onChange: setPage,
          showSizeChanger: false,
          showTotal: (total) => `共 ${total} 条`,
        }}
        style={{ background: '#fff', borderRadius: 6 }}
      />

      {/* 详情 Drawer */}
      <Drawer
        title={selected ? (pick(selected.raw_payload, 'name_cn', 'name_zh') || selected.name) : '详情'}
        open={Boolean(selected)}
        onClose={() => setSelected(null)}
        width={520}
        styles={{ body: { padding: 24 } }}
      >
        {selected && (
          <>
            <div style={{ fontSize: 11, fontWeight: 600, color: '#8c8c8c', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 10 }}>基本信息</div>
            <Descriptions column={1} size="small" bordered>
              <Descriptions.Item label="中文名">{pick(p, 'name_cn', 'name_zh') || selected.name}</Descriptions.Item>
              <Descriptions.Item label="英文名">{pick(p, 'name_en', 'name_english')}</Descriptions.Item>
              <Descriptions.Item label="网址">
                {(() => { const d = selected.domain ?? pick(p, 'website', 'domain'); return d && d !== '—' ? <Text style={{ color: '#1677ff' }}>{d}</Text> : '—'; })()}
              </Descriptions.Item>
              <Descriptions.Item label="成立时间">{pick(p, 'established_date', 'found_date', 'reg_date')}</Descriptions.Item>
              <Descriptions.Item label="员工规模">{pick(p, 'employee_scale', 'staff_num')}</Descriptions.Item>
              <Descriptions.Item label="注册资金">{pick(p, 'reg_capital', 'registered_capital')}</Descriptions.Item>
              <Descriptions.Item label="实缴资金">{pick(p, 'paid_capital', 'actual_capital')}</Descriptions.Item>
              <Descriptions.Item label="公司法人">{pick(p, 'legal_person', 'legal_representative')}</Descriptions.Item>
              <Descriptions.Item label="统一信用代码">
                <Text style={{ fontFamily: 'monospace', fontSize: 12 }}>{pick(p, 'credit_code', 'unified_credit_code')}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="注册地址">{pick(p, 'address', 'reg_address')}</Descriptions.Item>
              <Descriptions.Item label="通讯地址">{pick(p, 'contact_address', 'mailing_address')}</Descriptions.Item>
            </Descriptions>

            <div style={{ borderTop: '1px solid #f0f0f0', margin: '16px 0' }} />
            <div style={{ fontSize: 11, fontWeight: 600, color: '#8c8c8c', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 10 }}>采集信息</div>
            <Descriptions column={1} size="small" bordered>
              <Descriptions.Item label="励销云 ID">
                <Text style={{ fontFamily: 'monospace', fontSize: 12 }}>{selected.id}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="关键词">
                {pick(p, 'keyword', 'search_keyword') !== '—'
                  ? <Tag color="blue">{pick(p, 'keyword', 'search_keyword')}</Tag>
                  : '—'}
              </Descriptions.Item>
              <Descriptions.Item label="采集时间">{formatDateTime(selected.created_at)}</Descriptions.Item>
            </Descriptions>

            {contacts.length > 0 && (
              <>
                <div style={{ borderTop: '1px solid #f0f0f0', margin: '16px 0' }} />
                <div style={{ fontSize: 11, fontWeight: 600, color: '#8c8c8c', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 10 }}>
                  联系人（{contacts.length}）
                </div>
                <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                  <thead>
                    <tr style={{ background: '#fafafa' }}>
                      {['姓名', '职位', '电话', '邮箱'].map((h) => (
                        <th key={h} style={{ padding: '6px 10px', textAlign: 'left', borderBottom: '1px solid #f0f0f0', fontWeight: 500 }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {contacts.map((c, i) => (
                      <tr key={i} style={{ borderBottom: '1px solid #f0f0f0' }}>
                        <td style={{ padding: '6px 10px' }}>{String(c['name'] ?? '—')}</td>
                        <td style={{ padding: '6px 10px', color: '#595959' }}>{String(c['title'] ?? c['position'] ?? '—')}</td>
                        <td style={{ padding: '6px 10px', fontFamily: 'monospace' }}>{String(c['phone'] ?? c['mobile'] ?? '—')}</td>
                        <td style={{ padding: '6px 10px', color: '#8c8c8c' }}>{String(c['email'] ?? '—')}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </>
            )}
          </>
        )}
      </Drawer>
    </>
  );
}

Component.displayName = 'PeersDataPage';

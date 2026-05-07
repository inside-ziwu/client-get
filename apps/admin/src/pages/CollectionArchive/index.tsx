import { useState } from 'react';
import {
  Button,
  Descriptions,
  Drawer,
  Form,
  Input,
  InputNumber,
  Select,
  Space,
  Table,
  Tag,
  Typography,
  message,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { useQuery } from '@tanstack/react-query';
import { adminApi } from '../../lib/api';

const { Text, Title } = Typography;
const PAGE_SIZE = 20;

// ── 通用工具 ─────────────────────────────────────────────────────────
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
  pagination: { cursor: string | null; has_more: boolean; total?: number };
}

function emptyPage<T>(): PageData<T> {
  return { data: [], pagination: { cursor: null, has_more: false, total: 0 } };
}

function isNotFound(error: unknown) {
  return (error as { response?: { status?: number } }).response?.status === 404;
}

function formatDateTime(value: string | null | undefined) {
  return value ? new Date(value).toLocaleString('zh-CN', { hour12: false }) : '—';
}

/** 从 raw_payload 中取字符串值，按优先级依次尝试 key */
function pickStr(payload: Record<string, unknown>, ...keys: string[]): string {
  for (const k of keys) {
    const v = payload[k];
    if (v != null && v !== '') return String(v);
  }
  return '—';
}

/** 从 raw_payload 中取数字，不存在返回 null */
function pickNum(payload: Record<string, unknown>, ...keys: string[]): number | null {
  for (const k of keys) {
    const v = Number(payload[k]);
    if (!isNaN(v) && v > 0) return v;
  }
  return null;
}

/** 格式化美元金额 */
function fmtUsd(v: number | null) {
  if (v == null) return '—';
  if (v >= 1_000_000) return `$${(v / 1_000_000).toFixed(1)}M`;
  if (v >= 1_000) return `$${(v / 1_000).toFixed(0)}K`;
  return `$${v}`;
}

const COUNTRY_OPTIONS = [
  { label: '全部国家', value: '' },
  { label: '🇺🇸 美国', value: 'US' },
  { label: '🇩🇪 德国', value: 'DEU' },
  { label: '🇬🇧 英国', value: 'GBR' },
  { label: '🇯🇵 日本', value: 'JPN' },
  { label: '🇰🇷 韩国', value: 'KOR' },
  { label: '🇮🇳 印度', value: 'IND' },
  { label: '🇨🇦 加拿大', value: 'CAN' },
  { label: '🇦🇺 澳大利亚', value: 'AUS' },
  { label: '🇫🇷 法国', value: 'FRA' },
  { label: '🇳🇱 荷兰', value: 'NLD' },
  { label: '🇸🇪 瑞典', value: 'SWE' },
  { label: '🇨🇳 中国', value: 'CHN' },
];

const SIZE_OPTIONS = [
  { label: '全部规模', value: '' },
  { label: '微型（<10人）', value: 'tiny' },
  { label: '小型（10–49人）', value: 'small' },
  { label: '中型（50–199人）', value: 'medium' },
  { label: '大型（200+人）', value: 'large' },
];

// ── 腾道数据页 ───────────────────────────────────────────────────────
type TendataFilters = {
  keyword?: string;
  country?: string;
  industry?: string;
  tag?: string;
  size?: string;
  amountMin?: number;
  amountMax?: number;
  countMin?: number;
  countMax?: number;
  pcb?: string;
  contactMin?: number;
  contactMax?: number;
  yearMin?: number;
  yearMax?: number;
  method?: string;
};

function TendataPage() {
  const [form] = Form.useForm<TendataFilters>();
  const [page, setPage] = useState(1);
  const [applied, setApplied] = useState<TendataFilters>({});
  const [selected, setSelected] = useState<RawCompanyRow | null>(null);

  const query = useQuery({
    queryKey: ['admin', 'archive', 'tendata', page, applied.keyword, applied.country],
    queryFn: async () => {
      try {
        return (
          await adminApi.collection.listRawCompanies('tendata', {
            page,
            page_size: PAGE_SIZE,
            keyword: applied.keyword,
            country: applied.country || undefined,
          })
        ).data as PageData<RawCompanyRow>;
      } catch (error) {
        if (isNotFound(error)) return emptyPage<RawCompanyRow>();
        message.error('加载失败');
        return emptyPage<RawCompanyRow>();
      }
    },
  });

  const pageData = query.data ?? emptyPage<RawCompanyRow>();

  const onSearch = (values: TendataFilters) => {
    setApplied({
      keyword: values.keyword?.trim() || undefined,
      country: values.country || undefined,
    });
    setPage(1);
  };

  const onReset = () => {
    form.resetFields();
    setApplied({});
    setPage(1);
  };

  const columns: ColumnsType<RawCompanyRow> = [
    {
      title: '公司名称',
      key: 'name',
      ellipsis: true,
      width: 200,
      render: (_, row) => {
        const n = pickStr(row.raw_payload, 'name', 'company_name', 'name_en') !== '—'
          ? pickStr(row.raw_payload, 'name', 'company_name', 'name_en')
          : row.name;
        return <Text strong style={{ fontSize: 12 }}>{n}</Text>;
      },
    },
    {
      title: '国家',
      key: 'country',
      width: 80,
      render: (_, row) => {
        const flag = pickStr(row.raw_payload, 'flag');
        const iso = row.country || pickStr(row.raw_payload, 'country_iso3', 'country');
        return <Text style={{ fontSize: 12 }}>{flag !== '—' ? `${flag} ${iso}` : iso}</Text>;
      },
    },
    {
      title: '细分行业',
      key: 'industry',
      ellipsis: true,
      width: 160,
      render: (_, row) => (
        <Text type="secondary" style={{ fontSize: 12 }}>
          {pickStr(row.raw_payload, 'industry_desc', 'industry')}
        </Text>
      ),
    },
    {
      title: '产品标签',
      key: 'tags',
      width: 160,
      ellipsis: true,
      render: (_, row) => {
        const tags = Array.isArray(row.raw_payload['product_tags'])
          ? (row.raw_payload['product_tags'] as string[]).slice(0, 2)
          : [];
        return tags.length > 0
          ? <Space size={2} wrap>{tags.map((t, i) => <Tag key={i} style={{ fontSize: 11, margin: 0 }}>{t}</Tag>)}</Space>
          : <Text type="secondary">—</Text>;
      },
    },
    {
      title: '规模（人）',
      key: 'employee',
      width: 90,
      align: 'right' as const,
      render: (_, row) => {
        const n = pickNum(row.raw_payload, 'employee_num');
        return n != null ? <Text style={{ fontSize: 12 }}>{n.toLocaleString()}</Text> : <Text type="secondary">—</Text>;
      },
    },
    {
      title: '官网',
      key: 'website',
      width: 150,
      ellipsis: true,
      render: (_, row) => {
        const d = row.domain || pickStr(row.raw_payload, 'website', 'domain');
        return d && d !== '—'
          ? <Text style={{ fontSize: 12, color: '#1677ff' }}>{d}</Text>
          : <Text type="secondary">—</Text>;
      },
    },
    {
      title: '进口额（3年）',
      key: 'trade_amount',
      width: 110,
      align: 'right' as const,
      render: (_, row) => {
        const v = pickNum(row.raw_payload, 'trade_amount_3y_usd');
        return <Text style={{ fontSize: 12 }}>{fmtUsd(v)}</Text>;
      },
    },
    {
      title: '次数',
      key: 'trade_count',
      width: 70,
      align: 'right' as const,
      render: (_, row) => {
        const n = pickNum(row.raw_payload, 'trade_count_3y');
        return <Text style={{ fontSize: 12 }}>{n ?? '—'}</Text>;
      },
    },
    {
      title: '联系人',
      key: 'contacts',
      width: 70,
      align: 'center' as const,
      render: (_, row) => {
        const n = pickNum(row.raw_payload, 'contacts_count');
        return <Tag color={n && n > 0 ? 'green' : 'default'}>{n ?? 0}</Tag>;
      },
    },
    {
      title: '成立年',
      key: 'est_year',
      width: 80,
      align: 'center' as const,
      render: (_, row) => {
        const d = pickStr(row.raw_payload, 'incorporation_date', 'established_year');
        if (d === '—') return <Text type="secondary">—</Text>;
        return <Text style={{ fontSize: 12 }}>{String(d).slice(0, 4)}</Text>;
      },
    },
    {
      title: '供应商',
      key: 'suppliers',
      width: 60,
      align: 'center' as const,
      render: (_, row) => {
        const arr = Array.isArray(row.raw_payload['pcb_suppliers'])
          ? (row.raw_payload['pcb_suppliers'] as unknown[]).length
          : 0;
        return <Tag color={arr > 0 ? 'blue' : 'default'}>{arr}</Tag>;
      },
    },
    {
      title: '采集方式',
      key: 'method',
      width: 90,
      render: (_, row) => {
        const m = pickStr(row.raw_payload, 'collection_method');
        return m !== '—'
          ? <Tag color="purple" style={{ fontSize: 11 }}>{m}</Tag>
          : <Text type="secondary">—</Text>;
      },
    },
    {
      title: '关键词',
      key: 'keyword',
      width: 120,
      ellipsis: true,
      render: (_, row) => {
        const kw = pickStr(row.raw_payload, 'keyword');
        return kw !== '—'
          ? <Tag color="blue" style={{ fontSize: 11 }}>{kw}</Tag>
          : <Text type="secondary">—</Text>;
      },
    },
    {
      title: '更新时间',
      key: 'created_at',
      width: 140,
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
  const contacts = Array.isArray(p['contacts'])
    ? (p['contacts'] as Record<string, unknown>[])
    : [];
  const tags = Array.isArray(p['product_tags']) ? p['product_tags'] as string[] : [];
  const suppliers = Array.isArray(p['pcb_suppliers']) ? p['pcb_suppliers'] as string[] : [];

  return (
    <>
      <div style={{ marginBottom: 12 }}>
        <Title level={4} style={{ margin: 0 }}>腾道数据</Title>
        <Text type="secondary" style={{ fontSize: 13 }}>腾道采集的海外买家原始记录</Text>
      </div>

      {/* 筛选区 */}
      <div style={{ background: '#fff', borderRadius: 6, padding: '12px 16px 14px', marginBottom: 12, boxShadow: '0 1px 2px rgba(0,0,0,.06)' }}>
        <Form form={form} onFinish={onSearch}>
          {/* 第一行 */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 10 }}>
            <Form.Item name="keyword" style={{ margin: 0 }}>
              <Input placeholder="公司名 / 官网搜索" style={{ width: 176 }} allowClear />
            </Form.Item>
            <Form.Item name="country" style={{ margin: 0 }}>
              <Select placeholder="全部国家" style={{ width: 130 }} allowClear options={COUNTRY_OPTIONS} />
            </Form.Item>
            <Form.Item name="industry" style={{ margin: 0 }}>
              <Input placeholder="细分行业" style={{ width: 100 }} allowClear />
            </Form.Item>
            <Form.Item name="keyword_filter" style={{ margin: 0 }}>
              <Select placeholder="全部关键词" style={{ width: 160 }} allowClear options={[]} />
            </Form.Item>
            <Form.Item name="tag" style={{ margin: 0 }}>
              <Input placeholder="产品标签" style={{ width: 100 }} allowClear />
            </Form.Item>
            <Form.Item name="size" style={{ margin: 0 }}>
              <Select placeholder="全部规模" style={{ width: 140 }} allowClear options={SIZE_OPTIONS} />
            </Form.Item>
          </div>
          {/* 第二行 */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            <Text style={{ fontSize: 13, color: '#595959', whiteSpace: 'nowrap' }}>进口额</Text>
            <Form.Item name="amountMin" style={{ margin: 0 }}>
              <InputNumber placeholder="最小" style={{ width: 90 }} min={0} controls={false} />
            </Form.Item>
            <Text style={{ color: '#bfbfbf' }}>—</Text>
            <Form.Item name="amountMax" style={{ margin: 0 }}>
              <InputNumber placeholder="最大" style={{ width: 90 }} min={0} controls={false} />
            </Form.Item>
            <Text style={{ fontSize: 13, color: '#595959', whiteSpace: 'nowrap' }}>进口次数</Text>
            <Form.Item name="countMin" style={{ margin: 0 }}>
              <InputNumber placeholder="最小" style={{ width: 64 }} min={0} controls={false} />
            </Form.Item>
            <Text style={{ color: '#bfbfbf' }}>—</Text>
            <Form.Item name="countMax" style={{ margin: 0 }}>
              <InputNumber placeholder="最大" style={{ width: 64 }} min={0} controls={false} />
            </Form.Item>
            <Form.Item name="pcb" style={{ margin: 0 }}>
              <Select placeholder="PCB供应商" style={{ width: 110 }} allowClear
                options={[{ label: '有供应商', value: 'yes' }, { label: '无供应商', value: 'no' }]} />
            </Form.Item>
            <Text style={{ fontSize: 13, color: '#595959', whiteSpace: 'nowrap' }}>联系人</Text>
            <Form.Item name="contactMin" style={{ margin: 0 }}>
              <InputNumber placeholder="最小" style={{ width: 56 }} min={0} controls={false} />
            </Form.Item>
            <Text style={{ color: '#bfbfbf' }}>—</Text>
            <Form.Item name="contactMax" style={{ margin: 0 }}>
              <InputNumber placeholder="最大" style={{ width: 56 }} min={0} controls={false} />
            </Form.Item>
            <Text style={{ fontSize: 13, color: '#595959', whiteSpace: 'nowrap' }}>成立年</Text>
            <Form.Item name="yearMin" style={{ margin: 0 }}>
              <InputNumber placeholder="起" style={{ width: 64 }} min={1900} max={2030} controls={false} />
            </Form.Item>
            <Text style={{ color: '#bfbfbf' }}>—</Text>
            <Form.Item name="yearMax" style={{ margin: 0 }}>
              <InputNumber placeholder="止" style={{ width: 64 }} min={1900} max={2030} controls={false} />
            </Form.Item>
            <Form.Item name="method" style={{ margin: 0 }}>
              <Select placeholder="采集方式" style={{ width: 100 }} allowClear
                options={[{ label: '关键词', value: 'keyword' }, { label: '推荐', value: 'recommendation' }]} />
            </Form.Item>
            <div style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>
              <Button type="primary" htmlType="submit">查询</Button>
              <Button onClick={onReset}>重置</Button>
            </div>
          </div>
        </Form>
      </div>

      <Table<RawCompanyRow>
        columns={columns}
        dataSource={pageData.data}
        loading={query.isFetching}
        rowKey="id"
        size="small"
        scroll={{ x: 1600 }}
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
        title={
          selected
            ? (pickStr(selected.raw_payload, 'name', 'company_name', 'name_en') !== '—'
                ? pickStr(selected.raw_payload, 'name', 'company_name', 'name_en')
                : selected.name)
            : '详情'
        }
        open={Boolean(selected)}
        onClose={() => setSelected(null)}
        width={860}
        styles={{ body: { padding: 24 } }}
      >
        {selected && (
          <>
            {/* 基本信息 */}
            <div style={{ fontSize: 11, fontWeight: 600, color: '#8c8c8c', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 10 }}>基本信息</div>
            <Descriptions column={2} size="small" bordered>
              <Descriptions.Item label="公司名">
                {pickStr(p, 'name', 'company_name', 'name_en') !== '—'
                  ? pickStr(p, 'name', 'company_name', 'name_en')
                  : selected.name}
              </Descriptions.Item>
              <Descriptions.Item label="英文名">
                {pickStr(p, 'name_en', 'name')}
              </Descriptions.Item>
              <Descriptions.Item label="国家">
                {(() => {
                  const flag = pickStr(p, 'flag');
                  const iso = selected.country || pickStr(p, 'country_iso3', 'country');
                  return flag !== '—' ? `${flag} ${iso}` : iso;
                })()}
              </Descriptions.Item>
              <Descriptions.Item label="成立时间">
                {pickStr(p, 'incorporation_date', 'established_year')}
              </Descriptions.Item>
              <Descriptions.Item label="官网" span={2}>
                {(() => {
                  const d = selected.domain || pickStr(p, 'website', 'domain');
                  return d && d !== '—'
                    ? <Text style={{ color: '#1677ff' }}>{d}</Text>
                    : '—';
                })()}
              </Descriptions.Item>
              <Descriptions.Item label="细分行业" span={2}>
                {pickStr(p, 'industry_desc', 'industry')}
              </Descriptions.Item>
              <Descriptions.Item label="产品标签" span={2}>
                {tags.length > 0
                  ? <Space size={4} wrap>{tags.map((t, i) => <Tag key={i}>{t}</Tag>)}</Space>
                  : '—'}
              </Descriptions.Item>
              <Descriptions.Item label="PCB供应商" span={2}>
                {suppliers.length > 0
                  ? <Space size={4} wrap>{suppliers.map((s, i) => <Tag key={i} color="blue">{String(s)}</Tag>)}</Space>
                  : '—'}
              </Descriptions.Item>
            </Descriptions>

            {/* 规模与贸易 */}
            <div style={{ borderTop: '1px solid #f0f0f0', margin: '16px 0' }} />
            <div style={{ fontSize: 11, fontWeight: 600, color: '#8c8c8c', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 10 }}>规模与贸易</div>
            <Descriptions column={3} size="small" bordered>
              <Descriptions.Item label="员工数">
                {(() => {
                  const n = pickNum(p, 'employee_num');
                  return n != null ? `${n.toLocaleString()} 人` : '—';
                })()}
              </Descriptions.Item>
              <Descriptions.Item label="3年进口额">
                {fmtUsd(pickNum(p, 'trade_amount_3y_usd'))}
              </Descriptions.Item>
              <Descriptions.Item label="3年进口次数">
                {pickNum(p, 'trade_count_3y') ?? '—'}
              </Descriptions.Item>
            </Descriptions>

            {/* 联系人 */}
            <div style={{ borderTop: '1px solid #f0f0f0', margin: '16px 0' }} />
            <div style={{ fontSize: 11, fontWeight: 600, color: '#8c8c8c', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 10 }}>
              关联联系人（{contacts.length} 人）
            </div>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12, tableLayout: 'fixed' }}>
              <thead>
                <tr style={{ background: '#fafafa' }}>
                  {['姓名', '职位', '邮箱', '重要度', '验证'].map((h) => (
                    <th key={h} style={{ padding: '6px 10px', textAlign: 'left', borderBottom: '1px solid #f0f0f0', fontWeight: 500 }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {contacts.length === 0
                  ? <tr><td colSpan={5} style={{ padding: '16px 10px', textAlign: 'center', color: '#8c8c8c' }}>暂无联系人</td></tr>
                  : contacts.map((c, i) => (
                    <tr key={i} style={{ borderBottom: '1px solid #f0f0f0' }}>
                      <td style={{ padding: '6px 10px' }}>{String(c['name'] ?? '—')}</td>
                      <td style={{ padding: '6px 10px', color: '#595959' }}>{String(c['title'] ?? c['position'] ?? '—')}</td>
                      <td style={{ padding: '6px 10px', color: '#1677ff', overflow: 'hidden', textOverflow: 'ellipsis' }}>{String(c['email'] ?? '—')}</td>
                      <td style={{ padding: '6px 10px', textAlign: 'center' }}>{String(c['importance'] ?? c['score'] ?? '—')}</td>
                      <td style={{ padding: '6px 10px', textAlign: 'center' }}>
                        {c['email_verified']
                          ? <Tag color="green" style={{ margin: 0 }}>已验</Tag>
                          : <Tag color="default" style={{ margin: 0 }}>未验</Tag>}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </>
        )}
      </Drawer>
    </>
  );
}

// ── 客户数据页（清洗公司） ────────────────────────────────────────────
type CleanFilters = {
  keyword?: string;
  country?: string;
  industry?: string;
  tag?: string;
  size?: string;
  amountMin?: number;
  amountMax?: number;
  countMin?: number;
  countMax?: number;
  pcb?: string;
  contactMin?: number;
  contactMax?: number;
  yearMin?: number;
  yearMax?: number;
};

const INDUSTRY_OPTIONS = [
  { label: '全部细分行业', value: '' },
  { label: 'PCB制造', value: 'PCB制造' },
  { label: 'EMS代工', value: 'EMS代工' },
  { label: 'PCB设计', value: 'PCB设计' },
  { label: '分销商/代理', value: '分销商/代理' },
  { label: '航空航天', value: '航空航天' },
  { label: '医疗（认证）', value: '医疗（认证）' },
  { label: '汽车电子（认证）', value: '汽车电子（认证）' },
];

function CleanArchivePage() {
  const [form] = Form.useForm<CleanFilters>();
  const [page, setPage] = useState(1);
  const [applied, setApplied] = useState<CleanFilters>({});
  const [selected, setSelected] = useState<CleanCompanyRow | null>(null);

  const query = useQuery({
    queryKey: ['admin', 'archive', 'clean', page, applied.keyword],
    queryFn: async () => {
      try {
        return (
          await adminApi.collection.listCleanCompanies({
            page,
            page_size: PAGE_SIZE,
            keyword: applied.keyword,
          })
        ).data as PageData<CleanCompanyRow>;
      } catch (error) {
        if (isNotFound(error)) return emptyPage<CleanCompanyRow>();
        message.error('加载失败');
        return emptyPage<CleanCompanyRow>();
      }
    },
  });

  const pageData = query.data ?? emptyPage<CleanCompanyRow>();

  const onSearch = (values: CleanFilters) => {
    setApplied({ keyword: values.keyword?.trim() || undefined });
    setPage(1);
  };

  const onReset = () => {
    form.resetFields();
    setApplied({});
    setPage(1);
  };

  const columns: ColumnsType<CleanCompanyRow> = [
    {
      title: '公司名称',
      key: 'name',
      ellipsis: true,
      width: 220,
      render: (_, row) => <Text strong style={{ fontSize: 12 }}>{row.name_display || row.name_normalized}</Text>,
    },
    {
      title: '国家/地区',
      key: 'country',
      width: 90,
      render: (_, row) => <Text style={{ fontSize: 12 }}>{row.country_iso3 || '—'}</Text>,
    },
    {
      title: '细分行业',
      key: 'industry',
      width: 120,
      render: () => <Text type="secondary">—</Text>,
    },
    {
      title: '员工规模',
      key: 'size',
      width: 90,
      render: () => <Text type="secondary">—</Text>,
    },
    {
      title: '近3年进口额',
      key: 'trade',
      width: 110,
      align: 'right' as const,
      render: () => <Text type="secondary">—</Text>,
    },
    {
      title: '工厂性质',
      key: 'factory',
      width: 90,
      render: () => <Text type="secondary">—</Text>,
    },
    {
      title: '供应商',
      key: 'supplier',
      width: 70,
      align: 'center' as const,
      render: () => <Text type="secondary">—</Text>,
    },
    {
      title: '联系人数',
      key: 'contacts',
      width: 80,
      align: 'center' as const,
      render: () => <Text type="secondary">—</Text>,
    },
    {
      title: '数据来源',
      key: 'sources',
      width: 160,
      render: (_, row) => (
        <Space size={4} wrap>
          {row.sources.map((s) => <Tag key={s} style={{ fontSize: 11, margin: 0 }}>{s}</Tag>)}
        </Space>
      ),
    },
    {
      title: '域名',
      key: 'domain',
      width: 150,
      ellipsis: true,
      render: (_, row) => row.domain
        ? <Text style={{ fontSize: 12, color: '#1677ff' }}>{row.domain}</Text>
        : <Text type="secondary">—</Text>,
    },
    {
      title: '入库时间',
      key: 'created_at',
      width: 140,
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

  return (
    <>
      <div style={{ marginBottom: 12 }}>
        <Title level={4} style={{ margin: 0 }}>客户数据</Title>
        <Text type="secondary" style={{ fontSize: 13 }}>经清洗去重后的正式客户公司库</Text>
      </div>

      {/* 筛选区 */}
      <div style={{ background: '#fff', borderRadius: 6, padding: '12px 16px 14px', marginBottom: 12, boxShadow: '0 1px 2px rgba(0,0,0,.06)' }}>
        <Form form={form} onFinish={onSearch}>
          {/* 第一行 */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 10 }}>
            <Form.Item name="keyword" style={{ margin: 0 }}>
              <Input placeholder="公司名 / 域名搜索" style={{ width: 176 }} allowClear />
            </Form.Item>
            <Form.Item name="country" style={{ margin: 0 }}>
              <Select placeholder="全部国家" style={{ width: 130 }} allowClear options={COUNTRY_OPTIONS} />
            </Form.Item>
            <Form.Item name="industry" style={{ margin: 0 }}>
              <Select placeholder="全部细分行业" style={{ width: 148 }} allowClear options={INDUSTRY_OPTIONS} />
            </Form.Item>
            <Form.Item name="keyword_filter" style={{ margin: 0 }}>
              <Select placeholder="全部关键词" style={{ width: 160 }} allowClear options={[]} />
            </Form.Item>
            <Form.Item name="tag" style={{ margin: 0 }}>
              <Input placeholder="产品标签" style={{ width: 110 }} allowClear />
            </Form.Item>
            <Form.Item name="size" style={{ margin: 0 }}>
              <Select placeholder="全部规模" style={{ width: 150 }} allowClear options={SIZE_OPTIONS} />
            </Form.Item>
          </div>
          {/* 第二行 */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            <Text style={{ fontSize: 13, color: '#595959', whiteSpace: 'nowrap' }}>进口额</Text>
            <Form.Item name="amountMin" style={{ margin: 0 }}>
              <InputNumber placeholder="最小(USD)" style={{ width: 100 }} min={0} controls={false} />
            </Form.Item>
            <Text style={{ color: '#bfbfbf' }}>—</Text>
            <Form.Item name="amountMax" style={{ margin: 0 }}>
              <InputNumber placeholder="最大(USD)" style={{ width: 100 }} min={0} controls={false} />
            </Form.Item>
            <Text style={{ fontSize: 13, color: '#595959', whiteSpace: 'nowrap' }}>进口次数</Text>
            <Form.Item name="countMin" style={{ margin: 0 }}>
              <InputNumber placeholder="最小" style={{ width: 64 }} min={0} controls={false} />
            </Form.Item>
            <Text style={{ color: '#bfbfbf' }}>—</Text>
            <Form.Item name="countMax" style={{ margin: 0 }}>
              <InputNumber placeholder="最大" style={{ width: 64 }} min={0} controls={false} />
            </Form.Item>
            <Form.Item name="pcb" style={{ margin: 0 }}>
              <Select placeholder="PCB供应商" style={{ width: 110 }} allowClear
                options={[{ label: '有供应商', value: 'yes' }, { label: '无供应商', value: 'no' }]} />
            </Form.Item>
            <Text style={{ fontSize: 13, color: '#595959', whiteSpace: 'nowrap' }}>联系人</Text>
            <Form.Item name="contactMin" style={{ margin: 0 }}>
              <InputNumber placeholder="最小" style={{ width: 56 }} min={0} controls={false} />
            </Form.Item>
            <Text style={{ color: '#bfbfbf' }}>—</Text>
            <Form.Item name="contactMax" style={{ margin: 0 }}>
              <InputNumber placeholder="最大" style={{ width: 56 }} min={0} controls={false} />
            </Form.Item>
            <Text style={{ fontSize: 13, color: '#595959', whiteSpace: 'nowrap' }}>成立年</Text>
            <Form.Item name="yearMin" style={{ margin: 0 }}>
              <InputNumber placeholder="起始" style={{ width: 64 }} min={1900} max={2030} controls={false} />
            </Form.Item>
            <Text style={{ color: '#bfbfbf' }}>—</Text>
            <Form.Item name="yearMax" style={{ margin: 0 }}>
              <InputNumber placeholder="截止" style={{ width: 64 }} min={1900} max={2030} controls={false} />
            </Form.Item>
            <div style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>
              <Button type="primary" htmlType="submit">查询</Button>
              <Button onClick={onReset}>重置</Button>
            </div>
          </div>
        </Form>
      </div>

      <Table<CleanCompanyRow>
        columns={columns}
        dataSource={pageData.data}
        loading={query.isFetching}
        rowKey="id"
        size="small"
        scroll={{ x: 1400 }}
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
        title={selected ? (selected.name_display || selected.name_normalized) : '详情'}
        open={Boolean(selected)}
        onClose={() => setSelected(null)}
        width={640}
        styles={{ body: { padding: 24 } }}
      >
        {selected && (
          <>
            <div style={{ fontSize: 11, fontWeight: 600, color: '#8c8c8c', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 10 }}>基本信息</div>
            <Descriptions column={1} size="small" bordered>
              <Descriptions.Item label="展示名称">{selected.name_display}</Descriptions.Item>
              <Descriptions.Item label="标准名称">
                <Text style={{ fontFamily: 'monospace', fontSize: 12 }}>{selected.name_normalized}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="国家/地区">{selected.country_iso3 ?? '—'}</Descriptions.Item>
              <Descriptions.Item label="域名">
                {selected.domain
                  ? <Text style={{ color: '#1677ff' }}>{selected.domain}</Text>
                  : '—'}
              </Descriptions.Item>
              <Descriptions.Item label="数据来源">
                <Space size={4} wrap>
                  {selected.sources.map((s) => <Tag key={s}>{s}</Tag>)}
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="入库时间">{formatDateTime(selected.created_at)}</Descriptions.Item>
            </Descriptions>

            <div style={{ borderTop: '1px solid #f0f0f0', margin: '16px 0' }} />
            <div style={{ fontSize: 11, fontWeight: 600, color: '#8c8c8c', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 8 }}>
              扩展信息
            </div>
            <Text type="secondary" style={{ fontSize: 13 }}>
              细分行业、员工规模、贸易额等字段来自腾道原始数据，可通过腾道数据页查看。
            </Text>
          </>
        )}
      </Drawer>
    </>
  );
}

// ── 三个路由 Component 导出 ───────────────────────────────────────────
export function PeersComponent() {
  // 同行公司已迁移至 /collection/peers (PeersData页)
  // 此处保留兼容导出
  return null;
}

export function TendataComponent() {
  return <TendataPage />;
}

export function CustomersComponent() {
  return <CleanArchivePage />;
}

export { TendataComponent as Component };

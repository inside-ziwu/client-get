import { useState } from 'react';
import {
  Card,
  Tabs,
  Select,
  Space,
  Typography,
  Tag,
  Button,
  Divider,
  Spin,
  Alert,
} from 'antd';
import {
  LinkOutlined,
  RobotOutlined,
} from '@ant-design/icons';

const { Text, Title, Paragraph } = Typography;
const { Option } = Select;

interface Article {
  id: string;
  title: string;
  category: '行业动态' | '政策法规' | '价格走势' | '客户动态';
  source: string;
  date: string;
  summary: string;
  url: string;
  ai_summary?: string;
}

const MOCK_ARTICLES: Article[] = [
  {
    id: 'a1',
    title: '全球PCB市场Q1出货量同比增长12%，高端HDI需求尤为强劲',
    category: '行业动态',
    source: 'PCBindustry.com',
    date: '2026-04-16',
    summary: '据最新行业报告显示，2026年第一季度全球印刷电路板市场出货量同比增长12%，其中高密度互连（HDI）板需求增长尤为突出，主要受益于5G设备和AI服务器采购的持续拉动。',
    url: '#',
    ai_summary: '德国客户群与5G、AI服务器高度相关。建议在下一轮开发信中突出HDI技术能力，可提升S/A级客户回复率约15-20%。',
  },
  {
    id: 'a2',
    title: '欧盟新电子产品法规ESPR将于2026年Q3生效，PCB供应商需提前备案',
    category: '政策法规',
    source: 'EU Official Journal',
    date: '2026-04-15',
    summary: '欧盟可持续产品法规（ESPR）将于今年第三季度正式实施，要求进入欧盟市场的电子产品供应商提供完整的材料声明和碳足迹数据，PCB制造商需在6月前完成备案。',
    url: '#',
    ai_summary: '您有23家欧盟目标客户，政策合规是当前痛点。建议发送合规支持主题邮件，以"我们已完成ESPR备案"作为切入点，预计可显著提升联系成功率。',
  },
  {
    id: 'a3',
    title: '铜箔原材料价格Q2小幅回落，PCB制造成本压力有望缓解',
    category: '价格走势',
    source: 'MetalPriceLive',
    date: '2026-04-14',
    summary: '受全球铜矿产量恢复和需求结构调整影响，PCB核心原材料铜箔价格在Q2初期出现小幅回落，较Q1高点下降约3.2%，PCB制造商的成本压力有望在下半年逐步缓解。',
    url: '#',
    ai_summary: '成本回落窗口期是争取价格敏感型客户的好时机。建议向C/D级客户发送以"成本优化"为主题的开发信，转化率可能高于均值。',
  },
  {
    id: 'a4',
    title: 'Müller Electronics GmbH扩大在华PCB采购规模，寻找新供应商',
    category: '客户动态',
    source: '海关数据',
    date: '2026-04-13',
    summary: 'Müller Electronics GmbH近三个月采购量同比增加45%，并在多个B2B平台更新了采购需求，主要集中在4-8层标准FR4和薄型FPC领域，正积极寻找价格和品质兼顾的供应商。',
    url: '#',
    ai_summary: '该公司已在您的精选客户库中（评级B）。采购量激增信号显示其处于供应商切换期，建议立即升级为A级并优先触达，当前是最佳窗口。',
  },
  {
    id: 'a5',
    title: '日本半导体设备投资持续扩张，带动配套PCB订单增量',
    category: '行业动态',
    source: 'SemiInsider Japan',
    date: '2026-04-12',
    summary: '日本半导体设备行业2026财年资本支出计划同比增加28%，直接带动高精度多层PCB的配套需求。主要受益的细分市场包括测试设备板、探针卡和封装基板。',
    url: '#',
    ai_summary: '您的日本精密客户群（31家）与此高度相关。建议优先推进日本精密电路合作方开发计划，并在模板中加入测试设备板的技术规格。',
  },
  {
    id: 'a6',
    title: '美国IPC APEX展会回顾：AI驱动PCB设计自动化成最大亮点',
    category: '行业动态',
    source: 'IPC Official',
    date: '2026-04-10',
    summary: '本届IPC APEX EXPO上，AI驱动的PCB设计自动化工具受到广泛关注，多家EDA厂商发布了基于大模型的布线优化和DFM检查工具，业内预计2026年将是PCB设计智能化的关键转折年。',
    url: '#',
  },
];

const CATEGORY_COLOR: Record<string, string> = {
  '行业动态': 'blue',
  '政策法规': 'orange',
  '价格走势': 'green',
  '客户动态': 'purple',
};

const TIME_OPTIONS = [
  { label: '最近7天', value: '7' },
  { label: '最近30天', value: '30' },
  { label: '最近90天', value: '90' },
];

const AI_BALANCE = 520;

function ArticleCard({ article, showAI }: { article: Article; showAI: boolean }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div style={{ borderBottom: '1px solid #f0f0f0', padding: '16px 0' }}>
      <Space style={{ marginBottom: 8 }}>
        <Tag color={CATEGORY_COLOR[article.category]}>{article.category}</Tag>
        <Text type="secondary" style={{ fontSize: 12 }}>{article.source}</Text>
        <Text type="secondary" style={{ fontSize: 12 }}>·</Text>
        <Text type="secondary" style={{ fontSize: 12 }}>{article.date}</Text>
      </Space>
      <Title level={5} style={{ marginBottom: 8, marginTop: 0 }}>{article.title}</Title>
      <Paragraph
        type="secondary"
        style={{ fontSize: 13, marginBottom: showAI && article.ai_summary ? 12 : 4 }}
        ellipsis={expanded ? false : { rows: 2, expandable: false }}
      >
        {article.summary}
      </Paragraph>
      {showAI && article.ai_summary && (
        <div style={{
          background: '#f0f5ff',
          border: '1px solid #adc6ff',
          borderRadius: 6,
          padding: '10px 14px',
          marginBottom: 8,
        }}>
          <Space style={{ marginBottom: 4 }}>
            <RobotOutlined style={{ color: '#4096ff' }} />
            <Text style={{ fontSize: 12, color: '#4096ff', fontWeight: 500 }}>AI 洞察</Text>
          </Space>
          <div><Text style={{ fontSize: 13 }}>{article.ai_summary}</Text></div>
        </div>
      )}
      <Space>
        <Button
          type="link"
          size="small"
          icon={<LinkOutlined />}
          href={article.url}
          style={{ paddingLeft: 0 }}
        >
          查看原文
        </Button>
        <Button
          type="link"
          size="small"
          style={{ paddingLeft: 0 }}
          onClick={() => setExpanded((v) => !v)}
        >
          {expanded ? '收起' : '展开'}
        </Button>
      </Space>
    </div>
  );
}

export function Component() {
  const [activeCategory, setActiveCategory] = useState('all');
  const [timeRange, setTimeRange] = useState('7');
  const [visibleCount, setVisibleCount] = useState(4);
  const [loadingMore, setLoadingMore] = useState(false);

  const filtered = MOCK_ARTICLES.filter(
    (a) => activeCategory === 'all' || a.category === activeCategory
  );
  const visible = filtered.slice(0, visibleCount);
  const hasMore = visibleCount < filtered.length;
  const showAI = AI_BALANCE > 0;

  const handleLoadMore = () => {
    setLoadingMore(true);
    setTimeout(() => {
      setVisibleCount((v) => v + 4);
      setLoadingMore(false);
    }, 800);
  };

  const tabItems = [
    { key: 'all', label: `全部 (${MOCK_ARTICLES.length})` },
    { key: '行业动态', label: '行业动态' },
    { key: '政策法规', label: '政策法规' },
    { key: '价格走势', label: '价格走势' },
    { key: '客户动态', label: '客户动态' },
  ];

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      {!showAI && (
        <Alert
          type="warning"
          showIcon
          message="AI 额度不足，AI 洞察已隐藏。请联系管理员充值后恢复。"
        />
      )}

      <Card
        bodyStyle={{ padding: 0 }}
        title={
          <Tabs
            activeKey={activeCategory}
            onChange={(k) => { setActiveCategory(k); setVisibleCount(4); }}
            items={tabItems}
            style={{ marginBottom: -1 }}
          />
        }
        extra={
          <Select
            value={timeRange}
            onChange={setTimeRange}
            style={{ width: 120 }}
            size="small"
          >
            {TIME_OPTIONS.map((o) => (
              <Option key={o.value} value={o.value}>{o.label}</Option>
            ))}
          </Select>
        }
      >
        <div style={{ padding: '0 24px' }}>
          {visible.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '48px 0' }}>
              <Text type="secondary">暂无相关情报</Text>
            </div>
          ) : (
            visible.map((article) => (
              <ArticleCard key={article.id} article={article} showAI={showAI} />
            ))
          )}

          {hasMore && (
            <>
              <Divider />
              <div style={{ textAlign: 'center', paddingBottom: 16 }}>
                {loadingMore ? (
                  <Spin size="small" />
                ) : (
                  <Button onClick={handleLoadMore}>加载更多</Button>
                )}
              </div>
            </>
          )}

          {!hasMore && visible.length > 0 && (
            <div style={{ textAlign: 'center', padding: '16px 0' }}>
              <Text type="secondary" style={{ fontSize: 12 }}>已显示全部 {filtered.length} 条情报</Text>
            </div>
          )}
        </div>
      </Card>

      {showAI && (
        <Card size="small">
          <Space>
            <RobotOutlined style={{ color: '#1677ff' }} />
            <Text type="secondary" style={{ fontSize: 12 }}>
              AI 洞察由 DeepSeek V3 生成，基于您的客户画像和行业情报自动匹配。当前 AI 额度：
              <Text strong style={{ color: '#1677ff' }}> {AI_BALANCE} tokens</Text>
            </Text>
          </Space>
        </Card>
      )}
    </Space>
  );
}

Component.displayName = 'IntelligencePage';

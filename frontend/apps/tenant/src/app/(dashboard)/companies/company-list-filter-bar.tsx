'use client';

import type { FilterField, FilterFieldRenderContext } from '@shared/ui';
import { FilterBar, Input } from '@shared/ui';
import {
  type FilterValues,
  countryZh,
} from '@/components/company-filters';

interface FiltersOptions {
  countries?: string[];
  sub_industries?: string[];
  product_tags?: string[];
  grades?: string[];
}

interface CompanyListFilterBarProps {
  values: FilterValues;
  options?: FiltersOptions;
  optionsState: 'ready' | 'loading' | 'empty';
  appliedCount: number;
  isSubmitting: boolean;
  onChange: (next: FilterValues) => void;
  onSubmit: (next: FilterValues) => void;
  onReset: () => void;
}

const SYSTEM_GRADES = ['S', 'A', 'B', 'C', 'D'] as const;

type RangeFilterName =
  | 'trade_amount_min'
  | 'trade_amount_max'
  | 'trade_count_min'
  | 'trade_count_max'
  | 'contact_count_min'
  | 'contact_count_max'
  | 'founded_year_from'
  | 'founded_year_to';

interface RangeFilterConfig {
  label: string;
  startName: RangeFilterName;
  startLabel: string;
  startPrefix: string;
  endName: RangeFilterName;
  endLabel: string;
  endPrefix: string;
}

const RANGE_FILTERS: ReadonlyArray<RangeFilterConfig> = [
  {
    label: '进口额',
    startName: 'trade_amount_min',
    startLabel: '最低进口额',
    startPrefix: '最低',
    endName: 'trade_amount_max',
    endLabel: '最高进口额',
    endPrefix: '最高',
  },
  {
    label: '进口次数',
    startName: 'trade_count_min',
    startLabel: '最低进口次数',
    startPrefix: '最低',
    endName: 'trade_count_max',
    endLabel: '最高进口次数',
    endPrefix: '最高',
  },
  {
    label: '联系人',
    startName: 'contact_count_min',
    startLabel: '最少联系人',
    startPrefix: '最少',
    endName: 'contact_count_max',
    endLabel: '最多联系人',
    endPrefix: '最多',
  },
  {
    label: '成立年份',
    startName: 'founded_year_from',
    startLabel: '成立年份起',
    startPrefix: '起始',
    endName: 'founded_year_to',
    endLabel: '成立年份止',
    endPrefix: '截止',
  },
];

const toOptions = (items: readonly string[], label: (value: string) => string = (value) => value) =>
  items.map((value) => ({ value, label: label(value) }));

function RangeFilterControl({
  config,
  values,
  setValue,
  disabled,
}: FilterFieldRenderContext<FilterValues> & { config: RangeFilterConfig }) {
  const renderEndpoint = (
    name: RangeFilterName,
    label: string,
    prefix: string,
  ) => (
    <div
      className="flex w-1/2 min-w-0 items-center"
      data-filter-kind="number"
    >
      <span
        aria-hidden="true"
        className="shrink-0 pl-3 text-xs text-ui-body-muted"
      >
        {prefix}
      </span>
      <Input
        aria-label={label}
        className="h-full min-w-0 flex-1 rounded-none border-0 bg-transparent px-2 text-ui-body shadow-none [appearance:textfield] focus-visible:ring-0 focus-visible:ring-offset-0 disabled:bg-ui-surface-soft [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
        type="number"
        value={values[name]}
        placeholder="不限"
        disabled={disabled}
        onChange={(event) => setValue(name, event.target.value)}
      />
    </div>
  );

  return (
    <div
      data-range-control
      className="flex h-10 w-full overflow-hidden rounded-ui-md border border-ui-border bg-ui-canvas transition-colors focus-within:border-ui-foreground focus-within:ring-2 focus-within:ring-ui-foreground focus-within:ring-offset-2 focus-within:ring-offset-ui-canvas"
    >
      {renderEndpoint(config.startName, config.startLabel, config.startPrefix)}
      <span aria-hidden="true" className="my-2 w-px shrink-0 bg-ui-border" />
      {renderEndpoint(config.endName, config.endLabel, config.endPrefix)}
    </div>
  );
}

export function CompanyListFilterBar({
  values,
  options,
  optionsState,
  appliedCount,
  isSubmitting,
  onChange,
  onSubmit,
  onReset,
}: CompanyListFilterBarProps) {
  const remoteOptionState = (items: readonly string[] | undefined) =>
    optionsState === 'ready' && !items?.length ? 'empty' : optionsState;
  const fields: ReadonlyArray<FilterField<FilterValues>> = [
    {
      name: 'keyword',
      kind: 'text',
      label: '关键词',
      placeholder: '公司名 / 域名搜索',
    },
    {
      name: 'countries',
      kind: 'multiSelect',
      label: '国家',
      width: 'small',
      placeholder: '不限',
      searchPlaceholder: '搜索国家',
      options: toOptions(options?.countries ?? [], countryZh),
      optionState: remoteOptionState(options?.countries),
    },
    {
      name: 'sub_industries',
      kind: 'multiSelect',
      label: '细分行业',
      placeholder: '不限',
      searchPlaceholder: '搜索细分行业',
      options: toOptions(options?.sub_industries ?? []),
      optionState: remoteOptionState(options?.sub_industries),
    },
    {
      name: 'product_tags',
      kind: 'multiSelect',
      label: '产品标签',
      placeholder: '不限',
      searchPlaceholder: '搜索产品标签',
      options: toOptions(options?.product_tags ?? []),
      optionState: remoteOptionState(options?.product_tags),
    },
    {
      name: 'collection_type',
      kind: 'select',
      label: '采集类型',
      width: 'small',
      placeholder: '不限',
      options: [
        { value: 'keyword', label: '关键词采集' },
        { value: 'reverse', label: '精准反推' },
        { value: 'manual', label: '手工录入' },
        { value: 'unknown', label: '来源待确认' },
      ],
    },
    {
      name: 'business_status',
      kind: 'select',
      label: '群组状态',
      width: 'small',
      placeholder: '不限',
      options: [
        { value: 'not_new', label: '已入群' },
        { value: 'new', label: '未入群' },
      ],
    },
    {
      name: 'grades',
      kind: 'multiSelect',
      label: '大模型评级',
      width: 'small',
      placeholder: '不限',
      searchPlaceholder: '搜索大模型评级',
      options: toOptions(options?.grades ?? []),
      optionState: remoteOptionState(options?.grades),
    },
    {
      name: 'system_grades',
      kind: 'multiSelect',
      label: '模板评级',
      width: 'small',
      placeholder: '不限',
      searchPlaceholder: '搜索模板评级',
      options: toOptions(SYSTEM_GRADES),
    },
    ...RANGE_FILTERS.map<FilterField<FilterValues>>((config) => ({
      name: config.startName,
      kind: 'custom',
      label: config.label,
      width: { custom: 256 },
      advanced: true,
      render: (context) => (
        <RangeFilterControl config={config} {...context} />
      ),
    })),
  ];

  return (
    <FilterBar
      values={values}
      fields={fields}
      onChange={onChange}
      onSubmit={onSubmit}
      onReset={onReset}
      isSubmitting={isSubmitting}
      appliedCount={appliedCount}
      layout="compact"
      collapseAdvanced={false}
      optionStateMode="inspectable"
      actionsPlacement="inline"
    />
  );
}

'use client';

import type { FilterField } from '@shared/ui';
import { FilterBar } from '@shared/ui';
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

const toOptions = (items: readonly string[], label: (value: string) => string = (value) => value) =>
  items.map((value) => ({ value, label: label(value) }));

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
    { name: 'keyword', kind: 'text', label: '关键词', placeholder: '公司名 / 域名搜索' },
    {
      name: 'countries',
      kind: 'multiSelect',
      label: '国家',
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
      placeholder: '不限',
      searchPlaceholder: '搜索大模型评级',
      options: toOptions(options?.grades ?? []),
      optionState: remoteOptionState(options?.grades),
    },
    {
      name: 'system_grades',
      kind: 'multiSelect',
      label: '模板评级',
      placeholder: '不限',
      searchPlaceholder: '搜索模板评级',
      options: toOptions(SYSTEM_GRADES),
    },
    {
      name: 'trade_amount_min',
      kind: 'number',
      label: '最低进口额',
      placeholder: '不限',
      advanced: true,
    },
    {
      name: 'trade_amount_max',
      kind: 'number',
      label: '最高进口额',
      placeholder: '不限',
      advanced: true,
    },
    {
      name: 'trade_count_min',
      kind: 'number',
      label: '最低进口次数',
      placeholder: '不限',
      advanced: true,
    },
    {
      name: 'trade_count_max',
      kind: 'number',
      label: '最高进口次数',
      placeholder: '不限',
      advanced: true,
    },
    {
      name: 'contact_count_min',
      kind: 'number',
      label: '最少联系人',
      placeholder: '不限',
      advanced: true,
    },
    {
      name: 'contact_count_max',
      kind: 'number',
      label: '最多联系人',
      placeholder: '不限',
      advanced: true,
    },
    {
      name: 'founded_year_from',
      kind: 'number',
      label: '成立年份起',
      placeholder: '不限',
      advanced: true,
    },
    {
      name: 'founded_year_to',
      kind: 'number',
      label: '成立年份止',
      placeholder: '不限',
      advanced: true,
    },
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
    />
  );
}

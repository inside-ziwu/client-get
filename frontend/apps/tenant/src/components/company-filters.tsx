'use client';

import type { CompanyListFilters } from '@shared/api';
import { Search, X } from 'lucide-react';
import { FormEvent, useState } from 'react';
import {
  Button, Card, CardContent, Input, MultiSelect,
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@shared/ui';

export type FilterValues = {
  keyword: string;
  countries: string[];
  sub_industries: string[];
  product_tags: string[];
  grade: string;
  trade_amount_min: string;
  trade_amount_max: string;
  trade_count_min: string;
  trade_count_max: string;
  contact_count_min: string;
  contact_count_max: string;
  founded_year_from: string;
  founded_year_to: string;
};

export const EMPTY_FILTERS: FilterValues = {
  keyword: '',
  countries: [],
  sub_industries: [],
  product_tags: [],
  grade: '',
  trade_amount_min: '',
  trade_amount_max: '',
  trade_count_min: '',
  trade_count_max: '',
  contact_count_min: '',
  contact_count_max: '',
  founded_year_from: '',
  founded_year_to: '',
};

export const COUNTRY_ZH: Record<string, string> = {
  'China': '中国', 'Hong Kong': '中国香港', 'Macau': '中国澳门', 'Taiwan': '中国台湾',
  'United States': '美国', 'United Kingdom': '英国', 'France': '法国', 'Germany': '德国',
  'Japan': '日本', 'South Korea': '韩国', 'India': '印度', 'Australia': '澳大利亚',
  'Canada': '加拿大', 'Singapore': '新加坡', 'Malaysia': '马来西亚', 'Thailand': '泰国',
  'Vietnam': '越南', 'Philippines': '菲律宾', 'Bangladesh': '孟加拉国', 'Mexico': '墨西哥',
  'Kuwait': '科威特', 'Aruba': '阿鲁巴', 'Bulgaria': '保加利亚', 'Czech Republic': '捷克',
  'Luxembourg': '卢森堡', '未公开': '未公开',
  CHN: '中国', HKG: '中国香港', MAC: '中国澳门', TWN: '中国台湾',
  USA: '美国', GBR: '英国', FRA: '法国', DEU: '德国',
  JPN: '日本', KOR: '韩国', IND: '印度', AUS: '澳大利亚',
  CAN: '加拿大', SGP: '新加坡', MYS: '马来西亚', THA: '泰国',
  VNM: '越南', PHL: '菲律宾', BGD: '孟加拉国', MEX: '墨西哥',
  KWT: '科威特', ABW: '阿鲁巴', BGR: '保加利亚', CZE: '捷克',
  LUX: '卢森堡', UNK: '未知',
};

export function countryZh(v: string | null | undefined) {
  if (!v) return '-';
  return COUNTRY_ZH[v] ?? v;
}

export function buildParams(f: FilterValues, page: number, pageSize: number): CompanyListFilters {
  const p: CompanyListFilters = { page, page_size: pageSize };
  if (f.keyword.trim()) p.keyword = f.keyword.trim();
  if (f.grade) p.grade = f.grade;
  if (f.countries.length) p['countries[]'] = f.countries;
  if (f.sub_industries.length) p['sub_industries[]'] = f.sub_industries;
  if (f.product_tags.length) p['product_tags[]'] = f.product_tags;
  if (f.trade_amount_min) p.trade_amount_min = Number(f.trade_amount_min);
  if (f.trade_amount_max) p.trade_amount_max = Number(f.trade_amount_max);
  if (f.trade_count_min) p.trade_count_min = Number(f.trade_count_min);
  if (f.trade_count_max) p.trade_count_max = Number(f.trade_count_max);
  if (f.contact_count_min) p.contact_count_min = Number(f.contact_count_min);
  if (f.contact_count_max) p.contact_count_max = Number(f.contact_count_max);
  if (f.founded_year_from) p.founded_year_from = Number(f.founded_year_from);
  if (f.founded_year_to) p.founded_year_to = Number(f.founded_year_to);
  return p;
}

interface FiltersOptions {
  countries?: string[];
  sub_industries?: string[];
  product_tags?: string[];
  grades?: string[];
}

interface CompanyFiltersProps {
  filtersOptions?: FiltersOptions;
  onApply: (filters: FilterValues) => void;
  onReset?: () => void;
  compact?: boolean;
}

export default function CompanyFilters({ filtersOptions: fo, onApply, onReset, compact }: CompanyFiltersProps) {
  const [filters, setFilters] = useState<FilterValues>(EMPTY_FILTERS);

  const countryOpts = (fo?.countries ?? []).map((v: string) => ({ label: countryZh(v), value: v }));
  const subIndustryOpts = (fo?.sub_industries ?? []).map((v: string) => ({ label: v, value: v }));
  const productTagOpts = (fo?.product_tags ?? []).map((v: string) => ({ label: v, value: v }));
  const gradeOpts = (fo?.grades ?? []) as string[];

  const onSearch = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    onApply(filters);
  };

  const handleReset = () => {
    setFilters(EMPTY_FILTERS);
    onApply(EMPTY_FILTERS);
    onReset?.();
  };

  const wrapper = compact ? 'space-y-3' : undefined;

  return (
    <Card className={compact ? 'border-0 shadow-none' : undefined}>
      <CardContent className={compact ? 'p-0' : 'p-4'}>
        <form className="space-y-3" onSubmit={onSearch}>
          <div className={wrapper ?? "grid gap-3 lg:grid-cols-5"}>
            <Input
              placeholder="公司名 / 域名搜索"
              value={filters.keyword}
              onChange={(e) => setFilters((f) => ({ ...f, keyword: e.target.value }))}
            />
            <MultiSelect
              value={filters.countries}
              onChange={(v) => setFilters((f) => ({ ...f, countries: v }))}
              options={countryOpts}
              placeholder="国家"
              allowCreate={false}
            />
            <MultiSelect
              value={filters.sub_industries}
              onChange={(v) => setFilters((f) => ({ ...f, sub_industries: v }))}
              options={subIndustryOpts}
              placeholder="细分行业"
              allowCreate={false}
            />
            <MultiSelect
              value={filters.product_tags}
              onChange={(v) => setFilters((f) => ({ ...f, product_tags: v }))}
              options={productTagOpts}
              placeholder="产品标签"
              allowCreate={false}
            />
            <Select
              value={filters.grade || 'all'}
              onValueChange={(v) => setFilters((f) => ({ ...f, grade: v === 'all' ? '' : v }))}
            >
              <SelectTrigger><SelectValue placeholder="评级（不限）" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">评级（不限）</SelectItem>
                {gradeOpts.map((g) => <SelectItem key={g} value={g}>{g}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div className="grid gap-3 lg:grid-cols-[1fr_1fr_1fr_1fr_auto]">
            <div className="flex items-center gap-1">
              <Input type="number" placeholder="进口额(起)" value={filters.trade_amount_min}
                onChange={(e) => setFilters((f) => ({ ...f, trade_amount_min: e.target.value }))} />
              <span className="text-muted-foreground">-</span>
              <Input type="number" placeholder="进口额(止)" value={filters.trade_amount_max}
                onChange={(e) => setFilters((f) => ({ ...f, trade_amount_max: e.target.value }))} />
            </div>
            <div className="flex items-center gap-1">
              <Input type="number" placeholder="进口次数(起)" value={filters.trade_count_min}
                onChange={(e) => setFilters((f) => ({ ...f, trade_count_min: e.target.value }))} />
              <span className="text-muted-foreground">-</span>
              <Input type="number" placeholder="进口次数(止)" value={filters.trade_count_max}
                onChange={(e) => setFilters((f) => ({ ...f, trade_count_max: e.target.value }))} />
            </div>
            <div className="flex items-center gap-1">
              <Input type="number" placeholder="联系人(起)" value={filters.contact_count_min}
                onChange={(e) => setFilters((f) => ({ ...f, contact_count_min: e.target.value }))} />
              <span className="text-muted-foreground">-</span>
              <Input type="number" placeholder="联系人(止)" value={filters.contact_count_max}
                onChange={(e) => setFilters((f) => ({ ...f, contact_count_max: e.target.value }))} />
            </div>
            <div className="flex items-center gap-1">
              <Input type="number" placeholder="成立年(起)" value={filters.founded_year_from}
                onChange={(e) => setFilters((f) => ({ ...f, founded_year_from: e.target.value }))} />
              <span className="text-muted-foreground">-</span>
              <Input type="number" placeholder="成立年(止)" value={filters.founded_year_to}
                onChange={(e) => setFilters((f) => ({ ...f, founded_year_to: e.target.value }))} />
            </div>
            <div className="flex items-center gap-2">
              <Button type="submit" size="sm"><Search className="mr-1 h-3.5 w-3.5" />查询</Button>
              <Button type="button" variant="outline" size="sm" onClick={handleReset}><X className="mr-1 h-3.5 w-3.5" />重置</Button>
            </div>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

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
  'Luxembourg': '卢森堡', 'Turkey': '土耳其', 'Russia': '俄罗斯', 'Russian Federation': '俄罗斯',
  'Indonesia': '印度尼西亚', 'Pakistan': '巴基斯坦', 'Sri Lanka': '斯里兰卡',
  'United Arab Emirates': '阿联酋', 'Saudi Arabia': '沙特阿拉伯', 'Israel': '以色列',
  'Netherlands': '荷兰', 'Belgium': '比利时', 'Italy': '意大利', 'Spain': '西班牙',
  'Switzerland': '瑞士', 'Sweden': '瑞典', 'Norway': '挪威', 'Denmark': '丹麦',
  'Finland': '芬兰', 'Poland': '波兰', 'Austria': '奥地利', 'Ireland': '爱尔兰',
  'Portugal': '葡萄牙', 'Greece': '希腊', 'Romania': '罗马尼亚', 'Hungary': '匈牙利',
  'South Africa': '南非', 'Brazil': '巴西', 'Argentina': '阿根廷', 'Chile': '智利',
  'Colombia': '哥伦比亚', 'Peru': '秘鲁', 'New Zealand': '新西兰', '未公开': '未公开',
  CHN: '中国', HKG: '中国香港', MAC: '中国澳门', TWN: '中国台湾',
  USA: '美国', GBR: '英国', FRA: '法国', DEU: '德国',
  JPN: '日本', KOR: '韩国', IND: '印度', AUS: '澳大利亚',
  CAN: '加拿大', SGP: '新加坡', MYS: '马来西亚', THA: '泰国',
  VNM: '越南', PHL: '菲律宾', BGD: '孟加拉国', MEX: '墨西哥',
  KWT: '科威特', ABW: '阿鲁巴', BGR: '保加利亚', CZE: '捷克',
  LUX: '卢森堡', TUR: '土耳其', RUS: '俄罗斯', IDN: '印度尼西亚',
  PAK: '巴基斯坦', LKA: '斯里兰卡', ARE: '阿联酋', SAU: '沙特阿拉伯',
  ISR: '以色列', NLD: '荷兰', BEL: '比利时', ITA: '意大利', ESP: '西班牙',
  CHE: '瑞士', SWE: '瑞典', NOR: '挪威', DNK: '丹麦', FIN: '芬兰',
  POL: '波兰', AUT: '奥地利', IRL: '爱尔兰', PRT: '葡萄牙', GRC: '希腊',
  ROU: '罗马尼亚', HUN: '匈牙利', ZAF: '南非', BRA: '巴西',
  ARG: '阿根廷', CHL: '智利', COL: '哥伦比亚', PER: '秘鲁',
  NZL: '新西兰', UNK: '未公开',
};

const ISO3_TO_ISO2: Record<string, string> = {
  ABW: 'AW', AFG: 'AF', AGO: 'AO', AIA: 'AI', ALA: 'AX', ALB: 'AL', AND: 'AD', ARE: 'AE',
  ARG: 'AR', ARM: 'AM', ASM: 'AS', ATA: 'AQ', ATF: 'TF', ATG: 'AG', AUS: 'AU', AUT: 'AT',
  AZE: 'AZ', BDI: 'BI', BEL: 'BE', BEN: 'BJ', BES: 'BQ', BFA: 'BF', BGD: 'BD', BGR: 'BG',
  BHR: 'BH', BHS: 'BS', BIH: 'BA', BLM: 'BL', BLR: 'BY', BLZ: 'BZ', BMU: 'BM', BOL: 'BO',
  BRA: 'BR', BRB: 'BB', BRN: 'BN', BTN: 'BT', BVT: 'BV', BWA: 'BW', CAF: 'CF', CAN: 'CA',
  CCK: 'CC', CHE: 'CH', CHL: 'CL', CHN: 'CN', CIV: 'CI', CMR: 'CM', COD: 'CD', COG: 'CG',
  COK: 'CK', COL: 'CO', COM: 'KM', CPV: 'CV', CRI: 'CR', CUB: 'CU', CUW: 'CW', CXR: 'CX',
  CYM: 'KY', CYP: 'CY', CZE: 'CZ', DEU: 'DE', DJI: 'DJ', DMA: 'DM', DNK: 'DK', DOM: 'DO',
  DZA: 'DZ', ECU: 'EC', EGY: 'EG', ERI: 'ER', ESH: 'EH', ESP: 'ES', EST: 'EE', ETH: 'ET',
  FIN: 'FI', FJI: 'FJ', FLK: 'FK', FRA: 'FR', FRO: 'FO', FSM: 'FM', GAB: 'GA', GBR: 'GB',
  GEO: 'GE', GGY: 'GG', GHA: 'GH', GIB: 'GI', GIN: 'GN', GLP: 'GP', GMB: 'GM', GNB: 'GW',
  GNQ: 'GQ', GRC: 'GR', GRD: 'GD', GRL: 'GL', GTM: 'GT', GUF: 'GF', GUM: 'GU', GUY: 'GY',
  HKG: 'HK', HMD: 'HM', HND: 'HN', HRV: 'HR', HTI: 'HT', HUN: 'HU', IDN: 'ID', IMN: 'IM',
  IND: 'IN', IOT: 'IO', IRL: 'IE', IRN: 'IR', IRQ: 'IQ', ISL: 'IS', ISR: 'IL', ITA: 'IT',
  JAM: 'JM', JEY: 'JE', JOR: 'JO', JPN: 'JP', KAZ: 'KZ', KEN: 'KE', KGZ: 'KG', KHM: 'KH',
  KIR: 'KI', KNA: 'KN', KOR: 'KR', KWT: 'KW', LAO: 'LA', LBN: 'LB', LBR: 'LR', LBY: 'LY',
  LCA: 'LC', LIE: 'LI', LKA: 'LK', LSO: 'LS', LTU: 'LT', LUX: 'LU', LVA: 'LV', MAC: 'MO',
  MAF: 'MF', MAR: 'MA', MCO: 'MC', MDA: 'MD', MDG: 'MG', MDV: 'MV', MEX: 'MX', MHL: 'MH',
  MKD: 'MK', MLI: 'ML', MLT: 'MT', MMR: 'MM', MNE: 'ME', MNG: 'MN', MNP: 'MP', MOZ: 'MZ',
  MRT: 'MR', MSR: 'MS', MTQ: 'MQ', MUS: 'MU', MWI: 'MW', MYS: 'MY', MYT: 'YT', NAM: 'NA',
  NCL: 'NC', NER: 'NE', NFK: 'NF', NGA: 'NG', NIC: 'NI', NIU: 'NU', NLD: 'NL', NOR: 'NO',
  NPL: 'NP', NRU: 'NR', NZL: 'NZ', OMN: 'OM', PAK: 'PK', PAN: 'PA', PCN: 'PN', PER: 'PE',
  PHL: 'PH', PLW: 'PW', PNG: 'PG', POL: 'PL', PRI: 'PR', PRK: 'KP', PRT: 'PT', PRY: 'PY',
  PSE: 'PS', PYF: 'PF', QAT: 'QA', REU: 'RE', ROU: 'RO', RUS: 'RU', RWA: 'RW', SAU: 'SA',
  SDN: 'SD', SEN: 'SN', SGP: 'SG', SGS: 'GS', SHN: 'SH', SJM: 'SJ', SLB: 'SB', SLE: 'SL',
  SLV: 'SV', SMR: 'SM', SOM: 'SO', SPM: 'PM', SRB: 'RS', SSD: 'SS', STP: 'ST', SUR: 'SR',
  SVK: 'SK', SVN: 'SI', SWE: 'SE', SWZ: 'SZ', SXM: 'SX', SYC: 'SC', SYR: 'SY', TCA: 'TC',
  TCD: 'TD', TGO: 'TG', THA: 'TH', TJK: 'TJ', TKL: 'TK', TKM: 'TM', TLS: 'TL', TON: 'TO',
  TTO: 'TT', TUN: 'TN', TUR: 'TR', TUV: 'TV', TWN: 'TW', TZA: 'TZ', UGA: 'UG', UKR: 'UA',
  UMI: 'UM', URY: 'UY', USA: 'US', UZB: 'UZ', VAT: 'VA', VCT: 'VC', VEN: 'VE', VGB: 'VG',
  VIR: 'VI', VNM: 'VN', VUT: 'VU', WLF: 'WF', WSM: 'WS', YEM: 'YE', ZAF: 'ZA', ZMB: 'ZM',
  ZWE: 'ZW',
};

const regionNames = new Intl.DisplayNames(['zh-CN'], { type: 'region' });

export function countryZh(v: string | null | undefined) {
  if (!v) return '-';
  const value = v.trim();
  if (!value) return '-';
  if (COUNTRY_ZH[value]) return COUNTRY_ZH[value];
  if (/[\u4e00-\u9fa5]/.test(value)) return value;
  const upperValue = value.toUpperCase();
  if (COUNTRY_ZH[upperValue]) return COUNTRY_ZH[upperValue];
  const regionCode = ISO3_TO_ISO2[upperValue] ?? (/^[A-Z]{2}$/.test(upperValue) ? upperValue : undefined);
  if (regionCode) return regionNames.of(regionCode) ?? value;
  return value;
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

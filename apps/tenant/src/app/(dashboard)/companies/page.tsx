'use client';

import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { Button, DescriptionList, MultiSelect, RatingTag, Sheet, SheetContent, SheetDescription, SheetTitle } from '@shared/ui';
import { tenantApi } from '@/lib/api';
import { DataTable, PageHeader, SearchBar } from '@/components/pages/page-kit';

type Company = Awaited<ReturnType<typeof tenantApi.companies.list>>['data']['data'][number];

export default function CompaniesPage() {
  const [keyword, setKeyword] = useState('');
  const [countries, setCountries] = useState<string[]>([]);
  const [selected, setSelected] = useState<Company | null>(null);
  const filtersQuery = useQuery({
    queryKey: ['tenant', 'companies', 'filters'],
    queryFn: async () => (await tenantApi.companies.filters()).data.data,
  });
  const companiesQuery = useQuery({
    queryKey: ['tenant', 'companies', keyword, countries],
    queryFn: async () =>
      (await tenantApi.companies.list({ keyword, 'countries[]': countries, limit: 50 })).data.data,
  });

  const countryOptions = (filtersQuery.data?.countries ?? []).map((item) => ({ label: item, value: item }));

  return (
    <div className="tenant-page">
      <PageHeader title="公司列表" description="筛选、查看和处理租户公司数据" />
      <div className="grid gap-3 lg:grid-cols-[1fr_320px]">
        <SearchBar value={keyword} onChange={setKeyword} placeholder="公司名、域名、行业" />
        <MultiSelect value={countries} onChange={setCountries} options={countryOptions} placeholder="国家/地区" />
      </div>
      <DataTable
        rows={companiesQuery.data}
        columns={[
          { key: 'name', title: '公司', render: (row) => <div><div className="font-medium">{row.name}</div><div className="text-xs text-muted-foreground">{row.domain}</div></div> },
          { key: 'country', title: '国家', render: (row) => row.country ?? '-' },
          { key: 'industry', title: '行业', render: (row) => row.industry ?? '-' },
          { key: 'grade', title: '评级', render: (row) => (row.grade ? <RatingTag grade={row.grade} /> : '-') },
          { key: 'score', title: '分数', render: (row) => row.total_score ?? '-' },
          { key: 'action', title: '操作', render: (row) => <Button size="sm" variant="outline" onClick={() => setSelected(row)}>详情</Button> },
        ]}
      />
      <Sheet open={Boolean(selected)} onOpenChange={(open: boolean) => !open && setSelected(null)}>
        <SheetContent>
          <div className="p-5">
            <SheetTitle>{selected?.name}</SheetTitle>
            <SheetDescription>{selected?.domain ?? '公司详情'}</SheetDescription>
            {selected ? (
              <DescriptionList
                className="mt-5"
                items={[
                  { label: '英文名', value: selected.name_en },
                  { label: '行业', value: selected.industry },
                  { label: '国家', value: selected.country },
                  { label: '员工规模', value: selected.employee_scale },
                  { label: '联系人', value: selected.contacts_count },
                  { label: '备注', value: selected.notes },
                ]}
              />
            ) : null}
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
}

'use client';

import type { Country, TimeSegment } from '@shared/api';
import { queryKeys } from '@shared/api';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowLeft, Plus, Save } from 'lucide-react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { FormEvent, useMemo, useState } from 'react';
import { toast } from 'sonner';
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Checkbox,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
  Input,
  Label,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@shared/ui';
import { adminApi } from '@/lib/api';
import { SegmentBadges, TimeSegmentsEditor, WeekdayBadges, WeekdayPicker, validateSegments } from '../../components';

type RuleForm = {
  name: string;
  work_days: number[];
  time_segments: TimeSegment[];
};

export default function RuleSetDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<RuleForm>({ name: '', work_days: [], time_segments: [] });
  const [assignOpen, setAssignOpen] = useState(false);
  const [countrySearch, setCountrySearch] = useState('');
  const [selectedCountries, setSelectedCountries] = useState<string[]>([]);

  const detailQuery = useQuery({
    queryKey: queryKeys.admin.workSchedule.ruleSet(id),
    queryFn: async () => (await adminApi.workSchedule.getRuleSet(id)).data.data,
  });
  const countriesQuery = useQuery({
    queryKey: queryKeys.admin.workSchedule.countries(),
    queryFn: async () => (await adminApi.workSchedule.listCountries()).data.data,
  });

  const countries = countriesQuery.data ?? [];
  const linkedCountrySet = useMemo(
    () => new Set((detailQuery.data?.countries ?? []).map((country) => country.iso3)),
    [detailQuery.data?.countries],
  );
  const filteredCountries = useMemo(() => {
    const query = countrySearch.trim().toLowerCase();
    return countries.filter((country) => {
      if (linkedCountrySet.has(country.iso3)) return false;
      if (!query) return true;
      return `${country.iso3} ${country.name_zh} ${country.name_en}`.toLowerCase().includes(query);
    });
  }, [countries, countrySearch, linkedCountrySet]);
  const selectedCountrySet = useMemo(() => new Set(selectedCountries), [selectedCountries]);
  const selectedAssignedElsewhere = useMemo(
    () => countries.filter((country) => selectedCountrySet.has(country.iso3) && country.rule_set_id && country.rule_set_id !== id),
    [countries, id, selectedCountrySet],
  );

  const invalidate = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: queryKeys.admin.workSchedule.all() }),
      queryClient.invalidateQueries({ queryKey: queryKeys.admin.workSchedule.ruleSet(id) }),
    ]);
  };

  const updateMutation = useMutation({
    mutationFn: (payload: RuleForm) => adminApi.workSchedule.updateRuleSet(id, payload),
    onSuccess: async () => {
      toast.success('规则集已保存');
      setEditing(false);
      await invalidate();
    },
    onError: () => toast.error('保存失败'),
  });

  const assignMutation = useMutation({
    mutationFn: (iso3List: string[]) => adminApi.workSchedule.assignCountries(id, iso3List),
    onSuccess: async () => {
      toast.success('国家已关联');
      setAssignOpen(false);
      setSelectedCountries([]);
      setCountrySearch('');
      await invalidate();
    },
    onError: () => toast.error('关联国家失败'),
  });

  const removeMutation = useMutation({
    mutationFn: (iso3: string) => adminApi.workSchedule.removeCountry(id, iso3),
    onSuccess: async () => {
      toast.success('国家已移除');
      await invalidate();
    },
    onError: () => toast.error('移除国家失败'),
  });

  const startEdit = () => {
    const rule = detailQuery.data;
    if (!rule) return;
    setForm({ name: rule.name, work_days: rule.work_days, time_segments: rule.time_segments });
    setEditing(true);
  };

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const error = validateRule(form);
    if (error) {
      toast.error(error);
      return;
    }
    updateMutation.mutate(form);
  };
  const toggleCountry = (iso3: string, checked: boolean) => {
    setSelectedCountries((current) => (
      checked ? [...new Set([...current, iso3])] : current.filter((item) => item !== iso3)
    ));
  };
  const selectFilteredCountries = () => {
    setSelectedCountries((current) => [...new Set([...current, ...filteredCountries.map((country) => country.iso3)])]);
  };
  const clearSelectedCountries = () => {
    setSelectedCountries([]);
  };
  const setAssignDialogOpen = (open: boolean) => {
    setAssignOpen(open);
    if (!open) {
      setCountrySearch('');
      setSelectedCountries([]);
    }
  };

  if (detailQuery.isLoading) {
    return <div className="admin-page text-sm text-muted-foreground">加载中...</div>;
  }
  if (detailQuery.isError || !detailQuery.data) {
    return <div className="admin-page text-sm text-destructive">规则集加载失败</div>;
  }

  const rule = detailQuery.data;
  const segmentError = validateSegments(form.time_segments);

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <div className="space-y-2">
          <Button asChild variant="link">
            <Link href="/work-schedule">
              <ArrowLeft className="h-4 w-4" />
              返回发送时间配置
            </Link>
          </Button>
          <h1 className="admin-page-title">{rule.name}</h1>
        </div>
        {!editing && <Button onClick={startEdit}>编辑</Button>}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>规则信息</CardTitle>
        </CardHeader>
        <CardContent>
          {editing ? (
            <form className="space-y-4" onSubmit={submit}>
              <div className="space-y-2">
                <Label htmlFor="rule-name">名称</Label>
                <Input id="rule-name" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} />
              </div>
              <div className="space-y-2">
                <Label>工作日</Label>
                <WeekdayPicker value={form.work_days} onChange={(workDays) => setForm({ ...form, work_days: workDays })} />
              </div>
              <div className="space-y-2">
                <Label>时段</Label>
                <TimeSegmentsEditor
                  value={form.time_segments}
                  onChange={(segments) => setForm({ ...form, time_segments: segments })}
                  error={segmentError}
                />
              </div>
              <div className="flex justify-end gap-2">
                <Button type="button" variant="outline" onClick={() => setEditing(false)}>取消</Button>
                <Button type="submit" disabled={updateMutation.isPending || !!segmentError}>
                  <Save className="h-4 w-4" />
                  保存
                </Button>
              </div>
            </form>
          ) : (
            <div className="grid gap-4 md:grid-cols-3">
              <div className="space-y-2">
                <Label>名称</Label>
                <div className="text-sm">{rule.name}</div>
              </div>
              <div className="space-y-2">
                <Label>工作日</Label>
                <WeekdayBadges days={rule.work_days} />
              </div>
              <div className="space-y-2">
                <Label>时段</Label>
                <SegmentBadges segments={rule.time_segments} />
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0">
          <CardTitle>关联国家</CardTitle>
          <Button type="button" onClick={() => setAssignDialogOpen(true)}>
            <Plus className="h-4 w-4" />
            添加国家
          </Button>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>国家</TableHead>
                <TableHead>ISO3</TableHead>
                <TableHead>时区</TableHead>
                <TableHead className="w-24 text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(rule.countries ?? []).length === 0 ? (
                <TableRow>
                  <TableCell colSpan={4} className="py-8 text-center text-sm text-muted-foreground">
                    暂无关联国家
                  </TableCell>
                </TableRow>
              ) : (
                (rule.countries ?? []).map((country: Country) => (
                  <TableRow key={country.iso3}>
                    <TableCell>
                      <div className="font-medium">{country.name_zh}</div>
                      <div className="text-xs text-muted-foreground">{country.name_en}</div>
                    </TableCell>
                    <TableCell><Badge variant="outline">{country.iso3}</Badge></TableCell>
                    <TableCell>{country.timezone}</TableCell>
                    <TableCell className="text-right">
                      <Button variant="ghost" size="sm" className="text-destructive" onClick={() => removeMutation.mutate(country.iso3)}>
                        删除
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Dialog open={assignOpen} onOpenChange={setAssignDialogOpen}>
        <DialogContent className="sm:max-w-[860px]">
          <DialogTitle>添加关联国家</DialogTitle>
          <DialogDescription>搜索并批量选择需要使用当前规则集的国家。</DialogDescription>
          <div className="space-y-3">
            <Input placeholder="搜索国家名、英文名或 ISO3" value={countrySearch} onChange={(event) => setCountrySearch(event.target.value)} />
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="text-sm text-muted-foreground">
                可选 {filteredCountries.length} 个，已选 {selectedCountries.length} 个
              </div>
              <div className="flex gap-2">
                <Button type="button" variant="outline" size="sm" disabled={!filteredCountries.length} onClick={selectFilteredCountries}>
                  全选当前结果
                </Button>
                <Button type="button" variant="outline" size="sm" disabled={!selectedCountries.length} onClick={clearSelectedCountries}>
                  清空
                </Button>
                <Button
                  type="button"
                  size="sm"
                  disabled={!selectedCountries.length || assignMutation.isPending}
                  onClick={() => assignMutation.mutate(selectedCountries)}
                >
                  <Plus className="h-4 w-4" />
                  批量添加
                </Button>
              </div>
            </div>
            <div className="max-h-[420px] overflow-y-auto rounded-md border border-border">
              {countriesQuery.isLoading ? (
                <div className="py-8 text-center text-sm text-muted-foreground">国家加载中...</div>
              ) : filteredCountries.length === 0 ? (
                <div className="py-8 text-center text-sm text-muted-foreground">没有可添加的国家</div>
              ) : (
                <div className="divide-y divide-border">
                  {filteredCountries.map((country) => (
                    <label key={country.iso3} className="flex cursor-pointer items-center gap-3 px-3 py-2 hover:bg-muted/50">
                      <Checkbox
                        checked={selectedCountrySet.has(country.iso3)}
                        onCheckedChange={(checked) => toggleCountry(country.iso3, checked === true)}
                      />
                      <span className="min-w-0 flex-1">
                        <span className="font-medium">{country.name_zh} / {country.iso3}</span>
                        <span className="ml-2 text-xs text-muted-foreground">{country.name_en}</span>
                      </span>
                      {country.rule_set_id && country.rule_set_id !== id ? (
                        <Badge variant="outline">将从 {country.rule_set_name} 移入</Badge>
                      ) : null}
                    </label>
                  ))}
                </div>
              )}
            </div>
            {selectedAssignedElsewhere.length > 0 && (
              <p className="text-sm text-amber-600">
                已选 {selectedAssignedElsewhere.length} 个国家当前属于其他规则集，批量添加后会移动到当前规则集。
              </p>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function validateRule(form: RuleForm) {
  if (!form.name.trim()) return '请填写规则集名称';
  if (!form.work_days.length) return '请选择至少一个工作日';
  if (!form.time_segments.length) return '请添加至少一个时段';
  return validateSegments(form.time_segments);
}

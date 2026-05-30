'use client';

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
  Input,
  Label,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@shared/ui';
import { adminApi } from '@/lib/api';

const COMMON_TIMEZONES = [
  'UTC',
  'Asia/Shanghai',
  'Asia/Tokyo',
  'Asia/Seoul',
  'Asia/Singapore',
  'Asia/Kolkata',
  'Europe/London',
  'Europe/Berlin',
  'Europe/Paris',
  'America/New_York',
  'America/Chicago',
  'America/Los_Angeles',
  'Australia/Sydney',
];

export default function CountryDetailPage() {
  const params = useParams<{ iso3: string }>();
  const iso3 = params.iso3.toUpperCase();
  const queryClient = useQueryClient();
  const holidayYear = new Date().getFullYear();
  const [editing, setEditing] = useState(false);
  const [timezone, setTimezone] = useState('');
  const [ruleSetId, setRuleSetId] = useState('none');
  const [holidayDate, setHolidayDate] = useState('');
  const [holidayName, setHolidayName] = useState('');

  const countryQuery = useQuery({
    queryKey: queryKeys.admin.workSchedule.country(iso3),
    queryFn: async () => (await adminApi.workSchedule.getCountry(iso3)).data.data,
  });
  const ruleSetsQuery = useQuery({
    queryKey: queryKeys.admin.workSchedule.ruleSets(),
    queryFn: async () => (await adminApi.workSchedule.listRuleSets()).data.data,
  });
  const holidaysQuery = useQuery({
    queryKey: queryKeys.admin.workSchedule.holidays(iso3, holidayYear),
    queryFn: async () => (await adminApi.workSchedule.listHolidays(iso3, holidayYear)).data.data,
  });

  const timezoneOptions = useMemo(() => {
    const set = new Set(COMMON_TIMEZONES);
    if (countryQuery.data?.timezone) set.add(countryQuery.data.timezone);
    return [...set].sort();
  }, [countryQuery.data?.timezone]);

  const invalidate = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: queryKeys.admin.workSchedule.all() }),
      queryClient.invalidateQueries({ queryKey: queryKeys.admin.workSchedule.country(iso3) }),
      queryClient.invalidateQueries({ queryKey: queryKeys.admin.workSchedule.holidays(iso3, holidayYear) }),
    ]);
  };

  const updateMutation = useMutation({
    mutationFn: () => adminApi.workSchedule.updateCountry(iso3, {
      timezone,
      rule_set_id: ruleSetId === 'none' ? null : ruleSetId,
    }),
    onSuccess: async () => {
      toast.success('国家配置已保存');
      setEditing(false);
      await invalidate();
    },
    onError: () => toast.error('保存失败'),
  });

  const createHolidayMutation = useMutation({
    mutationFn: () => adminApi.workSchedule.createHoliday(iso3, { date: holidayDate, name: holidayName || undefined }),
    onSuccess: async () => {
      toast.success('假日已添加');
      setHolidayDate('');
      setHolidayName('');
      await invalidate();
    },
    onError: () => toast.error('添加假日失败'),
  });

  const deleteHolidayMutation = useMutation({
    mutationFn: (id: string) => adminApi.workSchedule.deleteHoliday(iso3, id),
    onSuccess: async () => {
      toast.success('假日已删除');
      await invalidate();
    },
    onError: () => toast.error('删除假日失败'),
  });

  const startEdit = () => {
    const country = countryQuery.data;
    if (!country) return;
    setTimezone(country.timezone);
    setRuleSetId(country.rule_set_id ?? 'none');
    setEditing(true);
  };

  const submitCountry = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!timezone.trim()) {
      toast.error('请填写时区');
      return;
    }
    updateMutation.mutate();
  };

  const submitHoliday = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!holidayDate) {
      toast.error('请选择日期');
      return;
    }
    createHolidayMutation.mutate();
  };

  if (countryQuery.isLoading) {
    return <div className="admin-page text-sm text-muted-foreground">加载中...</div>;
  }
  if (countryQuery.isError || !countryQuery.data) {
    return <div className="admin-page text-sm text-destructive">国家加载失败</div>;
  }

  const country = countryQuery.data;
  const ruleSets = (ruleSetsQuery.data ?? []).filter((item) => !item.is_default);

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
          <div>
            <h1 className="admin-page-title">{country.name_zh}</h1>
            <p className="admin-page-description">{country.name_en} / {country.iso3}</p>
          </div>
        </div>
        {!editing && <Button onClick={startEdit}>编辑</Button>}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>国家配置</CardTitle>
        </CardHeader>
        <CardContent>
          {editing ? (
            <form className="space-y-4" onSubmit={submitCountry}>
              <div className="space-y-2">
                <Label htmlFor="timezone">主时区</Label>
                <Input
                  id="timezone"
                  list="timezone-options"
                  value={timezone}
                  onChange={(event) => setTimezone(event.target.value)}
                />
                <datalist id="timezone-options">
                  {timezoneOptions.map((item) => <option key={item} value={item} />)}
                </datalist>
              </div>
              <div className="space-y-2">
                <Label>关联规则集</Label>
                <Select value={ruleSetId} onValueChange={setRuleSetId}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">不关联，使用默认规则</SelectItem>
                    {ruleSets.map((item) => (
                      <SelectItem key={item.id} value={item.id}>{item.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex justify-end gap-2">
                <Button type="button" variant="outline" onClick={() => setEditing(false)}>取消</Button>
                <Button type="submit" disabled={updateMutation.isPending}>
                  <Save className="h-4 w-4" />
                  保存
                </Button>
              </div>
            </form>
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label className="block">主时区</Label>
                <div className="text-sm">{country.timezone}</div>
              </div>
              <div className="space-y-2">
                <Label className="block">关联规则集</Label>
                <div>
                  {country.rule_set_name ? <Badge variant="secondary">{country.rule_set_name}</Badge> : <Badge variant="outline">默认规则</Badge>}
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="space-y-4">
          <div className="flex items-center justify-between gap-3">
            <CardTitle>假日管理</CardTitle>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <form className="grid gap-2 md:grid-cols-[180px_1fr_100px]" onSubmit={submitHoliday}>
            <Input type="date" value={holidayDate} onChange={(event) => setHolidayDate(event.target.value)} />
            <Input placeholder="假日名称" value={holidayName} onChange={(event) => setHolidayName(event.target.value)} />
            <Button type="submit" disabled={createHolidayMutation.isPending}>
              <Plus className="h-4 w-4" />
              添加
            </Button>
          </form>
          {holidaysQuery.isLoading ? (
            <div className="py-8 text-center text-sm text-muted-foreground">加载中...</div>
          ) : (holidaysQuery.data ?? []).length === 0 ? (
            <div className="py-8 text-center text-sm text-muted-foreground">暂无假日数据</div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>日期</TableHead>
                  <TableHead>名称</TableHead>
                  <TableHead>来源</TableHead>
                  <TableHead className="w-24 text-right">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(holidaysQuery.data ?? []).map((holiday) => (
                  <TableRow key={holiday.id}>
                    <TableCell>{holiday.date}</TableCell>
                    <TableCell>{holiday.name || '-'}</TableCell>
                    <TableCell>
                      <Badge variant={holiday.source === 'seed' ? 'secondary' : 'outline'}>
                        {formatHolidaySource(holiday.source)}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right">
                      <Button variant="ghost" size="sm" className="text-destructive" onClick={() => deleteHolidayMutation.mutate(holiday.id)}>
                        删除
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function formatHolidaySource(source: string) {
  if (source === 'seed') return '系统';
  if (source === 'manual') return '手动添加';
  return '其他来源';
}

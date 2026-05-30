'use client';

import type { TimeSegment, WorkRuleSet } from '@shared/api';
import { queryKeys } from '@shared/api';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Plus, Search } from 'lucide-react';
import Link from 'next/link';
import { FormEvent, useMemo, useState } from 'react';
import { toast } from 'sonner';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogTitle,
  Badge,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
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
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@shared/ui';
import { adminApi } from '@/lib/api';
import { SegmentBadges, TimeSegmentsEditor, WeekdayBadges, WeekdayPicker, validateSegments } from './components';

type RuleForm = {
  name: string;
  work_days: number[];
  time_segments: TimeSegment[];
};

const DEFAULT_RULE_FORM: RuleForm = {
  name: '',
  work_days: [0, 1, 2, 3, 4],
  time_segments: [{ start: '09:00', end: '17:00' }],
};

export function WorkSchedulePage() {
  const queryClient = useQueryClient();
  const [createOpen, setCreateOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<WorkRuleSet | null>(null);
  const [ruleForm, setRuleForm] = useState<RuleForm>(DEFAULT_RULE_FORM);
  const [defaultEditing, setDefaultEditing] = useState(false);
  const [defaultForm, setDefaultForm] = useState<RuleForm>(DEFAULT_RULE_FORM);
  const [countrySearch, setCountrySearch] = useState('');
  const [countryFilter, setCountryFilter] = useState('all');

  const countryParams = useMemo(() => ({
    search: countrySearch || undefined,
    has_rule_set: countryFilter === 'all' ? undefined : countryFilter === 'assigned',
  }), [countryFilter, countrySearch]);

  const ruleSetsQuery = useQuery({
    queryKey: queryKeys.admin.workSchedule.ruleSets(),
    queryFn: async () => (await adminApi.workSchedule.listRuleSets()).data.data,
  });
  const defaultRuleQuery = useQuery({
    queryKey: queryKeys.admin.workSchedule.defaultRule(),
    queryFn: async () => (await adminApi.workSchedule.getDefaultRule()).data.data,
  });
  const countriesQuery = useQuery({
    queryKey: queryKeys.admin.workSchedule.countries(countryParams),
    queryFn: async () => (await adminApi.workSchedule.listCountries(countryParams)).data.data,
  });

  const invalidate = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: queryKeys.admin.workSchedule.all() }),
    ]);
  };

  const createMutation = useMutation({
    mutationFn: (payload: RuleForm) => adminApi.workSchedule.createRuleSet(payload),
    onSuccess: async () => {
      toast.success('规则集已创建');
      setCreateOpen(false);
      setRuleForm(DEFAULT_RULE_FORM);
      await invalidate();
    },
    onError: () => toast.error('创建规则集失败'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => adminApi.workSchedule.deleteRuleSet(id),
    onSuccess: async () => {
      toast.success('规则集已删除');
      setDeleteTarget(null);
      await invalidate();
    },
    onError: () => toast.error('删除规则集失败'),
  });

  const defaultMutation = useMutation({
    mutationFn: (payload: RuleForm) => adminApi.workSchedule.updateDefaultRule(payload),
    onSuccess: async () => {
      toast.success('默认规则已更新');
      setDefaultEditing(false);
      await invalidate();
    },
    onError: () => toast.error('默认规则更新失败'),
  });

  const submitCreate = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const error = validateRuleForm(ruleForm);
    if (error) {
      toast.error(error);
      return;
    }
    createMutation.mutate({ ...ruleForm, name: ruleForm.name.trim() });
  };

  const startDefaultEdit = () => {
    const rule = defaultRuleQuery.data;
    if (!rule) return;
    setDefaultForm({
      name: rule.name,
      work_days: rule.work_days,
      time_segments: rule.time_segments,
    });
    setDefaultEditing(true);
  };

  const submitDefault = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const error = validateRuleForm(defaultForm);
    if (error) {
      toast.error(error);
      return;
    }
    defaultMutation.mutate(defaultForm);
  };

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">发送时间配置</h1>
          <p className="admin-page-description">按国家时区、工作日、假日和时段控制邮件发送。</p>
        </div>
      </div>

      <Tabs defaultValue="rule-sets">
        <TabsList>
          <TabsTrigger value="rule-sets">规则集</TabsTrigger>
          <TabsTrigger value="countries">国家</TabsTrigger>
          <TabsTrigger value="default-rule">默认规则</TabsTrigger>
        </TabsList>

        <TabsContent value="rule-sets">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0">
              <CardTitle>工作规则集</CardTitle>
              <Button onClick={() => setCreateOpen(true)}>
                <Plus className="h-4 w-4" />
                新建
              </Button>
            </CardHeader>
            <CardContent>
              {ruleSetsQuery.isLoading ? (
                <div className="py-10 text-center text-sm text-muted-foreground">加载中...</div>
              ) : ruleSetsQuery.isError ? (
                <div className="py-10 text-center text-sm text-destructive">规则集加载失败</div>
              ) : (ruleSetsQuery.data ?? []).filter((item) => !item.is_default).length === 0 ? (
                <div className="py-10 text-center text-sm text-muted-foreground">尚未创建规则集</div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>名称</TableHead>
                      <TableHead>工作日</TableHead>
                      <TableHead>时段</TableHead>
                      <TableHead>关联国家</TableHead>
                      <TableHead className="w-32 text-right">操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {(ruleSetsQuery.data ?? []).filter((item) => !item.is_default).map((item) => (
                      <TableRow key={item.id}>
                        <TableCell className="font-medium">{item.name}</TableCell>
                        <TableCell><WeekdayBadges days={item.work_days} /></TableCell>
                        <TableCell><SegmentBadges segments={item.time_segments} /></TableCell>
                        <TableCell><Badge variant="outline">{item.country_count}</Badge></TableCell>
                        <TableCell>
                          <div className="flex justify-end gap-1">
                            <Button asChild variant="ghost" size="sm">
                              <Link href={`/work-schedule/rule-sets/${item.id}`}>
                                详情
                              </Link>
                            </Button>
                            <Button variant="ghost" size="sm" className="text-destructive" onClick={() => setDeleteTarget(item)}>
                              删除
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="countries">
          <Card>
            <CardHeader className="space-y-4">
              <div className="flex items-center justify-between gap-3">
                <CardTitle>国家时区</CardTitle>
              </div>
              <div className="grid gap-2 md:grid-cols-[1fr_180px]">
                <div className="relative">
                  <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                  <Input
                    className="pl-9"
                    placeholder="搜索国家名或 ISO3"
                    value={countrySearch}
                    onChange={(event) => setCountrySearch(event.target.value)}
                  />
                </div>
                <Select value={countryFilter} onValueChange={setCountryFilter}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">全部</SelectItem>
                    <SelectItem value="assigned">已关联规则集</SelectItem>
                    <SelectItem value="unassigned">未关联规则集</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardHeader>
            <CardContent>
              {countriesQuery.isLoading ? (
                <div className="py-10 text-center text-sm text-muted-foreground">加载中...</div>
              ) : countriesQuery.isError ? (
                <div className="py-10 text-center text-sm text-destructive">国家列表加载失败</div>
              ) : (
                <Table className="table-fixed">
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[38%]">国家</TableHead>
                      <TableHead className="w-20">ISO3</TableHead>
                      <TableHead className="w-[22%]">时区</TableHead>
                      <TableHead className="w-36">规则集</TableHead>
                      <TableHead className="w-20 text-center">假日</TableHead>
                      <TableHead className="w-24 text-right">操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {(countriesQuery.data ?? []).map((item) => (
                      <TableRow key={item.iso3}>
                        <TableCell>
                          <div className="font-medium">{item.name_zh}</div>
                          <div className="text-xs text-muted-foreground">{item.name_en}</div>
                        </TableCell>
                        <TableCell className="font-mono text-xs">{item.iso3}</TableCell>
                        <TableCell className="truncate">{item.timezone}</TableCell>
                        <TableCell>
                          {item.rule_set_name ? <Badge variant="secondary">{item.rule_set_name}</Badge> : <Badge variant="outline">默认规则</Badge>}
                        </TableCell>
                        <TableCell className="text-center">
                          <Badge variant={item.holiday_count ? 'secondary' : 'outline'}>{item.holiday_count}</Badge>
                        </TableCell>
                        <TableCell className="whitespace-nowrap text-right">
                          <Button asChild variant="ghost" size="sm" className="whitespace-nowrap">
                            <Link href={`/work-schedule/countries/${item.iso3}`}>
                              详情
                            </Link>
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="default-rule">
          <Card>
            <CardHeader className="flex flex-row items-start justify-between gap-3 space-y-0">
              <div className="space-y-1">
                <CardTitle>默认规则</CardTitle>
                <CardDescription>应用于未关联规则集的国家，按各国家主时区判断工作日、假日和时段。</CardDescription>
              </div>
              {!defaultEditing && (
                <Button onClick={startDefaultEdit}>
                  编辑
                </Button>
              )}
            </CardHeader>
            <CardContent>
              {defaultRuleQuery.isLoading ? (
                <div className="text-sm text-muted-foreground">加载中...</div>
              ) : defaultRuleQuery.isError ? (
                <div className="text-sm text-destructive">默认规则加载失败</div>
              ) : defaultEditing ? (
                <RuleFormView
                  form={defaultForm}
                  setForm={setDefaultForm}
                  saving={defaultMutation.isPending}
                  onSubmit={submitDefault}
                  onCancel={() => setDefaultEditing(false)}
                  submitText="保存默认规则"
                />
              ) : defaultRuleQuery.data ? (
                <div className="grid gap-4 md:grid-cols-3">
                  <div className="space-y-2">
                    <Label>时区</Label>
                    <div className="text-sm">各国家主时区</div>
                  </div>
                  <div className="space-y-2">
                    <Label>工作日</Label>
                    <WeekdayBadges days={defaultRuleQuery.data.work_days} />
                  </div>
                  <div className="space-y-2">
                    <Label>时段</Label>
                    <SegmentBadges segments={defaultRuleQuery.data.time_segments} />
                  </div>
                </div>
              ) : null}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="sm:max-w-[760px]">
          <DialogTitle>新建规则集</DialogTitle>
          <DialogDescription>同一规则集可关联多个国家，时段支持跨天。</DialogDescription>
          <RuleFormView
            form={ruleForm}
            setForm={setRuleForm}
            saving={createMutation.isPending}
            onSubmit={submitCreate}
            onCancel={() => setCreateOpen(false)}
            submitText="创建规则集"
          />
        </DialogContent>
      </Dialog>

      <AlertDialog open={!!deleteTarget} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <AlertDialogContent>
          <AlertDialogTitle>删除规则集</AlertDialogTitle>
          <AlertDialogDescription>
            删除后会自动解除 {deleteTarget?.country_count ?? 0} 个国家的关联，之后这些国家将使用默认规则。
          </AlertDialogDescription>
          <div className="flex justify-end gap-2">
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction
              disabled={deleteMutation.isPending}
              onClick={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
            >
              删除
            </AlertDialogAction>
          </div>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

function RuleFormView({
  form,
  setForm,
  saving,
  onSubmit,
  onCancel,
  submitText,
}: {
  form: RuleForm;
  setForm: (form: RuleForm) => void;
  saving: boolean;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onCancel: () => void;
  submitText: string;
}) {
  const segmentError = validateSegments(form.time_segments);
  return (
    <form className="space-y-4" onSubmit={onSubmit}>
      <div className="space-y-2">
        <Label htmlFor="rule-name">名称</Label>
        <Input
          id="rule-name"
          value={form.name}
          onChange={(event) => setForm({ ...form, name: event.target.value })}
        />
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
        <Button type="button" variant="outline" onClick={onCancel}>取消</Button>
        <Button type="submit" disabled={saving || !!segmentError}>{submitText}</Button>
      </div>
    </form>
  );
}

function validateRuleForm(form: RuleForm) {
  if (!form.name.trim()) return '请填写规则集名称';
  if (!form.work_days.length) return '请选择至少一个工作日';
  if (!form.time_segments.length) return '请添加至少一个时段';
  return validateSegments(form.time_segments);
}

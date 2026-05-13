'use client';

import type { CollectionKeyword } from '@shared/api';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ChevronDown, Clock3, PlayCircle, RefreshCw } from 'lucide-react';
import { useState } from 'react';
import { toast } from 'sonner';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { Sheet, SheetContent, SheetDescription, SheetTitle } from '@/components/ui/sheet';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { adminApi } from '@/lib/api';
import { formatDateTime } from '@/lib/format';

type ApiChannelKey = 'waimao_tong' | 'lixiaoyun';
type RowChannel = 'direct' | 'reverse';

const CHANNEL_LABEL = {
  direct: '直采（外贸通）',
  reverse: '反推（励销云→腾道）',
} as const;

const API_CHANNEL_BY_ROW: Record<RowChannel, ApiChannelKey> = {
  direct: 'waimao_tong',
  reverse: 'lixiaoyun',
};

const STATUS_COLOR: Record<string, 'default' | 'secondary' | 'outline' | 'destructive'> = {
  not_started: 'outline',
  pending: 'secondary',
  running: 'default',
  completed: 'secondary',
  failed: 'destructive',
  cancelled: 'outline',
  paused: 'outline',
  error: 'destructive',
};

const STATUS_LABEL: Record<string, string> = {
  not_started: '未执行',
  pending: '排队中',
  running: '进行中',
  completed: '已完成',
  failed: '失败',
  cancelled: '已取消',
  paused: '已暂停',
  error: '异常',
};

interface RowData {
  key: string;
  keyword: CollectionKeyword;
  channel: RowChannel;
  isFirst: boolean;
}

interface ReverseStageRow {
  key: 'stage1' | 'stage2';
  stage: string;
  status: string | null;
  totalCount: number;
  todayCount: number;
  dailyLimit: number | null;
  lastRunDate: string | null;
}

function normalizeStatus(status: string | null) {
  return status ?? 'not_started';
}

function TaskStatus({ status }: { status: string | null }) {
  const normalized = normalizeStatus(status);
  return <Badge variant={STATUS_COLOR[normalized] ?? 'outline'}>{STATUS_LABEL[normalized] ?? normalized}</Badge>;
}

function channelStatus(row: RowData) {
  return row.channel === 'direct' ? row.keyword.direct.status : row.keyword.reverse_stage2.status;
}

function channelLastRunDate(row: RowData) {
  return row.channel === 'direct' ? row.keyword.direct.last_run_date : row.keyword.reverse_stage2.last_run_date;
}

function resultSummary(value: Record<string, unknown>) {
  const keys = Object.keys(value ?? {}).filter((key) => key !== 'buyer_lookup_task_id');
  if (!keys.length) {
    return '-';
  }

  return keys.map((key) => `${key.replace(/_count$/, '')}: ${String(value[key])}`).join(' · ');
}

function reverseRows(keyword: CollectionKeyword): ReverseStageRow[] {
  return [
    {
      key: 'stage1',
      stage: 'stage1 励销云',
      status: keyword.reverse_stage1.status,
      totalCount: keyword.reverse_stage1.total_count,
      todayCount: keyword.reverse_stage1.today_count,
      dailyLimit: keyword.reverse_stage1.daily_limit,
      lastRunDate: keyword.reverse_stage1.last_run_date,
    },
    {
      key: 'stage2',
      stage: 'stage2 腾道',
      status: keyword.reverse_stage2.status,
      totalCount: keyword.reverse_stage2.total_count,
      todayCount: keyword.reverse_stage2.today_count,
      dailyLimit: keyword.reverse_stage2.daily_limit,
      lastRunDate: keyword.reverse_stage2.last_run_date,
    },
  ];
}

function ReverseDetailTable({ keyword }: { keyword: CollectionKeyword }) {
  return (
    <div className="rounded-md border bg-muted/20 p-3">
      <div className="mb-2 text-xs font-medium text-muted-foreground">反推阶段详情</div>
      <table className="w-full text-sm">
        <thead className="text-left text-xs text-muted-foreground">
          <tr>
            <th className="py-2">阶段</th>
            <th className="py-2">状态</th>
            <th className="py-2">累计</th>
            <th className="py-2">今日</th>
            <th className="py-2">上次运行</th>
          </tr>
        </thead>
        <tbody>
          {reverseRows(keyword).map((row) => (
            <tr key={row.key} className="border-t">
              <td className="py-2">{row.stage}</td>
              <td className="py-2">
                <TaskStatus status={row.status} />
              </td>
              <td className="py-2">{row.totalCount} 家</td>
              <td className="py-2">
                {row.todayCount}/{row.dailyLimit ?? '?'}
              </td>
              <td className="py-2 text-muted-foreground">{formatDateTime(row.lastRunDate)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function CollectionTasksPage() {
  const queryClient = useQueryClient();
  const [historyOpen, setHistoryOpen] = useState(false);
  const [historyTarget, setHistoryTarget] = useState<{ keyword: CollectionKeyword; channel: RowChannel } | null>(null);

  const { data, isLoading, isFetching, refetch } = useQuery({
    queryKey: ['admin', 'collection-keywords'],
    queryFn: async () => (await adminApi.collection.listKeywords()).data.data,
    refetchInterval: 15_000,
  });

  const historyQuery = useQuery({
    queryKey: ['admin', 'collection-history', historyTarget?.keyword.keyword_normalized, historyTarget?.channel],
    queryFn: async () => {
      if (!historyTarget) return [];
      return (
        await adminApi.collection.listHistory(
          historyTarget.keyword.keyword_normalized,
          API_CHANNEL_BY_ROW[historyTarget.channel],
        )
      ).data.data;
    },
    enabled: Boolean(historyTarget && historyOpen),
    staleTime: 0,
  });

  const triggerMutation = useMutation({
    mutationFn: (params: { keyword: CollectionKeyword; channel: RowChannel }) =>
      adminApi.collection.trigger({
        keyword_normalized: params.keyword.keyword_normalized,
        channel: API_CHANNEL_BY_ROW[params.channel],
      }),
    onSuccess: (_, vars) => {
      toast.success(`已触发「${vars.keyword.keyword}」${CHANNEL_LABEL[vars.channel]}`);
      queryClient.invalidateQueries({ queryKey: ['admin', 'collection-keywords'] });
    },
    onError: (error: unknown) => {
      const detail = (error as { response?: { data?: { error?: { message?: string } } } })?.response?.data?.error?.message;
      toast.error(detail ?? '触发失败，请重试');
    },
  });

  const keywords = data ?? [];
  const rows: RowData[] = keywords.flatMap((keyword) =>
    (['direct', 'reverse'] as RowChannel[]).map((channel, index) => ({
      key: `${keyword.keyword_normalized}__${channel}`,
      keyword,
      channel,
      isFirst: index === 0,
    })),
  );

  const openHistory = (row: RowData) => {
    setHistoryTarget({ keyword: row.keyword, channel: row.channel });
    setHistoryOpen(true);
  };

  return (
    <TooltipProvider>
      <div className="admin-page">
        <div className="admin-page-header">
          <div>
            <h1 className="admin-page-title">采集任务管理</h1>
            <p className="admin-page-description">关键词采集状态每 15 秒自动刷新。</p>
          </div>
          <Button variant="outline" size="sm" onClick={() => void refetch()} disabled={isFetching}>
            <RefreshCw className="h-4 w-4" />
            刷新
          </Button>
        </div>

        <Card>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full min-w-[1120px] text-sm">
                <thead className="border-b bg-muted/70 text-left text-xs text-muted-foreground">
                  <tr>
                    <th className="w-[240px] px-4 py-3">关键词</th>
                    <th className="w-[180px] px-4 py-3">渠道</th>
                    <th className="w-[120px] px-4 py-3">状态</th>
                    <th className="w-[160px] px-4 py-3">今日进度</th>
                    <th className="w-[220px] px-4 py-3">累计</th>
                    <th className="w-[180px] px-4 py-3">最近执行</th>
                    <th className="w-[220px] px-4 py-3 text-right">操作</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => (
                    <TaskRow
                      key={row.key}
                      row={row}
                      triggerPending={triggerMutation.isPending}
                      triggerVariables={triggerMutation.variables}
                      onTrigger={(target) => triggerMutation.mutate(target)}
                      onHistory={openHistory}
                    />
                  ))}
                </tbody>
              </table>
              {!rows.length && (
                <div className="py-10 text-center text-sm text-muted-foreground">
                  {isLoading ? '正在加载采集任务...' : '暂无采集任务'}
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        <Sheet open={historyOpen} onOpenChange={setHistoryOpen}>
          <SheetContent className="max-w-4xl overflow-y-auto p-0 sm:w-[860px]">
            <div className="border-b px-5 py-4">
              <SheetTitle>
                {historyTarget
                  ? `「${historyTarget.keyword.keyword}」${CHANNEL_LABEL[historyTarget.channel]} 历史记录`
                  : '历史记录'}
              </SheetTitle>
              <SheetDescription>展示任务创建、开始、结束、重试次数和结果摘要。</SheetDescription>
            </div>
            <div className="p-5">
              <div className="overflow-x-auto rounded-md border">
                <table className="w-full min-w-[760px] text-sm">
                  <thead className="bg-muted/70 text-left text-xs text-muted-foreground">
                    <tr>
                      {['创建时间', '状态', '开始', '结束', '重试次数', '结果'].map((label) => (
                        <th key={label} className="px-3 py-2">
                          {label}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {(historyQuery.data ?? []).map((item) => (
                      <tr key={item.task_id} className="border-t">
                        <td className="px-3 py-2">{formatDateTime(item.created_at)}</td>
                        <td className="px-3 py-2">
                          <TaskStatus status={item.status} />
                        </td>
                        <td className="px-3 py-2">{formatDateTime(item.started_at)}</td>
                        <td className="px-3 py-2">{formatDateTime(item.completed_at)}</td>
                        <td className="px-3 py-2">{item.attempt_count}</td>
                        <td className="px-3 py-2 text-xs text-muted-foreground">{resultSummary(item.result_summary)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {!(historyQuery.data ?? []).length && (
                  <div className="py-10 text-center text-sm text-muted-foreground">
                    {historyQuery.isLoading ? '正在加载历史记录...' : '暂无历史记录'}
                  </div>
                )}
              </div>
            </div>
          </SheetContent>
        </Sheet>
      </div>
    </TooltipProvider>
  );
}

function TaskRow({
  row,
  triggerPending,
  triggerVariables,
  onTrigger,
  onHistory,
}: {
  row: RowData;
  triggerPending: boolean;
  triggerVariables?: { keyword: CollectionKeyword; channel: RowChannel };
  onTrigger: (target: { keyword: CollectionKeyword; channel: RowChannel }) => void;
  onHistory: (row: RowData) => void;
}) {
  const [open, setOpen] = useState(false);
  const triggerLoading =
    triggerPending &&
    triggerVariables?.keyword.keyword_normalized === row.keyword.keyword_normalized &&
    triggerVariables.channel === row.channel;

  const disabledDirect = row.channel === 'direct';

  return (
    <>
      <tr className={row.keyword.error_msg ? 'border-b bg-destructive/5' : 'border-b'}>
        <td className="px-4 py-3 align-top">
          {row.isFirst && (
            <div className="space-y-1">
              <div className="font-medium">{row.keyword.keyword}</div>
              <div className="flex flex-wrap gap-1">
                {row.keyword.tenants.map((tenant) => (
                  <Badge key={tenant.id} variant="outline">
                    {tenant.name}
                  </Badge>
                ))}
              </div>
              {row.keyword.error_msg && <div className="text-xs text-destructive">{row.keyword.error_msg}</div>}
            </div>
          )}
        </td>
        <td className="px-4 py-3 align-top">
          <Badge variant={row.channel === 'direct' ? 'outline' : 'secondary'}>{CHANNEL_LABEL[row.channel]}</Badge>
        </td>
        <td className="px-4 py-3 align-top">
          <TaskStatus status={channelStatus(row)} />
        </td>
        <td className="px-4 py-3 align-top">
          {row.channel === 'direct'
            ? `${row.keyword.direct.today_pages}/${row.keyword.direct.total_pages ?? '?'} 页`
            : `${row.keyword.reverse_stage2.today_count}/${row.keyword.reverse_stage2.total_count ?? '?'} 家`}
        </td>
        <td className="px-4 py-3 align-top">
          {row.isFirst && (
            <div>
              <div>
                公司 {row.keyword.total_companies} · 联系人 {row.keyword.total_contacts}
              </div>
              <div className="text-xs text-muted-foreground">最近运行：{formatDateTime(row.keyword.last_run_date)}</div>
            </div>
          )}
        </td>
        <td className="px-4 py-3 align-top text-muted-foreground">{formatDateTime(channelLastRunDate(row))}</td>
        <td className="px-4 py-3 align-top">
          <div className="flex justify-end gap-2">
            {disabledDirect ? (
              <Tooltip>
                <TooltipTrigger asChild>
                  <span>
                    <Button size="sm" variant="outline" disabled>
                      <PlayCircle className="h-4 w-4" />
                      触发
                    </Button>
                  </span>
                </TooltipTrigger>
                <TooltipContent>外贸通采集 V3.1+ 可用</TooltipContent>
              </Tooltip>
            ) : (
              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <Button size="sm" variant="outline" disabled={triggerLoading}>
                    <PlayCircle className="h-4 w-4" />
                    触发
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                  <AlertDialogTitle>
                    触发「{row.keyword.keyword}」{CHANNEL_LABEL[row.channel]}？
                  </AlertDialogTitle>
                  <AlertDialogDescription>确认后会请求后端创建采集任务。</AlertDialogDescription>
                  <div className="flex justify-end gap-2">
                    <AlertDialogCancel>取消</AlertDialogCancel>
                    <AlertDialogAction onClick={() => onTrigger({ keyword: row.keyword, channel: row.channel })}>
                      确认
                    </AlertDialogAction>
                  </div>
                </AlertDialogContent>
              </AlertDialog>
            )}
            {row.channel === 'reverse' && (
              <Collapsible open={open} onOpenChange={setOpen}>
                <CollapsibleTrigger asChild>
                  <Button size="sm" variant="ghost">
                    <ChevronDown className="h-4 w-4" />
                    阶段
                  </Button>
                </CollapsibleTrigger>
              </Collapsible>
            )}
            <Button size="sm" variant="ghost" onClick={() => onHistory(row)}>
              <Clock3 className="h-4 w-4" />
              历史
            </Button>
          </div>
        </td>
      </tr>
      {row.channel === 'reverse' && (
        <tr className="border-b">
          <td colSpan={7} className="px-4 py-0">
            <Collapsible open={open} onOpenChange={setOpen}>
              <CollapsibleContent className="py-3">
                <ReverseDetailTable keyword={row.keyword} />
              </CollapsibleContent>
            </Collapsible>
          </td>
        </tr>
      )}
    </>
  );
}

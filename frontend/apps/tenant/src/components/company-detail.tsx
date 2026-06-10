'use client';

import type { Company } from '@shared/api';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { toast } from 'sonner';
import { Badge, Button, Input, Textarea } from '@shared/ui';
import { tenantApi } from '@/lib/api';

function dash(v: string | number | null | undefined) {
  if (v === null || v === undefined || v === '') return '-';
  return String(v);
}

function formatUsd(v: number | null | undefined) {
  if (v == null) return '-';
  return `$${v.toLocaleString('en-US', { maximumFractionDigits: 0 })}`;
}

function collectionTypeLabel(value: Company['collection_type']) {
  return value === 'keyword' ? '关键词采集' : '精准反推';
}

interface Props {
  company: Company;
  onGroupAdd?: (tcId: string, name: string) => void;
  onSaved: () => void;
}

export default function CompanyDetail({ company: c, onGroupAdd, onSaved }: Props) {
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [editTags, setEditTags] = useState<string[]>([]);
  const [editNote, setEditNote] = useState('');
  const [editScoreAdj, setEditScoreAdj] = useState(0);
  const [tagInput, setTagInput] = useState('');

  const contactsQuery = useQuery({
    queryKey: ['tenant', 'companies', 'contacts', c.id],
    queryFn: async () => (await tenantApi.companies.contacts(c.id)).data.data,
  });
  const contacts = contactsQuery.data ?? [];

  const saveMutation = useMutation({
    mutationFn: async () => {
      await tenantApi.companies.patch(c.tc_id, {
        tags: editTags,
        note: editNote,
        score_adjustment: editScoreAdj,
      });
    },
    onSuccess: () => {
      toast.success('保存成功');
      setEditing(false);
      queryClient.invalidateQueries({ queryKey: ['tenant', 'companies'] });
      onSaved();
    },
    onError: () => toast.error('保存失败'),
  });

  const startEdit = () => {
    setEditTags([...(c.tags ?? [])]);
    setEditNote(c.note ?? '');
    setEditScoreAdj(c.score_adjustment ?? 0);
    setEditing(true);
  };

  const cancelEdit = () => setEditing(false);

  const addTag = () => {
    const t = tagInput.trim();
    if (t && !editTags.includes(t)) setEditTags([...editTags, t]);
    setTagInput('');
  };

  const showAi = c.grade != null || c.wmt_score != null;
  const showTrade = c.trade_amount_3y_usd != null || c.trade_summary != null;
  const scoreDetails = Array.isArray(c.score_details) ? c.score_details as Array<{ dimension?: string; score?: number; max_possible?: number }> : [];

  return (
    <div className="space-y-5 p-5 text-sm">
      {/* 操作按钮 */}
      <div className="flex items-center gap-2">
        {onGroupAdd && (
          <Button size="sm" variant="outline" onClick={() => onGroupAdd(c.tc_id, c.name)}>加入群组</Button>
        )}
        {editing ? (
          <>
            <Button size="sm" disabled={saveMutation.isPending} onClick={() => saveMutation.mutate()}>
              {saveMutation.isPending ? '保存中...' : '保存'}
            </Button>
            <Button size="sm" variant="ghost" onClick={cancelEdit}>取消</Button>
          </>
        ) : (
          <Button size="sm" variant="outline" onClick={startEdit}>编辑</Button>
        )}
      </div>

      {/* 基本信息 */}
      <section>
        <h3 className="mb-2 font-semibold">基本信息</h3>
        <div className="grid grid-cols-2 gap-x-8 gap-y-2">
          <InfoRow label="网站" value={c.website} />
          <InfoRow label="评级" value={c.grade} />
          <InfoRow label="采集类型" value={collectionTypeLabel(c.collection_type)} />
          <InfoRow label="国家" value={c.country_iso3} />
          <InfoRow label="总分" value={c.wmt_score} />
          <InfoRow label="细分行业" value={c.sub_industry} />
          <InfoRow label="评分调整" value={editing ? undefined : c.score_adjustment} />
          <InfoRow label="成立年" value={c.founded_year} />
          <InfoRow label="进口额" value={formatUsd(c.trade_amount_3y_usd)} />
          <InfoRow label="产品标签" value={(c.product_tags ?? []).join(', ') || '-'} />
          <InfoRow label="进口次数" value={c.trade_count} />
          <InfoRow label="来源同行" value={c.source_competitor} />
          <InfoRow label="来源同行（中文名）" value={c.source_competitor_cn} />
        </div>
        {editing && (
          <div className="mt-2 grid grid-cols-2 gap-x-8">
            <div />
            <div>
              <span className="text-xs text-muted-foreground">评分调整 (-20 ~ +20)</span>
              <Input type="number" min={-20} max={20} className="mt-1 h-8 w-24"
                value={editScoreAdj} onChange={(e) => setEditScoreAdj(Math.max(-20, Math.min(20, Number(e.target.value) || 0)))} />
            </div>
          </div>
        )}
      </section>

      {/* AI 评估 */}
      {showAi && (
        <section>
          <h3 className="mb-2 font-semibold">AI 评估</h3>
          {scoreDetails.length > 0 && (
            <div className="mb-3 space-y-2">
              {scoreDetails.map((d, i) => (
                <div key={i} className="flex items-center gap-3">
                  <span className="w-28 truncate text-xs text-muted-foreground">{d.dimension ?? `维度${i + 1}`}</span>
                  <div className="h-2 flex-1 rounded-full bg-muted">
                    <div className="h-2 rounded-full bg-primary" style={{ width: `${d.max_possible ? ((d.score ?? 0) / d.max_possible) * 100 : 0}%` }} />
                  </div>
                  <span className="w-12 text-right text-xs">{d.score ?? 0}/{d.max_possible ?? 0}</span>
                </div>
              ))}
            </div>
          )}
          <div className="grid grid-cols-2 gap-x-8 gap-y-2">
            <InfoRow label="公司类型分析" value={c.company_type_analysis} />
            <InfoRow label="邮件优先级" value={c.email_priority} />
            <InfoRow label="销售策略" value={c.sales_approach} />
            <InfoRow label="主营业务" value={c.main_business} />
          </div>
          {c.match_reasons != null && (
            <div className="mt-2">
              <span className="text-xs text-muted-foreground">匹配原因</span>
              <p className="mt-0.5 text-xs">{String(typeof c.match_reasons === 'string' ? c.match_reasons : JSON.stringify(c.match_reasons))}</p>
            </div>
          )}
          {c.potential_needs != null && (
            <div className="mt-2">
              <span className="text-xs text-muted-foreground">潜在需求</span>
              <p className="mt-0.5 text-xs">{String(typeof c.potential_needs === 'string' ? c.potential_needs : JSON.stringify(c.potential_needs))}</p>
            </div>
          )}
          {c.recommended_products != null && (
            <div className="mt-2">
              <span className="text-xs text-muted-foreground">推荐产品</span>
              <p className="mt-0.5 text-xs">{String(typeof c.recommended_products === 'string' ? c.recommended_products : JSON.stringify(c.recommended_products))}</p>
            </div>
          )}
          {c.risk_factors != null && (
            <div className="mt-2">
              <span className="text-xs text-muted-foreground">风险因素</span>
              <p className="mt-0.5 text-xs">{String(typeof c.risk_factors === 'string' ? c.risk_factors : JSON.stringify(c.risk_factors))}</p>
            </div>
          )}
        </section>
      )}

      {/* 贸易数据 */}
      {showTrade && (
        <section>
          <h3 className="mb-2 font-semibold">贸易数据</h3>
          <div className="grid grid-cols-2 gap-x-8 gap-y-2">
            <InfoRow label="近三年进口额" value={formatUsd(c.trade_amount_3y_usd)} />
            <InfoRow label="进口次数" value={c.trade_count} />
          </div>
          {c.trade_summary && (
            <div className="mt-2">
              <span className="text-xs text-muted-foreground">贸易摘要</span>
              <p className="mt-0.5 text-xs">{c.trade_summary}</p>
            </div>
          )}
        </section>
      )}

      {/* 标签 */}
      <section>
        <h3 className="mb-2 font-semibold">标签</h3>
        {editing ? (
          <div>
            <div className="flex flex-wrap gap-1">
              {editTags.map((t) => (
                <Badge key={t} variant="secondary" className="gap-1 text-xs">
                  {t}
                  <button className="ml-0.5 hover:text-destructive" onClick={() => setEditTags(editTags.filter((x) => x !== t))}>×</button>
                </Badge>
              ))}
            </div>
            <div className="mt-1 flex gap-1">
              <Input className="h-7 text-xs" placeholder="输入标签后回车" value={tagInput}
                onChange={(e) => setTagInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addTag(); } }}
              />
            </div>
          </div>
        ) : (
          <div className="flex flex-wrap gap-1">
            {(c.tags ?? []).length ? (c.tags!.map((t) => <Badge key={t} variant="secondary" className="text-xs">{t}</Badge>)) : <span className="text-muted-foreground">-</span>}
          </div>
        )}
      </section>

      {/* 备注 */}
      <section>
        <h3 className="mb-2 font-semibold">备注</h3>
        {editing ? (
          <Textarea rows={3} value={editNote} onChange={(e) => setEditNote(e.target.value)} />
        ) : (
          <p className="text-muted-foreground">{c.note || '-'}</p>
        )}
      </section>

      {/* 联系人 */}
      <section>
        <h3 className="mb-2 font-semibold">联系人</h3>
        {contacts.length === 0 ? (
          <p className="text-muted-foreground">暂无联系人数据</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead className="border-b bg-muted/70 text-left text-muted-foreground">
                <tr>
                  {['姓名', '职位', '部门', '邮箱', '邮箱状态', '电话'].map((h) => (
                    <th key={h} className="whitespace-nowrap px-2 py-1.5">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {contacts.map((ct: Record<string, unknown>, i: number) => (
                  <tr key={i} className="border-b">
                    <td className="px-2 py-1.5">{dash(ct.name as string)}</td>
                    <td className="px-2 py-1.5">{dash(ct.title as string)}</td>
                    <td className="px-2 py-1.5">{dash(ct.department as string)}</td>
                    <td className="px-2 py-1.5">{dash(ct.email as string)}</td>
                    <td className="px-2 py-1.5">{dash(ct.email_status as string)}</td>
                    <td className="px-2 py-1.5">{dash(ct.phone as string)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value?: string | number | null }) {
  return (
    <div className="flex items-baseline gap-2">
      <span className="w-20 shrink-0 text-xs text-muted-foreground">{label}</span>
      <span className="text-xs">{dash(value)}</span>
    </div>
  );
}

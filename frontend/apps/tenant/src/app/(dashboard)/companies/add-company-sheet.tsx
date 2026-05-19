'use client';

import { useMutation } from '@tanstack/react-query';
import { Plus, Trash2 } from 'lucide-react';
import { useState } from 'react';
import { toast } from 'sonner';
import {
  Button, Input, Label, MultiSelect,
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
  Separator,
  Sheet, SheetContent, SheetTitle,
  Textarea,
} from '@shared/ui';
import { tenantApi } from '@/lib/api';
import { COUNTRY_ZH } from '@/components/company-filters';

const EMPLOYEE_SIZE_OPTIONS = [
  '1-10', '11-50', '51-200', '201-500', '501-1000', '1001-5000', '5000+',
];

interface Contact {
  name: string;
  email: string;
  title: string;
}

const EMPTY_CONTACT: Contact = { name: '', email: '', title: '' };

function emptyForm() {
  return {
    name: '',
    english_name: '',
    country: '',
    domain: '',
    website: '',
    phone: '',
    industry: '',
    employee_size: '',
    founded_year: '',
    full_address: '',
    description: '',
    product_tags: [] as string[],
    note: '',
  };
}

export default function AddCompanySheet({
  open,
  onOpenChange,
  onSuccess,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
}) {
  const [form, setForm] = useState(emptyForm);
  const [contacts, setContacts] = useState<Contact[]>([{ ...EMPTY_CONTACT }]);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const countryOpts = Object.entries(COUNTRY_ZH)
    .filter(([k]) => k !== '未公开')
    .map(([value, label]) => ({ label, value }));

  const mutation = useMutation({
    mutationFn: async (payload: Record<string, unknown>) => {
      return (await tenantApi.companies.create(payload)).data;
    },
    onSuccess: () => {
      toast.success('公司创建成功');
      resetAndClose();
      onSuccess();
    },
    onError: (err: unknown) => {
      const msg =
        (err as { response?: { data?: { message?: string } } })?.response?.data?.message
        ?? '创建失败，请重试';
      toast.error(msg);
    },
  });

  const resetAndClose = () => {
    setForm(emptyForm());
    setContacts([{ ...EMPTY_CONTACT }]);
    setErrors({});
    onOpenChange(false);
  };

  const update = (field: string, value: unknown) => {
    setForm((prev) => ({ ...prev, [field]: value }));
    if (field === 'name' && errors.name) setErrors((prev) => ({ ...prev, name: '' }));
  };

  const updateContact = (idx: number, field: keyof Contact, value: string) => {
    setContacts((prev) => prev.map((c, i) => (i === idx ? { ...c, [field]: value } : c)));
  };

  const addContact = () => setContacts((prev) => [...prev, { ...EMPTY_CONTACT }]);

  const removeContact = (idx: number) => {
    if (contacts.length <= 1) return;
    setContacts((prev) => prev.filter((_, i) => i !== idx));
  };

  const handleSubmit = () => {
    if (!form.name.trim()) {
      setErrors({ name: '请输入公司名称' });
      return;
    }
    const validContacts = contacts.filter((c) => c.name || c.email || c.title);
    const payload: Record<string, unknown> = { name: form.name.trim() };
    if (form.english_name) payload.english_name = form.english_name;
    if (form.country) payload.country = form.country;
    if (form.domain) payload.domain = form.domain;
    if (form.website) payload.website = form.website;
    if (form.phone) payload.phone = form.phone;
    if (form.industry) payload.industry = form.industry;
    if (form.employee_size) payload.employee_size = form.employee_size;
    if (form.founded_year) payload.founded_year = form.founded_year;
    if (form.full_address) payload.full_address = form.full_address;
    if (form.description) payload.description = form.description;
    if (form.product_tags.length > 0) payload.product_tags = form.product_tags;
    if (form.note) payload.note = form.note;
    if (validContacts.length > 0) payload.contacts = validContacts;
    mutation.mutate(payload);
  };

  return (
    <Sheet open={open} onOpenChange={(o) => { if (!o) resetAndClose(); }}>
      <SheetContent className="w-[660px] max-w-full overflow-y-auto p-0">
        <div className="border-b px-5 py-4">
          <SheetTitle>新增公司</SheetTitle>
        </div>

        <div className="space-y-6 p-5">
          {/* 基本信息 */}
          <section className="space-y-4">
            <h3 className="text-sm font-medium text-muted-foreground">基本信息</h3>
            <div className="space-y-3">
              <div className="space-y-1.5">
                <Label htmlFor="ac-name">公司名称 *</Label>
                <Input id="ac-name" value={form.name} onChange={(e) => update('name', e.target.value)} placeholder="例：深圳市某某科技有限公司" />
                {errors.name && <p className="text-sm text-destructive">{errors.name}</p>}
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="ac-ename">英文名称</Label>
                <Input id="ac-ename" value={form.english_name} onChange={(e) => update('english_name', e.target.value)} placeholder="例：Shenzhen XX Technology Co., Ltd." />
              </div>
              <div className="space-y-1.5">
                <Label>国家</Label>
                <Select value={form.country} onValueChange={(v) => update('country', v)}>
                  <SelectTrigger><SelectValue placeholder="选择国家" /></SelectTrigger>
                  <SelectContent>
                    {countryOpts.map((o) => (
                      <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label htmlFor="ac-domain">域名</Label>
                  <Input id="ac-domain" value={form.domain} onChange={(e) => update('domain', e.target.value)} placeholder="例：example.com" />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="ac-website">网站</Label>
                  <Input id="ac-website" value={form.website} onChange={(e) => update('website', e.target.value)} placeholder="例：https://example.com" />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label htmlFor="ac-phone">电话</Label>
                  <Input id="ac-phone" value={form.phone} onChange={(e) => update('phone', e.target.value)} placeholder="例：+86-21-12345678" />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="ac-industry">行业</Label>
                  <Input id="ac-industry" value={form.industry} onChange={(e) => update('industry', e.target.value)} placeholder="例：电子制造" />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label>员工规模</Label>
                  <Select value={form.employee_size} onValueChange={(v) => update('employee_size', v)}>
                    <SelectTrigger><SelectValue placeholder="选择规模" /></SelectTrigger>
                    <SelectContent>
                      {EMPLOYEE_SIZE_OPTIONS.map((s) => (
                        <SelectItem key={s} value={s}>{s}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="ac-year">成立年份</Label>
                  <Input id="ac-year" type="number" value={form.founded_year} onChange={(e) => update('founded_year', e.target.value)} placeholder="例：2010" />
                </div>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="ac-address">地址</Label>
                <Input id="ac-address" value={form.full_address} onChange={(e) => update('full_address', e.target.value)} placeholder="例：上海市浦东新区张江路100号" />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="ac-desc">公司简介</Label>
                <Textarea id="ac-desc" value={form.description} onChange={(e) => update('description', e.target.value)} placeholder="简要描述公司业务" rows={3} />
              </div>
              <div className="space-y-1.5">
                <Label>产品标签</Label>
                <MultiSelect value={form.product_tags} onChange={(v) => update('product_tags', v)} options={[]} placeholder="输入标签并回车" allowCreate />
              </div>
            </div>
          </section>

          <Separator />

          {/* 联系人 */}
          <section className="space-y-3">
            <h3 className="text-sm font-medium text-muted-foreground">联系人（可选）</h3>
            {contacts.map((c, idx) => (
              <div key={idx} className="flex items-start gap-2">
                <div className="grid flex-1 grid-cols-3 gap-2">
                  <Input placeholder="姓名" value={c.name} onChange={(e) => updateContact(idx, 'name', e.target.value)} />
                  <Input placeholder="邮箱" value={c.email} onChange={(e) => updateContact(idx, 'email', e.target.value)} />
                  <Input placeholder="职位" value={c.title} onChange={(e) => updateContact(idx, 'title', e.target.value)} />
                </div>
                <Button type="button" variant="ghost" size="icon" className="mt-0.5 shrink-0" disabled={contacts.length <= 1} onClick={() => removeContact(idx)}>
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            ))}
            <Button type="button" variant="outline" size="sm" onClick={addContact}>
              <Plus className="mr-1 h-3.5 w-3.5" />添加联系人
            </Button>
          </section>

          <Separator />

          {/* 备注 */}
          <section className="space-y-3">
            <h3 className="text-sm font-medium text-muted-foreground">备注</h3>
            <Textarea value={form.note} onChange={(e) => update('note', e.target.value)} placeholder="补充说明" rows={3} />
          </section>
        </div>

        {/* 底部操作 */}
        <div className="sticky bottom-0 flex justify-end gap-2 border-t bg-background px-5 py-3">
          <Button variant="outline" onClick={resetAndClose}>取消</Button>
          <Button disabled={mutation.isPending} onClick={handleSubmit}>
            {mutation.isPending ? '创建中...' : '创建公司'}
          </Button>
        </div>
      </SheetContent>
    </Sheet>
  );
}

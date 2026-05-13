'use client';

import type { ClassificationCategory, ClassificationLevel } from '@shared/api';
import { useQuery } from '@tanstack/react-query';
import { Plus, Send, Trash2 } from 'lucide-react';
import { FormEvent, useEffect, useMemo, useState } from 'react';
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
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { adminApi } from '@/lib/api';

function firstLevel(levels: ClassificationLevel[]) {
  return levels[0]?.id ?? null;
}

function firstCategory(level?: ClassificationLevel) {
  return level?.categories?.[0]?.id ?? null;
}

export function ContactClassificationPage() {
  const [levels, setLevels] = useState<ClassificationLevel[]>([]);
  const [selectedLevelId, setSelectedLevelId] = useState<string | null>(null);
  const [selectedCategoryId, setSelectedCategoryId] = useState<string | null>(null);
  const [levelName, setLevelName] = useState('');
  const [levelDisplayName, setLevelDisplayName] = useState('');
  const [categoryName, setCategoryName] = useState('');
  const [categoryDisplayName, setCategoryDisplayName] = useState('');
  const [keywordsText, setKeywordsText] = useState('');
  const [saving, setSaving] = useState(false);
  const query = useQuery({
    queryKey: ['admin', 'contact-classification'],
    queryFn: async () => (await adminApi.contactClassification.listLevels()).data,
  });

  const selectedLevel = useMemo(
    () => levels.find((level) => level.id === selectedLevelId) ?? levels[0],
    [levels, selectedLevelId],
  );
  const categories = selectedLevel?.categories ?? [];
  const selectedCategory = useMemo(
    () => categories.find((category) => category.id === selectedCategoryId) ?? categories[0],
    [categories, selectedCategoryId],
  );

  const applyLevels = (nextLevels: ClassificationLevel[]) => {
    setLevels(nextLevels);
    const nextLevelId = selectedLevelId && nextLevels.some((level) => level.id === selectedLevelId)
      ? selectedLevelId
      : firstLevel(nextLevels);
    setSelectedLevelId(nextLevelId);
    const nextLevel = nextLevels.find((level) => level.id === nextLevelId);
    const nextCategoryId =
      selectedCategoryId && nextLevel?.categories?.some((category) => category.id === selectedCategoryId)
        ? selectedCategoryId
        : firstCategory(nextLevel);
    setSelectedCategoryId(nextCategoryId);
  };

  const load = async () => {
    const result = await query.refetch();
    if (result.data) {
      applyLevels(result.data.data);
    }
  };

  useEffect(() => {
    if (query.isError) {
      toast.error('加载联系人分类失败');
      return;
    }

    if (query.data) {
      applyLevels(query.data.data);
    }
  }, [query.data, query.isError]);

  const createLevel = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!levelName.trim() || !levelDisplayName.trim()) {
      toast.error('请输入 Level 名称和显示名');
      return;
    }
    setSaving(true);
    try {
      await adminApi.contactClassification.createLevel({
        name: levelName.trim(),
        display_name: levelDisplayName.trim(),
        sort_order: levels.length + 1,
        is_sendable: true,
      });
      setLevelName('');
      setLevelDisplayName('');
      toast.success('Level 已创建');
      await load();
    } catch {
      toast.error('创建 Level 失败');
    } finally {
      setSaving(false);
    }
  };

  const updateLevelSendable = async (level: ClassificationLevel, is_sendable: boolean) => {
    try {
      await adminApi.contactClassification.updateLevel(level.id, { is_sendable });
      toast.success('可发送状态已更新');
      await load();
    } catch {
      toast.error('更新 Level 失败');
    }
  };

  const deleteLevel = async (level: ClassificationLevel) => {
    try {
      await adminApi.contactClassification.deleteLevel(level.id);
      toast.success('Level 已删除');
      await load();
    } catch {
      toast.error('删除 Level 失败');
    }
  };

  const createCategory = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selectedLevel || !categoryName.trim() || !categoryDisplayName.trim()) {
      toast.error('请选择 Level 并输入 Category');
      return;
    }
    try {
      await adminApi.contactClassification.createCategory({
        level_id: selectedLevel.id,
        name: categoryName.trim(),
        display_name: categoryDisplayName.trim(),
        sort_order: categories.length + 1,
      });
      setCategoryName('');
      setCategoryDisplayName('');
      toast.success('Category 已创建');
      await load();
    } catch {
      toast.error('创建 Category 失败');
    }
  };

  const deleteCategory = async (category: ClassificationCategory) => {
    try {
      await adminApi.contactClassification.deleteCategory(category.id);
      toast.success('Category 已删除');
      await load();
    } catch {
      toast.error('删除 Category 失败');
    }
  };

  const addKeywords = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selectedCategory) return;
    const keywords = keywordsText
      .split(/\r?\n|,/)
      .map((item) => item.trim())
      .filter(Boolean);
    if (!keywords.length) {
      toast.error('请输入批量关键词');
      return;
    }
    try {
      await adminApi.contactClassification.addKeywords({ category_id: selectedCategory.id, keywords });
      setKeywordsText('');
      toast.success('关键词已添加');
      await load();
    } catch {
      toast.error('添加关键词失败');
    }
  };

  const deleteKeyword = async (id: string) => {
    try {
      await adminApi.contactClassification.deleteKeyword(id);
      toast.success('关键词已删除');
      await load();
    } catch {
      toast.error('删除关键词失败');
    }
  };

  const keywordItems = selectedCategory?.keyword_ids ?? [];
  const keywordStrings = selectedCategory?.keywords ?? [];

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">联系人分类规则</h1>
          <p className="admin-page-description">三列层级 UI：Level → Category → Keywords，并控制是否可发送。</p>
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-[320px_320px_1fr]">
        <Card>
          <CardContent className="space-y-4 p-4">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold">Level</h2>
              <Badge variant="outline">{levels.length}</Badge>
            </div>
            <form className="grid gap-2" onSubmit={createLevel}>
              <Input placeholder="name" value={levelName} onChange={(event) => setLevelName(event.target.value)} />
              <Input placeholder="display_name" value={levelDisplayName} onChange={(event) => setLevelDisplayName(event.target.value)} />
              <Button type="submit" disabled={saving}>
                <Plus className="h-4 w-4" />
                新增 Level
              </Button>
            </form>
            <div className="space-y-2">
              {levels.map((level) => (
                <button
                  key={level.id}
                  type="button"
                  className={`w-full rounded-md border p-3 text-left text-sm ${selectedLevel?.id === level.id ? 'border-primary bg-secondary/60' : 'bg-card hover:bg-muted/60'}`}
                  onClick={() => {
                    setSelectedLevelId(level.id);
                    setSelectedCategoryId(firstCategory(level));
                  }}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium">{level.display_name}</span>
                    <Badge variant={level.is_sendable ? 'secondary' : 'outline'}>
                      <Send className="mr-1 h-3 w-3" />
                      {level.is_sendable ? '可发送' : '不可发送'}
                    </Badge>
                  </div>
                  <div className="mt-1 text-xs text-muted-foreground">{level.name}</div>
                  <div className="mt-2 flex items-center justify-between">
                    <label className="flex items-center gap-2 text-xs" onClick={(event) => event.stopPropagation()}>
                      <Checkbox
                        checked={level.is_sendable}
                        onCheckedChange={(checked) => void updateLevelSendable(level, checked === true)}
                      />
                      is_sendable
                    </label>
                    <AlertDialog>
                      <AlertDialogTrigger asChild>
                        <Button variant="ghost" size="icon" aria-label="删除 Level" onClick={(event) => event.stopPropagation()}>
                          <Trash2 className="h-4 w-4 text-destructive" />
                        </Button>
                      </AlertDialogTrigger>
                      <AlertDialogContent>
                        <AlertDialogTitle>确认删除该 Level？</AlertDialogTitle>
                        <AlertDialogDescription>关联 Category 和 Keywords 会受后端约束影响。</AlertDialogDescription>
                        <div className="flex justify-end gap-2">
                          <AlertDialogCancel>取消</AlertDialogCancel>
                          <AlertDialogAction onClick={() => void deleteLevel(level)}>删除</AlertDialogAction>
                        </div>
                      </AlertDialogContent>
                    </AlertDialog>
                  </div>
                </button>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="space-y-4 p-4">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold">Category</h2>
              <Badge variant="outline">{categories.length}</Badge>
            </div>
            <form className="grid gap-2" onSubmit={createCategory}>
              <Input placeholder="name" value={categoryName} onChange={(event) => setCategoryName(event.target.value)} />
              <Input placeholder="display_name" value={categoryDisplayName} onChange={(event) => setCategoryDisplayName(event.target.value)} />
              <Button type="submit" disabled={!selectedLevel}>
                <Plus className="h-4 w-4" />
                新增 Category
              </Button>
            </form>
            <div className="space-y-2">
              {categories.map((category) => (
                <div
                  key={category.id}
                  className={`rounded-md border p-3 text-sm ${selectedCategory?.id === category.id ? 'border-primary bg-secondary/60' : 'bg-card'}`}
                >
                  <button type="button" className="w-full text-left" onClick={() => setSelectedCategoryId(category.id)}>
                    <div className="font-medium">{category.display_name}</div>
                    <div className="text-xs text-muted-foreground">{category.name}</div>
                  </button>
                  <div className="mt-2 flex items-center justify-between text-xs text-muted-foreground">
                    <span>{(category.keyword_ids?.length ?? category.keywords?.length ?? 0)} 个关键词</span>
                    <Button variant="ghost" size="icon" aria-label="删除 Category" onClick={() => void deleteCategory(category)}>
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="space-y-4 p-4">
            <div>
              <h2 className="text-sm font-semibold">Keywords</h2>
              <p className="text-sm text-muted-foreground">
                {selectedCategory ? `${selectedLevel?.display_name ?? ''} / ${selectedCategory.display_name}` : '请选择 Category'}
              </p>
            </div>
            <form className="space-y-2" onSubmit={addKeywords}>
              <Label>批量关键词</Label>
              <Textarea
                placeholder="关键词一行一个，也支持逗号分隔"
                value={keywordsText}
                onChange={(event) => setKeywordsText(event.target.value)}
              />
              <Button type="submit" disabled={!selectedCategory}>
                添加关键词
              </Button>
            </form>
            <div className="flex flex-wrap gap-2">
              {keywordItems.map((item) => (
                <Badge key={item.id} variant="secondary" className="gap-1">
                  {item.keyword}
                  <button type="button" aria-label="删除关键词" onClick={() => void deleteKeyword(item.id)}>
                    <Trash2 className="h-3 w-3" />
                  </button>
                </Badge>
              ))}
              {!keywordItems.length &&
                keywordStrings.map((keyword) => (
                  <Badge key={keyword} variant="outline">
                    {keyword}
                  </Badge>
                ))}
              {!keywordItems.length && !keywordStrings.length && (
                <div className="py-8 text-sm text-muted-foreground">暂无关键词</div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

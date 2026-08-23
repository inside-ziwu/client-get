/** 行业动态语种码 → 中文标签；语种由动态源种子驱动，未知码原样显示。两端共用，避免各维护一份。 */
export const INDUSTRY_NEWS_LANG_LABELS: Readonly<Record<string, string>> = {
  en: '英文',
  'zh-CN': '简体中文',
  'zh-TW': '繁体中文',
};

export function industryNewsLangLabel(lang: string): string {
  return INDUSTRY_NEWS_LANG_LABELS[lang] ?? lang;
}

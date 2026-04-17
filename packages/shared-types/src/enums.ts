// === 租户与用户 ===
export type TenantStatus = 'active' | 'suspended' | 'archived';
export type UserStatus = 'active' | 'disabled';
export type UserRole = 'admin' | 'operator' | 'viewer';

// === 数据源 ===
export type DataSourceType = 'waimao_tong' | 'tengdao' | 'lixiaoyun';

// === 公司与评分 ===
export type TenantCompanyStatus = 'pending_score' | 'scoring' | 'scored' | 'selected' | 'in_plan' | 'contacted' | 'replied' | 'converted' | 'excluded';
export type CompanyGrade = 'S' | 'A' | 'B' | 'C' | 'D';
export type ContactGrade = 'A' | 'B' | 'C' | 'D';
export type SeniorityLevel = 'c_level' | 'vp' | 'director' | 'manager' | 'staff';
export type TenantContactStatus = 'available' | 'in_plan' | 'contacted' | 'replied' | 'bounced' | 'unsubscribed';
export type GroupMemberAddedBy = 'manual' | 'auto';

// === 邮件模板 ===
export type EmailTemplateSourceType = 'custom' | 'platform_copy';

// === 发送计划 ===
export type SendingPlanStatus = 'draft' | 'scheduled' | 'running' | 'paused' | 'completed' | 'cancelled';
export type RecipientSource = 'group' | 'manual' | 'filter';
export type SequenceConditionType = 'always' | 'no_reply' | 'no_open' | 'opened' | 'clicked';
export type SequenceEnrollmentStatus = 'active' | 'completed' | 'replied' | 'bounced' | 'unsubscribed' | 'paused' | 'cancelled';

// === 邮件 ===
export type EmailStatus = 'pending' | 'queued' | 'sent' | 'delivered' | 'opened' | 'clicked' | 'replied' | 'bounced' | 'complained' | 'unsubscribed' | 'failed';
export type EmailEventType = 'sent' | 'delivered' | 'opened' | 'clicked' | 'replied' | 'bounced' | 'complained' | 'unsubscribed';

// === 情报 ===
export type IntelligenceSourceType = 'rss' | 'website' | 'manual';
export type IntelligenceArticleStatus = 'pending' | 'processed' | 'published' | 'archived';
export type ArticlePublicationStatus = 'unread' | 'read' | 'starred' | 'archived';

// === 域名预热 ===
export type DomainVerificationStatus = 'pending' | 'verifying' | 'verified' | 'failed';

// === AI ===
export type AiModelType = 'scoring' | 'email_generation' | 'intelligence' | 'general';
export type AiUsageType = 'scoring' | 'email_generation' | 'intelligence_summary' | 'other';

// === 财务 ===
export type BalanceTransactionType = 'recharge' | 'consumption' | 'refund' | 'adjustment';

// === 通知 ===
export type NotificationCategory = 'scoring_complete' | 'plan_complete' | 'reply_received' | 'balance_low' | 'intelligence' | 'system';

// === 采集任务 ===
export type CollectionTaskStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';

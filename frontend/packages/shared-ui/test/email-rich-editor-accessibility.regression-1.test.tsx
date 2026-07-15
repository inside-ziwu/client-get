import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { EmailRichEditor } from '../src/components/email-rich-editor';

describe('EmailRichEditor 可访问性', () => {
  // Regression: ISSUE-002 — 富文本格式按钮缺少可访问名称
  // Found by /qa on 2026-07-15
  // Report: .gstack/qa-reports/qa-report-phase-b-local-2026-07-15.md
  it('为每个格式按钮提供明确的可访问名称', async () => {
    render(<EmailRichEditor initialContent="<p>正文</p>" />);

    expect(await screen.findByRole('button', { name: '加粗' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '斜体' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '有序列表' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '无序列表' })).toBeInTheDocument();
  });
});

import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { EmailRichEditor } from '../src/components/email-rich-editor';

describe('EmailRichEditor 列表视觉', () => {
  // Regression: 人工 Gate 发现列表命令已生成 ol/ul，但基础样式隐藏了序号与圆点
  // Found by user acceptance on 2026-07-15
  it('为有序和无序列表恢复可见标记与内容缩进', async () => {
    const { container } = render(<EmailRichEditor initialContent="<p>正文</p>" />);

    await screen.findByRole('button', { name: '有序列表' });
    const content = container.querySelector('.tiptap')?.parentElement;

    expect(content).toHaveClass(
      '[&_.tiptap_ol]:list-decimal',
      '[&_.tiptap_ul]:list-disc',
      '[&_.tiptap_ol]:pl-6',
      '[&_.tiptap_ul]:pl-6',
    );
  });
});

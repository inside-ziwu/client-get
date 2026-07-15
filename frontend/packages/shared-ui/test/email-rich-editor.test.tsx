import { render, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { EmailRichEditor } from '../src/components/email-rich-editor';

describe('EmailRichEditor', () => {
  it('创建编辑器时同步初始 HTML 与纯文本，未编辑也可直接保存', async () => {
    const onUpdate = vi.fn();

    render(
      <EmailRichEditor
        initialContent="<p>你好，{{contact_name}}</p>"
        onUpdate={onUpdate}
      />,
    );

    await waitFor(() => {
      expect(onUpdate).toHaveBeenCalledWith(
        '<p>你好，{{contact_name}}</p>',
        '你好，{{contact_name}}',
      );
    });
  });
});

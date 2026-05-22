import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import React, { createRef } from 'react';

afterEach(cleanup);

const mockCommands = {
  toggleBold: vi.fn(),
  toggleItalic: vi.fn(),
  toggleOrderedList: vi.fn(),
  toggleBulletList: vi.fn(),
  focus: vi.fn(),
  insertContent: vi.fn(),
};

const mockEditor = {
  getHTML: () => '<p>test</p>',
  getText: () => 'test',
  isActive: () => false,
  isFocused: false,
  commands: mockCommands,
  chain: () => ({
    focus: () => ({
      toggleBold: () => ({ run: vi.fn() }),
      toggleItalic: () => ({ run: vi.fn() }),
      toggleOrderedList: () => ({ run: vi.fn() }),
      toggleBulletList: () => ({ run: vi.fn() }),
    }),
  }),
};

vi.mock('@tiptap/react', () => ({
  useEditor: () => mockEditor,
  EditorContent: ({ editor }: { editor: unknown }) =>
    editor ? <div data-testid="editor-content" /> : null,
}));

vi.mock('@tiptap/starter-kit', () => ({
  default: {},
}));

vi.mock('@tiptap/extension-placeholder', () => ({
  default: { configure: () => ({}) },
}));

import {
  EmailRichEditor,
  type EmailRichEditorHandle,
} from '@shared/ui/components/email-rich-editor';

describe('EmailRichEditor', () => {
  it('渲染不崩溃', () => {
    const { container } = render(<EmailRichEditor />);
    expect(container.querySelector('.prose')).toBeInTheDocument();
  });

  it('渲染工具栏 4 个按钮', () => {
    render(<EmailRichEditor />);
    const buttons = screen.getAllByRole('button');
    expect(buttons.length).toBe(4);
  });

  it('ref 上存在 insertVariable 方法', () => {
    const ref = createRef<EmailRichEditorHandle>();
    render(<EmailRichEditor ref={ref} />);
    expect(typeof ref.current?.insertVariable).toBe('function');
  });
});

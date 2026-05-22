'use client';

import { forwardRef, useImperativeHandle } from 'react';
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Placeholder from '@tiptap/extension-placeholder';
import { Button } from './button';

export interface EmailRichEditorHandle {
  insertVariable(text: string): void;
}

interface EmailRichEditorProps {
  initialContent?: string;
  placeholder?: string;
  onUpdate?: (html: string, text: string) => void;
}

export const EmailRichEditor = forwardRef<
  EmailRichEditorHandle,
  EmailRichEditorProps
>(function EmailRichEditor({ initialContent, placeholder, onUpdate }, ref) {
  const editor = useEditor({
    extensions: [
      StarterKit,
      Placeholder.configure({ placeholder: placeholder ?? '请输入邮件内容…' }),
    ],
    content: initialContent || '',
    immediatelyRender: false,
    onUpdate: ({ editor }) => {
      onUpdate?.(editor.getHTML(), editor.getText());
    },
  });

  useImperativeHandle(ref, () => ({
    insertVariable(text: string) {
      if (!editor) return;
      if (!editor.isFocused) {
        editor.commands.focus('end');
      }
      editor.commands.insertContent(text);
    },
  }));

  if (!editor) return null;

  return (
    <div className="rounded-md border">
      <div className="flex gap-1 border-b p-1">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={() => editor.chain().focus().toggleBold().run()}
          className={editor.isActive('bold') ? 'bg-accent' : ''}
        >
          B
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={() => editor.chain().focus().toggleItalic().run()}
          className={editor.isActive('italic') ? 'bg-accent' : ''}
        >
          I
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={() => editor.chain().focus().toggleOrderedList().run()}
          className={editor.isActive('orderedList') ? 'bg-accent' : ''}
        >
          OL
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={() => editor.chain().focus().toggleBulletList().run()}
          className={editor.isActive('bulletList') ? 'bg-accent' : ''}
        >
          UL
        </Button>
      </div>
      <EditorContent
        editor={editor}
        className="prose max-w-none p-3 min-h-[200px] [&_.tiptap]:outline-none"
      />
    </div>
  );
});

'use client';

import { forwardRef, useImperativeHandle, useRef } from 'react';
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Placeholder from '@tiptap/extension-placeholder';
import { Bold, Italic, ListOrdered, List } from 'lucide-react';
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
  const lastSelectionRef = useRef<{ from: number; to: number } | null>(null);

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
    onSelectionUpdate: ({ editor }) => {
      lastSelectionRef.current = {
        from: editor.state.selection.from,
        to: editor.state.selection.to,
      };
    },
    onBlur: ({ editor }) => {
      lastSelectionRef.current = {
        from: editor.state.selection.from,
        to: editor.state.selection.to,
      };
    },
  });

  useImperativeHandle(ref, () => ({
    insertVariable(text: string) {
      if (!editor) return;
      if (!editor.isFocused && lastSelectionRef.current) {
        const { from, to } = lastSelectionRef.current;
        editor.chain().focus().setTextSelection({ from, to }).insertContent(text).run();
        return;
      }
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
          size="icon"
          className={`h-8 w-8 ${editor.isActive('bold') ? 'bg-accent' : ''}`}
          onClick={() => editor.chain().focus().toggleBold().run()}
        >
          <Bold className="h-4 w-4" />
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className={`h-8 w-8 ${editor.isActive('italic') ? 'bg-accent' : ''}`}
          onClick={() => editor.chain().focus().toggleItalic().run()}
        >
          <Italic className="h-4 w-4" />
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className={`h-8 w-8 ${editor.isActive('orderedList') ? 'bg-accent' : ''}`}
          onClick={() => editor.chain().focus().toggleOrderedList().run()}
        >
          <ListOrdered className="h-4 w-4" />
        </Button>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className={`h-8 w-8 ${editor.isActive('bulletList') ? 'bg-accent' : ''}`}
          onClick={() => editor.chain().focus().toggleBulletList().run()}
        >
          <List className="h-4 w-4" />
        </Button>
      </div>
      <EditorContent
        editor={editor}
        className="prose max-w-none p-3 min-h-[200px] [&_.tiptap]:outline-none"
      />
    </div>
  );
});

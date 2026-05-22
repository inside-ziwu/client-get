'use client';

import 'grapesjs/dist/css/grapes.min.css';
import type { Editor, Plugin } from 'grapesjs';
import { forwardRef, useEffect, useImperativeHandle, useRef } from 'react';

export interface GrapesEmailEditorHandle {
  getHtml: () => string;
  getDesign: () => unknown;
}

export const GrapesEmailEditor = forwardRef<
  GrapesEmailEditorHandle,
  { html?: string; design?: unknown; onReady?: () => void }
>(function GrapesEmailEditor({ html, design, onReady }, ref) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const editorRef = useRef<Editor | null>(null);

  useImperativeHandle(ref, () => ({
    getHtml: () => {
      const editor = editorRef.current;
      return editor ? `${editor.getHtml()}<style>${editor.getCss()}</style>` : (html ?? '');
    },
    getDesign: () => editorRef.current?.getProjectData() ?? design ?? null,
  }));

  useEffect(() => {
    let mounted = true;

    async function init() {
      if (!containerRef.current || editorRef.current) return;
      const [{ default: grapes }, { default: newsletter }] = await Promise.all([
        import('grapesjs'),
        import('grapesjs-preset-newsletter'),
      ]);
      if (!mounted || !containerRef.current) return;

      const editor = grapes.init({
        container: containerRef.current,
        height: '640px',
        storageManager: false,
        plugins: [newsletter as Plugin],
      });

      if (design && typeof design === 'object') {
        editor.loadProjectData(design as Parameters<typeof editor.loadProjectData>[0]);
      } else if (html) {
        editor.setComponents(html);
      }

      editorRef.current = editor;
      onReady?.();
    }

    void init();

    return () => {
      mounted = false;
      editorRef.current?.destroy();
      editorRef.current = null;
    };
  }, [design, html, onReady]);

  return <div ref={containerRef} className="min-h-[640px] overflow-hidden rounded-md border bg-white" />;
});

/**
 * GrapeJS email editor wrapper.
 *
 * Uses grapesjs-preset-newsletter which generates table-based,
 * inline-styled HTML compatible with major email clients.
 * Fully bundled via npm — no CDN dependency.
 */
import { forwardRef, useEffect, useImperativeHandle, useRef } from 'react';
import grapesjs from 'grapesjs';
import type { Editor } from 'grapesjs';
import gjsNewsletter from 'grapesjs-preset-newsletter';
import 'grapesjs/dist/css/grapes.min.css';

export interface GrapesEmailEditorRef {
  /** Returns inlined-CSS HTML ready for sending */
  getHtml: () => string;
  /** Returns the project JSON needed to reload the design later */
  getDesign: () => unknown;
}

interface Props {
  /** Initial design JSON (from a previous save). Omit for a blank canvas. */
  initialDesign?: unknown;
  height?: number;
}

const GrapesEmailEditor = forwardRef<GrapesEmailEditorRef, Props>(
  ({ initialDesign, height = 620 }, ref) => {
    const containerRef = useRef<HTMLDivElement>(null);
    const editorRef = useRef<Editor | null>(null);

    useEffect(() => {
      if (!containerRef.current) return;

      const editor = grapesjs.init({
        container: containerRef.current,
        height: `${height}px`,
        storageManager: false,
        plugins: [gjsNewsletter],
        pluginsOpts: {
          'grapesjs-preset-newsletter': {},
        },
        // Clean up default panels we don't need
        panels: { defaults: [] },
      });

      // Load existing design if provided
      if (initialDesign) {
        try {
          editor.loadProjectData(initialDesign as Parameters<Editor['loadProjectData']>[0]);
        } catch {
          // ignore malformed design
        }
      }

      editorRef.current = editor;

      return () => {
        editor.destroy();
        editorRef.current = null;
      };
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    // Expose methods to parent via ref
    useImperativeHandle(ref, () => ({
      getHtml: () => {
        if (!editorRef.current) return '';
        // gjs-get-inlined-html is provided by grapesjs core
        return (editorRef.current.runCommand('gjs-get-inlined-html') as string) ?? '';
      },
      getDesign: () => {
        if (!editorRef.current) return null;
        return editorRef.current.getProjectData();
      },
    }));

    return (
      <div
        ref={containerRef}
        style={{ border: '1px solid #d9d9d9', borderRadius: 6, overflow: 'hidden' }}
      />
    );
  },
);

GrapesEmailEditor.displayName = 'GrapesEmailEditor';
export default GrapesEmailEditor;

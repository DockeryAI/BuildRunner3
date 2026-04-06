/**
 * Monaco PRD Editor - Rich markdown editor with syntax highlighting
 *
 * Features:
 * - Monaco Editor integration
 * - Syntax highlighting for markdown
 * - Autocomplete
 * - Diff view for changes
 * - Live validation
 */

import React, { useRef, useEffect, useState } from 'react';
import * as monaco from 'monaco-editor';

interface MonacoPRDEditorProps {
  value: string;
  onChange: (value: string) => void;
  onSave?: () => void;
  readOnly?: boolean;
  showDiff?: boolean;
  originalValue?: string;
}

export function MonacoPRDEditor({
  value,
  onChange,
  onSave,
  readOnly = false,
  showDiff = false,
  originalValue
}: MonacoPRDEditorProps) {
  const editorRef = useRef<HTMLDivElement>(null);
  const [editor, setEditor] = useState<monaco.editor.IStandaloneCodeEditor | null>(null);
  const [diffEditor, setDiffEditor] = useState<monaco.editor.IStandaloneDiffEditor | null>(null);

  useEffect(() => {
    if (!editorRef.current) return;

    // Configure Monaco for markdown
    monaco.languages.setLanguageConfiguration('markdown', {
      wordPattern: /(-?\d*\.\d\w*)|([^\`\~\!\@\#\%\^\&\*\(\)\-\=\+\[\{\]\}\\\|\;\:\'\"\,\.\<\>\/\?\s]+)/g,
      comments: {
        blockComment: ['<!--', '-->']
      },
      brackets: [
        ['{', '}'],
        ['[', ']'],
        ['(', ')']
      ],
      autoClosingPairs: [
        { open: '{', close: '}' },
        { open: '[', close: ']' },
        { open: '(', close: ')' },
        { open: '<', close: '>', notIn: ['string'] },
        { open: '`', close: '`', notIn: ['string'] },
        { open: '"', close: '"', notIn: ['string'] },
        { open: "'", close: "'", notIn: ['string', 'comment'] },
        { open: '**', close: '**' },
        { open: '__', close: '__' },
        { open: '*', close: '*' },
        { open: '_', close: '_' }
      ],
      surroundingPairs: [
        { open: '(', close: ')' },
        { open: '[', close: ']' },
        { open: '`', close: '`' },
        { open: '**', close: '**' },
        { open: '__', close: '__' },
        { open: '*', close: '*' },
        { open: '_', close: '_' }
      ]
    });

    // Register markdown snippets
    monaco.languages.registerCompletionItemProvider('markdown', {
      provideCompletionItems: (model, position) => {
        const suggestions = [
          {
            label: 'feature',
            kind: monaco.languages.CompletionItemKind.Snippet,
            insertText: [
              '## Feature ${1:number}: ${2:name}',
              '',
              '**Priority:** ${3|high,medium,low|}',
              '',
              '### Description',
              '',
              '${4:description}',
              '',
              '### Requirements',
              '',
              '- ${5:requirement}',
              '',
              '### Acceptance Criteria',
              '',
              '- [ ] ${6:criterion}',
              ''
            ].join('\n'),
            insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
            documentation: 'Insert a feature template'
          },
          {
            label: 'requirement',
            kind: monaco.languages.CompletionItemKind.Snippet,
            insertText: '- ${1:requirement}',
            insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
            documentation: 'Insert a requirement item'
          },
          {
            label: 'acceptance',
            kind: monaco.languages.CompletionItemKind.Snippet,
            insertText: '- [ ] ${1:criterion}',
            insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
            documentation: 'Insert an acceptance criterion'
          }
        ];

        return { suggestions };
      }
    });

    // Create editor or diff editor based on mode
    if (showDiff && originalValue !== undefined) {
      const diffEditorInstance = monaco.editor.createDiffEditor(editorRef.current, {
        readOnly: readOnly,
        automaticLayout: true,
        theme: 'vs-light',
        minimap: { enabled: true },
        scrollBeyondLastLine: false,
        wordWrap: 'on',
        lineNumbers: 'on',
        renderSideBySide: true
      });

      const originalModel = monaco.editor.createModel(originalValue, 'markdown');
      const modifiedModel = monaco.editor.createModel(value, 'markdown');

      diffEditorInstance.setModel({
        original: originalModel,
        modified: modifiedModel
      });

      // Listen for changes
      modifiedModel.onDidChangeContent(() => {
        onChange(modifiedModel.getValue());
      });

      setDiffEditor(diffEditorInstance);

      return () => {
        diffEditorInstance.dispose();
        originalModel.dispose();
        modifiedModel.dispose();
      };
    } else {
      // Regular editor
      const editorInstance = monaco.editor.create(editorRef.current, {
        value: value,
        language: 'markdown',
        theme: 'vs-light',
        readOnly: readOnly,
        automaticLayout: true,
        minimap: { enabled: true },
        scrollBeyondLastLine: false,
        wordWrap: 'on',
        lineNumbers: 'on',
        fontSize: 14,
        tabSize: 2,
        insertSpaces: true,
        quickSuggestions: true,
        suggestOnTriggerCharacters: true,
        acceptSuggestionOnEnter: 'on',
        folding: true,
        foldingStrategy: 'indentation',
        showFoldingControls: 'always',
        formatOnPaste: true,
        formatOnType: true
      });

      // Listen for changes
      editorInstance.onDidChangeModelContent(() => {
        onChange(editorInstance.getValue());
      });

      // Add save command (Cmd/Ctrl+S)
      if (onSave) {
        editorInstance.addCommand(
          monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS,
          () => {
            onSave();
          }
        );
      }

      setEditor(editorInstance);

      return () => {
        editorInstance.dispose();
      };
    }
  }, [showDiff, originalValue]);

  // Update editor value when prop changes
  useEffect(() => {
    if (editor && editor.getValue() !== value) {
      editor.setValue(value);
    }
  }, [value, editor]);

  return (
    <div
      ref={editorRef}
      style={{
        width: '100%',
        height: '100%',
        minHeight: '400px',
        border: '1px solid #e0e0e0',
        borderRadius: '4px'
      }}
    />
  );
}

export default MonacoPRDEditor;

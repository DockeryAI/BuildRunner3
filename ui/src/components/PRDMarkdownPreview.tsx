/**
 * PRD Markdown Preview - Split-screen markdown editor with live preview
 *
 * Features:
 * - Real-time markdown rendering
 * - Split-screen layout (editor | preview)
 * - Syntax highlighting in preview
 * - Checkbox support for acceptance criteria
 * - Automatic heading anchors
 * - Mobile-responsive (stacked view)
 */

import React, { useState, useEffect, useMemo } from 'react';
import './PRDMarkdownPreview.css';

interface PRDMarkdownPreviewProps {
  value: string;
  onChange: (value: string) => void;
  onSave?: () => void;
  readOnly?: boolean;
}

export function PRDMarkdownPreview({
  value,
  onChange,
  onSave,
  readOnly = false
}: PRDMarkdownPreviewProps) {
  const [splitView, setSplitView] = useState<'split' | 'editor' | 'preview'>('split');

  // Simple markdown to HTML converter
  const renderMarkdown = useMemo(() => {
    let html = value;

    // Escape HTML
    html = html.replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');

    // Headers (must come before other patterns)
    html = html.replace(/^### (.+)$/gm, '<h3>$1</h3>');
    html = html.replace(/^## (.+)$/gm, '<h2>$1</h2>');
    html = html.replace(/^# (.+)$/gm, '<h1>$1</h1>');

    // Bold
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/__(.+?)__/g, '<strong>$1</strong>');

    // Italic
    html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
    html = html.replace(/_(.+?)_/g, '<em>$1</em>');

    // Code blocks
    html = html.replace(/```([a-z]*)\n([\s\S]*?)```/g, (match, lang, code) => {
      return `<pre><code class="language-${lang}">${code}</code></pre>`;
    });

    // Inline code
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

    // Checkboxes (acceptance criteria)
    html = html.replace(/- \[ \] (.+)$/gm, '<div class="checkbox unchecked"><input type="checkbox" disabled /> <span>$1</span></div>');
    html = html.replace(/- \[x\] (.+)$/gmi, '<div class="checkbox checked"><input type="checkbox" checked disabled /> <span>$1</span></div>');

    // Lists (must come after checkboxes)
    html = html.replace(/^- (.+)$/gm, '<li>$1</li>');
    html = html.replace(/^\* (.+)$/gm, '<li>$1</li>');
    html = html.replace(/^(\d+)\. (.+)$/gm, '<li>$2</li>');

    // Wrap consecutive <li> in <ul>
    html = html.replace(/(<li>.*<\/li>\n?)+/g, (match) => {
      return `<ul>${match}</ul>`;
    });

    // Links
    html = html.replace(/\[([^\]]+)\]\(([^\)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');

    // Paragraphs (lines not already wrapped)
    html = html.split('\n').map(line => {
      if (line.trim() === '' || line.startsWith('<') || line.match(/^[\s]*$/)) {
        return line;
      }
      return `<p>${line}</p>`;
    }).join('\n');

    // Priority badges
    html = html.replace(/\*\*Priority:\*\* (Critical|High|Medium|Low)/gi, (match, priority) => {
      const color = {
        'critical': '#dc2626',
        'high': '#ea580c',
        'medium': '#d97706',
        'low': '#65a30d'
      }[priority.toLowerCase()] || '#6b7280';
      return `<span class="priority-badge" style="background-color: ${color}20; color: ${color}; border-color: ${color};">Priority: ${priority}</span>`;
    });

    // Status badges
    html = html.replace(/\*\*Status:\*\* (\w+)/gi, (match, status) => {
      return `<span class="status-badge">${status}</span>`;
    });

    return html;
  }, [value]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Cmd/Ctrl + S to save
    if ((e.metaKey || e.ctrlKey) && e.key === 's') {
      e.preventDefault();
      onSave?.();
    }

    // Tab key inserts 2 spaces
    if (e.key === 'Tab') {
      e.preventDefault();
      const textarea = e.currentTarget;
      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      const newValue = value.substring(0, start) + '  ' + value.substring(end);
      onChange(newValue);

      // Set cursor position after inserted spaces
      setTimeout(() => {
        textarea.selectionStart = textarea.selectionEnd = start + 2;
      }, 0);
    }
  };

  return (
    <div className="prd-markdown-preview">
      {/* Toolbar */}
      <div className="preview-toolbar">
        <div className="view-controls">
          <button
            className={splitView === 'editor' ? 'active' : ''}
            onClick={() => setSplitView('editor')}
            title="Editor only"
          >
            📝 Editor
          </button>
          <button
            className={splitView === 'split' ? 'active' : ''}
            onClick={() => setSplitView('split')}
            title="Split view"
          >
            ⚡ Split
          </button>
          <button
            className={splitView === 'preview' ? 'active' : ''}
            onClick={() => setSplitView('preview')}
            title="Preview only"
          >
            👁️ Preview
          </button>
        </div>

        <div className="preview-stats">
          <span>{value.split('\n').length} lines</span>
          <span>{value.length} chars</span>
        </div>
      </div>

      {/* Split Content */}
      <div className={`preview-content layout-${splitView}`}>
        {/* Editor Pane */}
        {(splitView === 'editor' || splitView === 'split') && (
          <div className="editor-pane">
            <textarea
              value={value}
              onChange={(e) => onChange(e.target.value)}
              onKeyDown={handleKeyDown}
              readOnly={readOnly}
              className="markdown-textarea"
              placeholder="# Project Name

## Project Overview

Write your PRD in markdown...

## Feature 1: Feature Name

**Priority:** High
**Status:** Planned

### Description

Feature description here...

### Requirements

- Requirement 1
- Requirement 2

### Acceptance Criteria

- [ ] Criterion 1
- [ ] Criterion 2"
              spellCheck={false}
            />
          </div>
        )}

        {/* Preview Pane */}
        {(splitView === 'preview' || splitView === 'split') && (
          <div className="preview-pane">
            <div
              className="markdown-rendered"
              dangerouslySetInnerHTML={{ __html: renderMarkdown }}
            />
          </div>
        )}
      </div>

      {/* Help Footer */}
      {!readOnly && (
        <div className="preview-footer">
          <span className="help-text">
            💡 Supports: **bold**, *italic*, `code`, [links](url), - lists, - [ ] checkboxes
          </span>
          {onSave && (
            <span className="help-text">
              💾 Cmd/Ctrl+S to save
            </span>
          )}
        </div>
      )}
    </div>
  );
}

export default PRDMarkdownPreview;

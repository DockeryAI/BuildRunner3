import React, { useEffect, useRef } from 'react';
import { Terminal } from 'xterm';
import { FitAddon } from 'xterm-addon-fit';
import { SearchAddon } from 'xterm-addon-search';
import 'xterm/css/xterm.css';
import { useBuildStore, TerminalLine } from '../stores/buildStore';
import './TerminalPanel.css';

export const TerminalPanel: React.FC = () => {
  const terminalRef = useRef<HTMLDivElement>(null);
  const xtermRef = useRef<Terminal | null>(null);
  const fitAddonRef = useRef<FitAddon | null>(null);
  const { terminalLines, clearTerminalLines } = useBuildStore();
  const lastLineIndexRef = useRef(0);

  useEffect(() => {
    if (!terminalRef.current) return;

    // Initialize xterm
    const term = new Terminal({
      theme: {
        background: '#1e293b',
        foreground: '#e2e8f0',
        cursor: '#3b82f6',
        black: '#0f172a',
        red: '#ef4444',
        green: '#10b981',
        yellow: '#f59e0b',
        blue: '#3b82f6',
        magenta: '#a855f7',
        cyan: '#06b6d4',
        white: '#f1f5f9',
      },
      fontFamily: '"Fira Code", "Consolas", monospace',
      fontSize: 13,
      lineHeight: 1.4,
      cursorBlink: true,
      scrollback: 1000,
    });

    const fitAddon = new FitAddon();
    const searchAddon = new SearchAddon();

    term.loadAddon(fitAddon);
    term.loadAddon(searchAddon);
    term.open(terminalRef.current);
    fitAddon.fit();

    xtermRef.current = term;
    fitAddonRef.current = fitAddon;

    // Handle resize
    const handleResize = () => fitAddon.fit();
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      term.dispose();
    };
  }, []);

  useEffect(() => {
    if (!xtermRef.current) return;

    // Write new lines
    const newLines = terminalLines.slice(lastLineIndexRef.current);
    newLines.forEach((line) => {
      const colorCode = getColorCode(line.type);
      xtermRef.current?.writeln(`${colorCode}${line.content}\x1b[0m`);
    });

    lastLineIndexRef.current = terminalLines.length;
  }, [terminalLines]);

  const getColorCode = (type: TerminalLine['type']): string => {
    const codes: Record<string, string> = {
      stdout: '\x1b[37m',
      stderr: '\x1b[31m',
      info: '\x1b[36m',
      error: '\x1b[91m',
      success: '\x1b[32m',
    };
    return codes[type] || codes.stdout;
  };

  const handleClear = () => {
    xtermRef.current?.clear();
    clearTerminalLines();
    lastLineIndexRef.current = 0;
  };

  return (
    <div className="terminal-panel">
      <div className="terminal-header">
        <span className="terminal-title">Build Output</span>
        <div className="terminal-controls">
          <button onClick={handleClear} className="terminal-btn">
            Clear
          </button>
        </div>
      </div>
      <div ref={terminalRef} className="terminal-container" />
    </div>
  );
};

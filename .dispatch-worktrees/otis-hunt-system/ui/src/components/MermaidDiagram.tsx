/**
 * Mermaid Diagram Renderer
 * Renders Mermaid diagrams from markdown code blocks
 */

import { useEffect, useRef, useState } from 'react';

interface MermaidDiagramProps {
  diagram: string;
  className?: string;
}

export function MermaidDiagram({ diagram, className = '' }: MermaidDiagramProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!diagram || !containerRef.current) return;

    const renderDiagram = async () => {
      try {
        setIsLoading(true);
        setError(null);

        // Dynamically import mermaid (lazy load)
        const mermaid = await import('mermaid');

        // Initialize mermaid with configuration
        mermaid.default.initialize({
          startOnLoad: false,
          theme: 'dark',
          securityLevel: 'loose',
          fontFamily: 'monospace',
          themeVariables: {
            primaryColor: '#1177bb',
            primaryTextColor: '#e0e0e0',
            primaryBorderColor: '#0e639c',
            lineColor: '#00d9ff',
            secondaryColor: '#1a4d7a',
            tertiaryColor: '#0a0e27',
          },
        });

        // Generate unique ID for this diagram
        const id = `mermaid-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

        // Render the diagram
        const { svg } = await mermaid.default.render(id, diagram);

        if (containerRef.current) {
          containerRef.current.innerHTML = svg;
        }

        setIsLoading(false);
      } catch (err: any) {
        console.error('Mermaid render error:', err);
        setError(err.message || 'Failed to render diagram');
        setIsLoading(false);
      }
    };

    renderDiagram();
  }, [diagram]);

  if (error) {
    return (
      <div className={`mermaid-error ${className}`}>
        <div className="error-icon">⚠️</div>
        <div className="error-message">Failed to render diagram: {error}</div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className={`mermaid-loading ${className}`}>
        <div className="spinner">🔄</div>
        <div>Rendering diagram...</div>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      className={`mermaid-diagram ${className}`}
      style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        padding: '20px',
        background: 'rgba(10, 14, 39, 0.5)',
        borderRadius: '8px',
        border: '1px solid rgba(0, 217, 255, 0.2)',
      }}
    />
  );
}

/**
 * Architecture Diagram Section
 * Wrapper for displaying architecture diagrams in PRD
 */
interface ArchitectureSectionProps {
  diagram: string | null;
  onEdit?: () => void;
}

export function ArchitectureSection({ diagram, onEdit }: ArchitectureSectionProps) {
  if (!diagram) {
    return (
      <div className="architecture-placeholder">
        <div className="placeholder-icon">🏗️</div>
        <div className="placeholder-text">No architecture diagram yet</div>
        {onEdit && (
          <button onClick={onEdit} className="add-diagram-btn">
            Add Diagram
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="architecture-section">
      <div className="section-header">
        <h3>🏗️ System Architecture</h3>
        {onEdit && (
          <button onClick={onEdit} className="edit-diagram-btn">
            ✏️ Edit
          </button>
        )}
      </div>
      <MermaidDiagram diagram={diagram} />
    </div>
  );
}

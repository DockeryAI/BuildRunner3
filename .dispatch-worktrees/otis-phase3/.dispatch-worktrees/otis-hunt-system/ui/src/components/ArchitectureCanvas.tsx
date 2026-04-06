import React, { useCallback, useEffect, useState } from 'react';
import ReactFlow, {
  Node,
  Edge,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  ConnectionMode,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { Component } from '../stores/buildStore';
import { ComponentNode } from './nodes/ComponentNode';
import './ArchitectureCanvas.css';

interface ArchitectureCanvasProps {
  components: Component[];
  currentComponent?: string;
}

const nodeTypes = {
  component: ComponentNode,
};

export const ArchitectureCanvas: React.FC<ArchitectureCanvasProps> = ({
  components,
  currentComponent,
}) => {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);

  useEffect(() => {
    if (!components || components.length === 0) return;

    // Convert components to nodes
    const newNodes: Node[] = components.map((comp, index) => ({
      id: comp.id,
      type: 'component',
      position: calculatePosition(index, components.length),
      data: {
        component: comp,
        isActive: comp.id === currentComponent,
      },
    }));

    // Create edges from dependencies
    const newEdges: Edge[] = [];
    components.forEach((comp) => {
      comp.dependencies.forEach((depId) => {
        if (components.find((c) => c.id === depId)) {
          newEdges.push({
            id: `${comp.id}-${depId}`,
            source: depId,
            target: comp.id,
            animated: comp.status === 'in_progress',
            style: { stroke: '#64748b' },
          });
        }
      });
    });

    setNodes(newNodes);
    setEdges(newEdges);
  }, [components, currentComponent]);

  const calculatePosition = (index: number, total: number): { x: number; y: number } => {
    const radius = 250;
    const centerX = 400;
    const centerY = 300;
    const angle = (index / total) * 2 * Math.PI;

    return {
      x: centerX + radius * Math.cos(angle),
      y: centerY + radius * Math.sin(angle),
    };
  };

  return (
    <div className="architecture-canvas">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        connectionMode={ConnectionMode.Loose}
        fitView
      >
        <Background color="#1e293b" gap={16} />
        <Controls />
        <MiniMap 
          nodeColor={(node) => {
            const comp = node.data.component as Component;
            const colors: Record<string, string> = {
              not_started: '#475569',
              in_progress: '#3b82f6',
              completed: '#10b981',
              error: '#ef4444',
              blocked: '#f59e0b',
            };
            return colors[comp.status] || '#475569';
          }}
          maskColor="rgba(15, 23, 42, 0.8)"
        />
      </ReactFlow>
    </div>
  );
};

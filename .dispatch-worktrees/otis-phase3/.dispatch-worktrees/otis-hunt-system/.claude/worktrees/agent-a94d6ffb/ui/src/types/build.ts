/**
 * Build System Types
 * Type definitions for the build monitoring and execution system
 */

export type ComponentStatus = 'not_started' | 'in_progress' | 'completed' | 'error' | 'blocked';

export interface Component {
  id: string;
  name: string;
  type: 'frontend' | 'backend' | 'database' | 'service' | 'api';
  status: ComponentStatus;
  progress: number; // 0-100
  dependencies: string[]; // Component IDs
  files: string[];
  testsPass: boolean;
  startTime?: number;
  endTime?: number;
  error?: string;
}

export interface Feature {
  id: string;
  name: string;
  description: string;
  priority: 'high' | 'medium' | 'low';
  component: string; // Component ID
  status: ComponentStatus;
  progress: number;
  tasks: Task[];
  estimatedTime: number;
  actualTime?: number;
}

export interface Task {
  id: string;
  name: string;
  completed: boolean;
  timestamp?: number;
}

export interface BuildSession {
  id: string;
  projectName: string;
  projectAlias: string;
  projectPath: string;
  startTime: number;
  endTime?: number;
  status: 'initializing' | 'running' | 'paused' | 'completed' | 'error';
  components: Component[];
  features: Feature[];
  currentComponent?: string;
  currentFeature?: string;
}

export interface TerminalLine {
  id: string;
  timestamp: number;
  type: 'stdout' | 'stderr' | 'info' | 'error' | 'success';
  content: string;
}

export interface BuildMetrics {
  totalComponents: number;
  completedComponents: number;
  totalFeatures: number;
  completedFeatures: number;
  totalTime: number;
  estimatedTimeRemaining: number;
  linesOfCode: number;
  testsWritten: number;
  testsPassing: number;
}

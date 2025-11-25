import { Component, Feature, Task } from '../stores/buildStore';

export interface ParsedArchitecture {
  components: Component[];
  features: Feature[];
  dependencies: Map<string, string[]>;
}

export interface PRDData {
  architecture?: {
    components?: Array<{
      name: string;
      type: string;
      description?: string;
      dependencies?: string[];
    }>;
  };
  features?: Array<{
    name: string;
    description: string;
    priority?: string;
    component?: string;
    tasks?: string[];
    estimatedTime?: number;
  }>;
}

export class ArchitectureParser {
  parse(prdData: PRDData): ParsedArchitecture {
    const components = this.parseComponents(prdData);
    const features = this.parseFeatures(prdData, components);
    const dependencies = this.extractDependencies(prdData);

    return { components, features, dependencies };
  }

  private parseComponents(prdData: PRDData): Component[] {
    if (!prdData.architecture?.components) return [];

    return prdData.architecture.components.map((comp, index) => ({
      id: this.generateId(comp.name),
      name: comp.name,
      type: this.mapComponentType(comp.type),
      status: 'not_started' as const,
      progress: 0,
      dependencies: comp.dependencies || [],
      files: [],
      testsPass: false,
    }));
  }

  private parseFeatures(prdData: PRDData, components: Component[]): Feature[] {
    if (!prdData.features) return [];

    return prdData.features.map((feat, index) => {
      const componentId = this.findComponentId(feat.component, components);
      const tasks = this.parseTasks(feat.tasks || []);

      return {
        id: this.generateId(feat.name),
        name: feat.name,
        description: feat.description,
        priority: this.mapPriority(feat.priority),
        component: componentId,
        status: 'not_started' as const,
        progress: 0,
        tasks,
        estimatedTime: feat.estimatedTime || this.estimateTime(tasks.length),
      };
    });
  }

  private parseTasks(taskNames: string[]): Task[] {
    return taskNames.map((name, index) => ({
      id: `task-${Date.now()}-${index}`,
      name,
      completed: false,
    }));
  }

  private extractDependencies(prdData: PRDData): Map<string, string[]> {
    const deps = new Map<string, string[]>();

    if (prdData.architecture?.components) {
      prdData.architecture.components.forEach((comp) => {
        const id = this.generateId(comp.name);
        const compDeps = (comp.dependencies || []).map((dep) => this.generateId(dep));
        deps.set(id, compDeps);
      });
    }

    return deps;
  }

  private generateId(name: string): string {
    return name
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-|-$/g, '');
  }

  private mapComponentType(type: string): Component['type'] {
    const typeMap: Record<string, Component['type']> = {
      frontend: 'frontend',
      ui: 'frontend',
      client: 'frontend',
      backend: 'backend',
      server: 'backend',
      api: 'api',
      rest: 'api',
      graphql: 'api',
      database: 'database',
      db: 'database',
      storage: 'database',
      service: 'service',
      worker: 'service',
      queue: 'service',
    };

    const normalized = type.toLowerCase();
    return typeMap[normalized] || 'service';
  }

  private mapPriority(priority?: string): Feature['priority'] {
    if (!priority) return 'medium';

    const normalized = priority.toLowerCase();
    if (normalized.includes('high') || normalized.includes('critical')) return 'high';
    if (normalized.includes('low')) return 'low';
    return 'medium';
  }

  private findComponentId(componentName: string | undefined, components: Component[]): string {
    if (!componentName) return components[0]?.id || 'unknown';

    const normalized = componentName.toLowerCase();
    const found = components.find((c) => c.name.toLowerCase().includes(normalized));
    return found?.id || components[0]?.id || 'unknown';
  }

  private estimateTime(taskCount: number): number {
    return taskCount * 30;
  }

  parseCheckpoint(checkpointData: any): Partial<Component> | Partial<Feature> | null {
    if (!checkpointData) return null;

    if (checkpointData.component) {
      return {
        id: checkpointData.component.id,
        status: checkpointData.component.status,
        progress: checkpointData.component.progress || 0,
        files: checkpointData.component.files || [],
        testsPass: checkpointData.component.tests_pass || false,
      };
    }

    if (checkpointData.feature) {
      return {
        id: checkpointData.feature.id,
        status: checkpointData.feature.status,
        progress: checkpointData.feature.progress || 0,
        tasks: checkpointData.feature.tasks?.map((t: any) => ({
          id: t.id,
          name: t.name,
          completed: t.completed || false,
          timestamp: t.timestamp,
        })),
      };
    }

    return null;
  }

  calculateOverallProgress(components: Component[]): number {
    if (components.length === 0) return 0;
    const total = components.reduce((sum, comp) => sum + comp.progress, 0);
    return Math.round(total / components.length);
  }

  getComponentsByStatus(components: Component[], status: Component['status']): Component[] {
    return components.filter((c) => c.status === status);
  }

  getBlockedComponents(components: Component[], dependencies: Map<string, string[]>): Component[] {
    return components.filter((comp) => {
      if (comp.status !== 'blocked') return false;

      const deps = dependencies.get(comp.id) || [];
      return deps.some((depId) => {
        const dep = components.find((c) => c.id === depId);
        return dep && dep.status !== 'completed';
      });
    });
  }

  validateDependencies(components: Component[], dependencies: Map<string, string[]>): string[] {
    const errors: string[] = [];
    const componentIds = new Set(components.map((c) => c.id));

    dependencies.forEach((deps, compId) => {
      if (!componentIds.has(compId)) {
        errors.push(`Component ${compId} not found in components list`);
      }

      deps.forEach((depId) => {
        if (!componentIds.has(depId)) {
          errors.push(`Dependency ${depId} of ${compId} not found`);
        }
      });
    });

    const visited = new Set<string>();
    const recursionStack = new Set<string>();

    const hasCycle = (id: string): boolean => {
      visited.add(id);
      recursionStack.add(id);

      const deps = dependencies.get(id) || [];
      for (const depId of deps) {
        if (!visited.has(depId)) {
          if (hasCycle(depId)) return true;
        } else if (recursionStack.has(depId)) {
          errors.push(`Circular dependency detected: ${id} -> ${depId}`);
          return true;
        }
      }

      recursionStack.delete(id);
      return false;
    };

    componentIds.forEach((id) => {
      if (!visited.has(id)) {
        hasCycle(id);
      }
    });

    return errors;
  }
}

export const architectureParser = new ArchitectureParser();

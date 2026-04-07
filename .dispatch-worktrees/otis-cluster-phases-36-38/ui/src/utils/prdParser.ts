/**
 * PRD Parser - Converts PROJECT_SPEC.md markdown to structured data
 * Parses features, user stories, technical requirements, diagrams, etc.
 */

export interface Feature {
  id: string;
  title: string;
  priority: 'high' | 'medium' | 'low';
  status: 'planned' | 'in_progress' | 'completed' | 'discovered';
  description: string;
  acceptance_criteria: string;
  version?: string;
}

export interface TechnicalRequirements {
  frontend: string;
  backend: string;
  database: string;
  infrastructure: string;
}

export interface ExternalService {
  name: string;
  provider: string;
  endpoints: string[];
  authentication: string;
  rateLimits: string;
  dataRefresh: string;
  fallback: string;
  envVars: string[];
}

export interface PRDData {
  project_name: string;
  version: string;
  template: 'quick' | 'standard' | 'complete';
  created: string;
  overview: {
    executive_summary: string;
    goals: string;
    target_users: string;
  };
  features: Feature[];
  user_stories: string[];
  technical_requirements: TechnicalRequirements;
  external_services: ExternalService[];
  architecture_diagram: string | null;
  success_criteria: string[];
  dependencies: string[];
  effort_estimates: Record<string, string>;
}

/**
 * Parse PROJECT_SPEC.md markdown into structured data
 */
export function parsePRD(markdown: string): PRDData {
  const lines = markdown.split('\n');

  // Initialize result
  const result: PRDData = {
    project_name: '',
    version: '1.0.0',
    template: 'standard',
    created: new Date().toISOString(),
    overview: {
      executive_summary: '',
      goals: '',
      target_users: '',
    },
    features: [],
    user_stories: [],
    technical_requirements: {
      frontend: '',
      backend: '',
      database: '',
      infrastructure: '',
    },
    external_services: [],
    architecture_diagram: null,
    success_criteria: [],
    dependencies: [],
    effort_estimates: {},
  };

  let currentSection = '';
  let currentFeature: Partial<Feature> | null = null;
  let currentService: Partial<ExternalService> | null = null;
  let inCodeBlock = false;
  let codeBlockLang = '';
  let codeBlockContent: string[] = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();

    // Handle code blocks
    if (trimmed.startsWith('```')) {
      if (!inCodeBlock) {
        inCodeBlock = true;
        codeBlockLang = trimmed.substring(3).trim();
        codeBlockContent = [];
      } else {
        inCodeBlock = false;
        // Process completed code block
        if (codeBlockLang === 'mermaid') {
          result.architecture_diagram = codeBlockContent.join('\n');
        }
        codeBlockLang = '';
        codeBlockContent = [];
      }
      continue;
    }

    if (inCodeBlock) {
      codeBlockContent.push(line);
      continue;
    }

    // Parse metadata
    if (trimmed.startsWith('**Version:**')) {
      result.version = trimmed.replace('**Version:**', '').trim();
      continue;
    }
    if (trimmed.startsWith('**Created:**')) {
      result.created = trimmed.replace('**Created:**', '').trim();
      continue;
    }
    if (trimmed.startsWith('**Template:**')) {
      const template = trimmed.replace('**Template:**', '').trim().toLowerCase();
      if (template === 'quick' || template === 'standard' || template === 'complete') {
        result.template = template;
      }
      continue;
    }

    // Parse section headers
    if (trimmed.startsWith('# ') && !trimmed.startsWith('##')) {
      result.project_name = trimmed.substring(2).trim();
      continue;
    }

    if (trimmed.startsWith('## ')) {
      currentSection = trimmed.substring(3).trim().toLowerCase();
      currentFeature = null;
      currentService = null;
      continue;
    }

    // Parse features
    if (currentSection === 'features') {
      if (trimmed.startsWith('### ')) {
        // Save previous feature
        if (currentFeature && currentFeature.title) {
          result.features.push(currentFeature as Feature);
        }

        // Start new feature
        const title = trimmed.substring(4).trim();
        currentFeature = {
          id: `feature-${Date.now()}-${result.features.length}`,
          title,
          priority: 'medium',
          status: 'planned',
          description: '',
          acceptance_criteria: '',
        };
        continue;
      }

      if (currentFeature) {
        if (trimmed.startsWith('**Priority:**')) {
          const priority = trimmed.replace('**Priority:**', '').trim().toLowerCase();
          if (priority === 'high' || priority === 'medium' || priority === 'low') {
            currentFeature.priority = priority;
          }
        } else if (trimmed.startsWith('**Status:**')) {
          const status = trimmed.replace('**Status:**', '').trim().toLowerCase();
          if (status === 'planned' || status === 'in_progress' || status === 'completed' || status === 'discovered') {
            currentFeature.status = status;
          }
        } else if (trimmed.startsWith('**Description:**')) {
          currentFeature.description = trimmed.replace('**Description:**', '').trim();
        } else if (trimmed.startsWith('**Acceptance Criteria:**')) {
          // Start collecting criteria
          continue;
        } else if (trimmed.startsWith('- [ ]') || trimmed.startsWith('- [x]')) {
          if (!currentFeature.acceptance_criteria) {
            currentFeature.acceptance_criteria = trimmed;
          } else {
            currentFeature.acceptance_criteria += '\n' + trimmed;
          }
        } else if (trimmed && !trimmed.startsWith('**')) {
          // Add to description if not empty and not a metadata field
          if (currentFeature.description) {
            currentFeature.description += ' ' + trimmed;
          } else {
            currentFeature.description = trimmed;
          }
        }
      }
      continue;
    }

    // Parse overview
    if (currentSection === 'project overview') {
      if (trimmed.startsWith('**Executive Summary:**')) {
        let summary = trimmed.replace('**Executive Summary:**', '').trim();
        // Collect multi-line summary
        for (let j = i + 1; j < lines.length && !lines[j].trim().startsWith('**'); j++) {
          if (lines[j].trim()) {
            summary += ' ' + lines[j].trim();
          }
          i = j;
        }
        result.overview.executive_summary = summary;
        continue;
      }
      if (trimmed.startsWith('**Goals & Objectives:**')) {
        let goals = '';
        for (let j = i + 1; j < lines.length && !lines[j].trim().startsWith('**'); j++) {
          if (lines[j].trim().startsWith('-')) {
            goals += lines[j].trim() + '\n';
          }
          i = j;
        }
        result.overview.goals = goals.trim();
        continue;
      }
      if (trimmed.startsWith('**Target Users:**')) {
        let users = '';
        for (let j = i + 1; j < lines.length && !lines[j].trim().startsWith('**') && !lines[j].trim().startsWith('##'); j++) {
          if (lines[j].trim()) {
            users += lines[j].trim() + '\n';
          }
          i = j;
        }
        result.overview.target_users = users.trim();
        continue;
      }
    }

    // Parse user stories
    if (currentSection === 'user stories') {
      if (trimmed.startsWith('- As a ') || trimmed.startsWith('As a ')) {
        result.user_stories.push(trimmed.replace(/^- /, ''));
      }
      continue;
    }

    // Parse technical requirements
    if (currentSection === 'technical requirements') {
      if (trimmed.startsWith('**Frontend:**')) {
        let content = '';
        for (let j = i + 1; j < lines.length && !lines[j].trim().startsWith('**'); j++) {
          if (lines[j].trim()) {
            content += lines[j].trim() + '\n';
          }
          i = j;
        }
        result.technical_requirements.frontend = content.trim();
        continue;
      }
      if (trimmed.startsWith('**Backend:**')) {
        let content = '';
        for (let j = i + 1; j < lines.length && !lines[j].trim().startsWith('**'); j++) {
          if (lines[j].trim()) {
            content += lines[j].trim() + '\n';
          }
          i = j;
        }
        result.technical_requirements.backend = content.trim();
        continue;
      }
      if (trimmed.startsWith('**Database:**')) {
        let content = '';
        for (let j = i + 1; j < lines.length && !lines[j].trim().startsWith('**'); j++) {
          if (lines[j].trim()) {
            content += lines[j].trim() + '\n';
          }
          i = j;
        }
        result.technical_requirements.database = content.trim();
        continue;
      }
      if (trimmed.startsWith('**External Services & APIs:**')) {
        currentSection = 'external services';
        continue;
      }
    }

    // Parse external services
    if (currentSection === 'external services') {
      if (trimmed.startsWith('### ')) {
        // Save previous service
        if (currentService && currentService.name) {
          result.external_services.push(currentService as ExternalService);
        }

        // Start new service
        currentService = {
          name: trimmed.substring(4).trim(),
          provider: '',
          endpoints: [],
          authentication: '',
          rateLimits: '',
          dataRefresh: '',
          fallback: '',
          envVars: [],
        };
        continue;
      }

      if (currentService) {
        if (trimmed.startsWith('- **Provider:**')) {
          currentService.provider = trimmed.replace('- **Provider:**', '').trim();
        } else if (trimmed.startsWith('- **Endpoints:**')) {
          currentService.endpoints = trimmed.replace('- **Endpoints:**', '').trim().split(',').map(e => e.trim());
        } else if (trimmed.startsWith('- **Authentication:**')) {
          currentService.authentication = trimmed.replace('- **Authentication:**', '').trim();
        } else if (trimmed.startsWith('- **Rate Limits:**')) {
          currentService.rateLimits = trimmed.replace('- **Rate Limits:**', '').trim();
        } else if (trimmed.startsWith('- **Data Refresh:**')) {
          currentService.dataRefresh = trimmed.replace('- **Data Refresh:**', '').trim();
        } else if (trimmed.startsWith('- **Fallback:**')) {
          currentService.fallback = trimmed.replace('- **Fallback:**', '').trim();
        } else if (trimmed.startsWith('- **Required Env Vars:**')) {
          currentService.envVars = trimmed.replace('- **Required Env Vars:**', '').trim().split(',').map(e => e.trim());
        }
      }
      continue;
    }

    // Parse success criteria
    if (currentSection === 'success criteria') {
      if (trimmed.startsWith('- [ ]') || trimmed.startsWith('- [x]')) {
        result.success_criteria.push(trimmed.replace(/^- \[[ x]\] /, ''));
      }
      continue;
    }

    // Parse dependencies
    if (currentSection === 'dependencies') {
      if (trimmed.startsWith('-')) {
        result.dependencies.push(trimmed.substring(1).trim());
      }
      continue;
    }

    // Parse effort estimates
    if (currentSection === 'effort estimates') {
      if (trimmed.startsWith('-')) {
        const parts = trimmed.substring(1).split(':');
        if (parts.length === 2) {
          result.effort_estimates[parts[0].trim()] = parts[1].trim();
        }
      }
      continue;
    }
  }

  // Save last feature if exists
  if (currentFeature && currentFeature.title) {
    result.features.push(currentFeature as Feature);
  }

  // Save last service if exists
  if (currentService && currentService.name) {
    result.external_services.push(currentService as ExternalService);
  }

  return result;
}

/**
 * Convert structured data back to PROJECT_SPEC.md markdown
 */
export function serializePRD(data: PRDData): string {
  let md = `# ${data.project_name}\n\n`;
  md += `**Version:** ${data.version}\n`;
  md += `**Created:** ${data.created}\n`;
  md += `**Template:** ${data.template}\n\n`;

  // Overview
  md += `## Project Overview\n\n`;
  md += `**Executive Summary:**\n${data.overview.executive_summary}\n\n`;
  md += `**Goals & Objectives:**\n${data.overview.goals}\n\n`;
  md += `**Target Users:**\n${data.overview.target_users}\n\n`;

  // Features
  md += `## Features\n\n`;
  data.features.forEach(feature => {
    md += `### ${feature.title}\n`;
    md += `**Priority:** ${feature.priority}\n`;
    md += `**Status:** ${feature.status}\n`;
    md += `**Description:** ${feature.description}\n`;
    if (feature.acceptance_criteria) {
      md += `**Acceptance Criteria:**\n${feature.acceptance_criteria}\n`;
    }
    md += `\n`;
  });

  // User Stories
  if (data.user_stories.length > 0) {
    md += `## User Stories\n\n`;
    data.user_stories.forEach(story => {
      md += `- ${story}\n`;
    });
    md += `\n`;
  }

  // Technical Requirements
  md += `## Technical Requirements\n\n`;
  if (data.technical_requirements.frontend) {
    md += `**Frontend:**\n${data.technical_requirements.frontend}\n\n`;
  }
  if (data.technical_requirements.backend) {
    md += `**Backend:**\n${data.technical_requirements.backend}\n\n`;
  }
  if (data.technical_requirements.database) {
    md += `**Database:**\n${data.technical_requirements.database}\n\n`;
  }

  // External Services
  if (data.external_services.length > 0) {
    md += `**External Services & APIs:**\n\n`;
    data.external_services.forEach(service => {
      md += `### ${service.name}\n`;
      md += `- **Provider:** ${service.provider}\n`;
      md += `- **Endpoints:** ${service.endpoints.join(', ')}\n`;
      md += `- **Authentication:** ${service.authentication}\n`;
      md += `- **Rate Limits:** ${service.rateLimits}\n`;
      md += `- **Data Refresh:** ${service.dataRefresh}\n`;
      md += `- **Fallback:** ${service.fallback}\n`;
      md += `- **Required Env Vars:** ${service.envVars.join(', ')}\n`;
      md += `\n`;
    });
  }

  // Architecture
  if (data.architecture_diagram) {
    md += `## Architecture\n\n`;
    md += '```mermaid\n';
    md += data.architecture_diagram;
    md += '\n```\n\n';
  }

  // Success Criteria
  if (data.success_criteria.length > 0) {
    md += `## Success Criteria\n\n`;
    data.success_criteria.forEach(criterion => {
      md += `- [ ] ${criterion}\n`;
    });
    md += `\n`;
  }

  // Dependencies
  if (data.dependencies.length > 0) {
    md += `## Dependencies\n\n`;
    data.dependencies.forEach(dep => {
      md += `- ${dep}\n`;
    });
    md += `\n`;
  }

  // Effort Estimates
  if (Object.keys(data.effort_estimates).length > 0) {
    md += `## Effort Estimates\n\n`;
    Object.entries(data.effort_estimates).forEach(([key, value]) => {
      md += `- ${key}: ${value}\n`;
    });
    md += `\n`;
  }

  md += `---\n`;

  return md;
}

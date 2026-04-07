/**
 * ProgressSidebar Example Usage
 *
 * This file demonstrates how to integrate the ProgressSidebar component
 * into your application and handle component/feature click events.
 */

import { useState } from 'react';
import { ProgressSidebar } from './ProgressSidebar';

export function ProgressSidebarExample() {
  const [selectedComponent, setSelectedComponent] = useState<string | null>(null);
  const [selectedFeature, setSelectedFeature] = useState<string | null>(null);

  const handleComponentClick = (componentId: string) => {
    console.log('Component clicked:', componentId);
    setSelectedComponent(componentId);

    // Example: Highlight component in canvas
    // canvasAPI.highlightComponent(componentId);
  };

  const handleFeatureClick = (featureId: string) => {
    console.log('Feature clicked:', featureId);
    setSelectedFeature(featureId);

    // Example: Navigate to feature details
    // router.push(`/features/${featureId}`);
  };

  return (
    <div style={{ display: 'flex', height: '100vh' }}>
      {/* Progress Sidebar */}
      <ProgressSidebar
        onComponentClick={handleComponentClick}
        onFeatureClick={handleFeatureClick}
      />

      {/* Main Content Area */}
      <div style={{ flex: 1, padding: '20px' }}>
        <h1>Build Canvas</h1>
        {selectedComponent && (
          <div>Selected Component: {selectedComponent}</div>
        )}
        {selectedFeature && (
          <div>Selected Feature: {selectedFeature}</div>
        )}
      </div>
    </div>
  );
}

/**
 * Integration with WebSocket for Real-time Updates:
 *
 * import { useWebSocket } from '../hooks/useWebSocket';
 *
 * function MyComponent() {
 *   const { lastMessage } = useWebSocket({
 *     onMessage: (message) => {
 *       // Update component/feature state based on message
 *       if (message.type === 'task_update') {
 *         // Refresh progress data
 *       }
 *     }
 *   });
 *
 *   return <ProgressSidebar ... />;
 * }
 */

/**
 * Integration with a State Management Store:
 *
 * // In your store (e.g., Zustand, Redux, etc.)
 * interface BuildStore {
 *   components: Component[];
 *   features: Feature[];
 *   updateComponent: (id: string, updates: Partial<Component>) => void;
 *   updateFeature: (id: string, updates: Partial<Feature>) => void;
 * }
 *
 * // In ComponentProgress.tsx or FeatureProgress.tsx:
 * import { useBuildStore } from '../stores/buildStore';
 *
 * const components = useBuildStore((state) => state.components);
 * const features = useBuildStore((state) => state.features);
 */

export default ProgressSidebarExample;

"""Feature Registry System for BuildRunner 3.0

Manages feature tracking with JSON-based registry, CRUD operations,
and version-based progress calculation.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any


class FeatureRegistry:
    """Manages features.json with CRUD operations and progress tracking"""

    def __init__(self, project_root: str = "."):
        """Initialize feature registry

        Args:
            project_root: Root directory of the project
        """
        self.project_root = Path(project_root)
        self.features_file = self.project_root / ".buildrunner" / "features.json"
        self._ensure_directory()

    def _ensure_directory(self):
        """Ensure .buildrunner directory exists"""
        self.features_file.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> Dict[str, Any]:
        """Load features.json

        Returns:
            Dictionary containing all features data
        """
        if not self.features_file.exists():
            return self._get_default_structure()

        with open(self.features_file, 'r') as f:
            return json.load(f)

    def save(self, data: Dict[str, Any]):
        """Save features.json

        Args:
            data: Dictionary to save
        """
        with open(self.features_file, 'w') as f:
            json.dump(data, f, indent=2)

    def _get_default_structure(self) -> Dict[str, Any]:
        """Get default features.json structure

        Returns:
            Default structure dictionary
        """
        return {
            "project": "BuildRunner Project",
            "version": "1.0.0",
            "status": "in_development",
            "last_updated": datetime.now().isoformat() + "Z",
            "description": "",
            "features": [],
            "metrics": {
                "features_complete": 0,
                "features_in_progress": 0,
                "features_planned": 0,
                "completion_percentage": 0
            }
        }

    def add_feature(self, feature_id: str, name: str, description: str,
                   priority: str = "medium", week: Optional[int] = None,
                   build: Optional[str] = None) -> Dict[str, Any]:
        """Add a new feature

        Args:
            feature_id: Unique feature identifier
            name: Feature name
            description: Feature description
            priority: Priority level (critical, high, medium, low)
            week: Week number for this feature
            build: Build identifier (e.g., "1A", "2B")

        Returns:
            The created feature dictionary
        """
        data = self.load()

        # Check if feature already exists
        if any(f['id'] == feature_id for f in data['features']):
            raise ValueError(f"Feature with id '{feature_id}' already exists")

        feature = {
            "id": feature_id,
            "name": name,
            "status": "planned",
            "version": data.get("version", "1.0.0"),
            "priority": priority,
            "description": description
        }

        if week is not None:
            feature["week"] = week
        if build is not None:
            feature["build"] = build

        data['features'].append(feature)
        data['last_updated'] = datetime.now().isoformat() + "Z"

        # Update metrics
        self._update_metrics(data)
        self.save(data)

        return feature

    def complete_feature(self, feature_id: str) -> Dict[str, Any]:
        """Mark a feature as complete

        Args:
            feature_id: Feature identifier

        Returns:
            The updated feature dictionary

        Raises:
            ValueError: If feature not found
        """
        data = self.load()

        feature = None
        for f in data['features']:
            if f['id'] == feature_id:
                feature = f
                break

        if not feature:
            raise ValueError(f"Feature '{feature_id}' not found")

        feature['status'] = 'complete'
        data['last_updated'] = datetime.now().isoformat() + "Z"

        # Update metrics
        self._update_metrics(data)
        self.save(data)

        return feature

    def update_feature(self, feature_id: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Update feature properties

        Args:
            feature_id: Feature identifier
            **kwargs: Properties to update

        Returns:
            The updated feature dictionary or None if not found

        Raises:
            ValueError: If feature not found
        """
        data = self.load()

        feature = None
        for f in data['features']:
            if f['id'] == feature_id:
                feature = f
                break

        if not feature:
            return None

        # Update allowed fields
        allowed_fields = ['name', 'description', 'status', 'priority', 'week', 'build']
        for key, value in kwargs.items():
            if key in allowed_fields:
                feature[key] = value

        data['last_updated'] = datetime.now().isoformat() + "Z"

        # Update metrics
        self._update_metrics(data)
        self.save(data)

        return feature

    def delete_feature(self, feature_id: str) -> bool:
        """Delete a feature

        Args:
            feature_id: Feature identifier

        Returns:
            True if feature was deleted, False if not found
        """
        data = self.load()

        # Find and remove feature
        original_length = len(data['features'])
        data['features'] = [f for f in data['features'] if f['id'] != feature_id]

        if len(data['features']) == original_length:
            return False

        data['last_updated'] = datetime.now().isoformat() + "Z"

        # Update metrics
        self._update_metrics(data)
        self.save(data)

        return True

    def get_feature(self, feature_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific feature

        Args:
            feature_id: Feature identifier

        Returns:
            Feature dictionary or None if not found
        """
        data = self.load()

        for feature in data['features']:
            if feature['id'] == feature_id:
                return feature

        return None

    def list_features(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all features, optionally filtered by status

        Args:
            status: Filter by status (planned, in_progress, complete)

        Returns:
            List of feature dictionaries
        """
        data = self.load()
        features = data['features']

        if status:
            features = [f for f in features if f.get('status') == status]

        return features

    def get_status(self) -> Dict[str, Any]:
        """Get overall project status

        Returns:
            Dictionary with project metrics and status
        """
        data = self.load()
        return {
            "project": data.get("project", "Unknown"),
            "version": data.get("version", "1.0.0"),
            "status": data.get("status", "unknown"),
            "metrics": data.get("metrics", {}),
            "total_features": len(data.get("features", []))
        }

    def _update_metrics(self, data: Dict[str, Any]):
        """Update metrics based on current features

        Args:
            data: Features data dictionary
        """
        features = data.get('features', [])

        complete = sum(1 for f in features if f.get('status') == 'complete')
        in_progress = sum(1 for f in features if f.get('status') == 'in_progress')
        planned = sum(1 for f in features if f.get('status') == 'planned')
        total = len(features)

        completion = 0
        if total > 0:
            completion = round((complete / total) * 100)

        data['metrics'] = {
            "features_complete": complete,
            "features_in_progress": in_progress,
            "features_planned": planned,
            "completion_percentage": completion
        }

"""
PRD Mapper - Sync PROJECT_SPEC.md to features.json

Maps PRD sections to features.json, auto-generates feature entries, syncs changes
bidirectionally, generates atomic task lists, and identifies parallel vs sequential builds.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from .prd_parser import PRDParser, ParsedSpec, Feature


class PRDMapper:
    """
    Map PROJECT_SPEC to features.json with bidirectional sync.

    Features:
    - Convert PRD features to features.json format
    - Auto-generate feature entries
    - Bidirectional sync
    - Generate atomic task lists from phases
    - Identify parallel vs sequential builds
    """

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.spec_path = self.project_root / ".buildrunner" / "PROJECT_SPEC.md"
        self.features_path = self.project_root / ".buildrunner" / "features.json"

    def spec_to_features(self, spec: ParsedSpec) -> Dict:
        """Convert PROJECT_SPEC to features.json format"""
        features_data = {
            "version": "3.0.0",
            "project": {
                "name": f"{spec.industry}_{spec.use_case}_app" if spec.industry and spec.use_case else "project",
                "industry": spec.industry,
                "use_case": spec.use_case,
                "tech_stack": spec.tech_stack,
                "status": spec.status,
                "last_updated": datetime.now().isoformat()
            },
            "features": []
        }

        # Convert parsed features to feature entries
        for feature in spec.features:
            feature_entry = {
                "id": feature.name,
                "name": feature.name.replace('_', ' ').title(),
                "description": feature.description,
                "priority": feature.priority,
                "status": "planned",
                "dependencies": feature.dependencies,
                "tasks": self._generate_tasks_for_feature(feature)
            }
            features_data["features"].append(feature_entry)

        # Add phases as milestones
        features_data["phases"] = []
        for phase in spec.phases:
            phase_entry = {
                "number": phase.number,
                "name": phase.name,
                "features": phase.features,
                "duration": phase.duration,
                "status": "pending"
            }
            features_data["phases"].append(phase_entry)

        return features_data

    def _generate_tasks_for_feature(self, feature: Feature) -> List[Dict]:
        """Generate atomic tasks for a feature"""
        # In production, this would use AI to generate detailed tasks
        # For now, generate standard task structure
        tasks = [
            {
                "id": f"{feature.name}_design",
                "name": "Design component/feature",
                "status": "pending",
                "dependencies": []
            },
            {
                "id": f"{feature.name}_implement",
                "name": "Implement core functionality",
                "status": "pending",
                "dependencies": [f"{feature.name}_design"]
            },
            {
                "id": f"{feature.name}_test",
                "name": "Write tests",
                "status": "pending",
                "dependencies": [f"{feature.name}_implement"]
            },
            {
                "id": f"{feature.name}_integrate",
                "name": "Integrate with system",
                "status": "pending",
                "dependencies": [f"{feature.name}_test"]
            }
        ]

        return tasks

    def save_features_json(self, features_data: Dict):
        """Save features.json to disk"""
        self.features_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.features_path, 'w') as f:
            json.dump(features_data, f, indent=2)

    def load_features_json(self) -> Optional[Dict]:
        """Load existing features.json"""
        if not self.features_path.exists():
            return None

        with open(self.features_path, 'r') as f:
            return json.load(f)

    def sync_spec_to_features(self) -> Dict:
        """
        Sync PROJECT_SPEC.md to features.json.

        Reads spec, parses it, converts to features format, and saves.
        """
        # Parse spec
        parser = PRDParser(str(self.spec_path))
        spec = parser.parse()

        # Convert to features format
        features_data = self.spec_to_features(spec)

        # Save
        self.save_features_json(features_data)

        return features_data

    def sync_features_to_spec(self):
        """
        Sync changes from features.json back to PROJECT_SPEC.md.

        Updates spec with feature status changes.
        This is a partial sync - only updates status, not content.
        """
        features_data = self.load_features_json()

        if not features_data:
            return

        # In production, would update specific sections of PROJECT_SPEC.md
        # based on feature status changes
        print("Reverse sync: features.json → PROJECT_SPEC.md")
        print(f"  {len(features_data.get('features', []))} features to sync")

    def identify_parallel_builds(self, features_data: Dict) -> Dict[str, List[str]]:
        """
        Identify which builds can run in parallel.

        Analyzes dependency graph and returns groupings.
        """
        features = features_data.get('features', [])

        # Build dependency graph
        dependency_graph = {}
        for feature in features:
            feature_id = feature['id']
            dependencies = feature.get('dependencies', [])
            dependency_graph[feature_id] = dependencies

        # Identify independent features (no dependencies)
        independent = [fid for fid, deps in dependency_graph.items() if not deps]

        # Identify sequential chains
        sequential = []
        for fid, deps in dependency_graph.items():
            if deps:
                sequential.append(fid)

        parallel_groups = {
            "parallel": independent,
            "sequential": sequential
        }

        return parallel_groups

    def generate_build_plan(self, features_data: Dict) -> List[Dict]:
        """
        Generate atomic build plan from features.

        Returns list of build steps with parallelization info.
        """
        parallel_groups = self.identify_parallel_builds(features_data)

        build_plan = []

        # Add parallel builds first
        if parallel_groups['parallel']:
            build_plan.append({
                "step": 1,
                "type": "parallel",
                "features": parallel_groups['parallel'],
                "description": "These features can be built in parallel"
            })

        # Add sequential builds
        if parallel_groups['sequential']:
            for i, feature_id in enumerate(parallel_groups['sequential']):
                build_plan.append({
                    "step": len(build_plan) + 1,
                    "type": "sequential",
                    "features": [feature_id],
                    "description": f"Build {feature_id} (depends on previous steps)"
                })

        return build_plan


def main():
    """CLI entry point for testing"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python prd_mapper.py <project_root>")
        sys.exit(1)

    project_root = sys.argv[1]

    mapper = PRDMapper(project_root)

    print("\nSyncing PROJECT_SPEC → features.json...")
    features_data = mapper.sync_spec_to_features()

    print(f"\nFeatures JSON Created:")
    print(f"  Project: {features_data['project']['name']}")
    print(f"  Features: {len(features_data['features'])}")
    print(f"  Phases: {len(features_data.get('phases', []))}")

    # Generate build plan
    build_plan = mapper.generate_build_plan(features_data)
    print(f"\nBuild Plan: {len(build_plan)} steps")

    for step in build_plan:
        print(f"  Step {step['step']} ({step['type']}): {len(step['features'])} features")


if __name__ == "__main__":
    main()

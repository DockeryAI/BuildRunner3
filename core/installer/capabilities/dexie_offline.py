"""Dexie offline capability installer."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from core.installer.capabilities import CapabilityResult, write_template_if_missing

if TYPE_CHECKING:
    from core.project_type.facets import ProjectFacets


class DexieOfflineCapability:
    """Install the Dexie offline storage scaffold."""

    name = "dexie_offline"

    def install(
        self,
        target_repo: Path,
        *,
        declared_facets: ProjectFacets | None = None,
    ) -> CapabilityResult:
        repo_root = Path(target_repo).resolve()
        result = CapabilityResult(
            name=self.name,
            package_suggestions={"dexie": "^4"},
        )

        write_template_if_missing(
            asset_relative_path="templates/capabilities/dexie-offline/db.ts.template",
            target_path=repo_root / "src" / "db.ts",
            result=result,
        )

        _ = declared_facets
        return result

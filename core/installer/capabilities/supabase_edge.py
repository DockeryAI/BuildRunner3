"""Supabase Edge capability installer."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from core.installer.capabilities import CapabilityResult, write_template_if_missing
from core.project_type.facets import Capability

if TYPE_CHECKING:
    from core.project_type.facets import ProjectFacets


class SupabaseEdgeCapability:
    """Install shared Supabase Edge logging helpers."""

    name = "supabase_edge"

    def install(
        self,
        target_repo: Path,
        *,
        declared_facets: ProjectFacets | None = None,
    ) -> CapabilityResult:
        repo_root = Path(target_repo).resolve()
        result = CapabilityResult(name=self.name)

        write_template_if_missing(
            asset_relative_path="templates/capabilities/supabase-edge/_shared/devLog.ts",
            target_path=repo_root / "supabase" / "functions" / "_shared" / "devLog.ts",
            result=result,
        )

        if (
            declared_facets is not None
            and Capability.capacitor in declared_facets.capabilities
        ):
            result.notes.append(
                "Capacitor is enabled; consider a follow-up device_logs migration so "
                "native device events land alongside edge _debug output."
            )

        return result

"""PWA capability installer."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from core.installer.capabilities import CapabilityResult, write_template_if_missing

if TYPE_CHECKING:
    from core.project_type.facets import ProjectFacets


class PwaCapability:
    """Install the PWA service worker scaffold."""

    name = "pwa"

    def install(
        self,
        target_repo: Path,
        *,
        declared_facets: ProjectFacets | None = None,
    ) -> CapabilityResult:
        repo_root = Path(target_repo).resolve()
        result = CapabilityResult(
            name=self.name,
            package_suggestions={"vite-plugin-pwa": "^0.21"},
            notes=[
                "Register the Vite PWA plugin in vite.config and point it at src/sw.ts; "
                "this phase does not codemod vite.config for you."
            ],
        )

        write_template_if_missing(
            asset_relative_path="templates/capabilities/pwa/sw.ts.template",
            target_path=repo_root / "src" / "sw.ts",
            result=result,
        )

        _ = declared_facets
        return result

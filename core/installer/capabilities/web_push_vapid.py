"""Web push VAPID capability installer."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from core.installer.capabilities import CapabilityResult, write_template_if_missing

if TYPE_CHECKING:
    from core.project_type.facets import ProjectFacets


class WebPushVapidCapability:
    """Install a browser push debugging component."""

    name = "web_push_vapid"

    def install(
        self,
        target_repo: Path,
        *,
        declared_facets: ProjectFacets | None = None,
    ) -> CapabilityResult:
        repo_root = Path(target_repo).resolve()
        result = CapabilityResult(name=self.name)

        write_template_if_missing(
            asset_relative_path="templates/capabilities/web-push-vapid/PushDebug.tsx.template",
            target_path=repo_root / "src" / "components" / "PushDebug.tsx",
            result=result,
        )

        _ = declared_facets
        return result

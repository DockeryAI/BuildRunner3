"""Capacitor capability installer."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from core.installer.capabilities import (
    CapabilityConflictError,
    CapabilityResult,
    assert_no_capability_conflicts,
    write_template_if_missing,
)
from core.project_type.facets import Capability

if TYPE_CHECKING:
    from core.project_type.facets import ProjectFacets


class CapacitorCapability:
    """Install the Capacitor bridge scaffold."""

    name = "capacitor"

    def install(
        self,
        target_repo: Path,
        *,
        declared_facets: ProjectFacets | None = None,
    ) -> CapabilityResult:
        if (
            declared_facets is not None
            and Capability.pwa in declared_facets.capabilities
        ):
            raise CapabilityConflictError(
                "Cannot install capability 'capacitor' while 'pwa' is requested: "
                "capacitor wraps the same service-worker boundary."
            )

        assert_no_capability_conflicts(declared_facets)

        repo_root = Path(target_repo).resolve()
        result = CapabilityResult(
            name=self.name,
            package_suggestions={
                "@capacitor/core": "^8",
                "@capacitor/cli": "^8",
                "@capacitor/ios": "^8",
            },
            notes=[
                "Swap <BRLogger /> for <BRLoggerCapacitor /> in the React entry point; "
                "this phase only drops the files."
            ],
        )

        for asset_relative_path, target_path in (
            (
                "templates/capabilities/capacitor/capacitor.config.ts.template",
                repo_root / "capacitor.config.ts",
            ),
            (
                "templates/capabilities/capacitor/captures/BRLoggerCapacitor.tsx",
                repo_root / "src" / "captures" / "capacitor" / "BRLoggerCapacitor.tsx",
            ),
            (
                "templates/capabilities/capacitor/captures/capacitorCapture.ts",
                repo_root / "src" / "captures" / "capacitor" / "capacitorCapture.ts",
            ),
        ):
            write_template_if_missing(
                asset_relative_path=asset_relative_path,
                target_path=target_path,
                result=result,
            )

        return result

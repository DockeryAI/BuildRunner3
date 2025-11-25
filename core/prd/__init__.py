"""PRD Controller - Single source of truth for PROJECT_SPEC"""

from .prd_controller import PRDController, PRDVersion, PRDChangeEvent, get_prd_controller

__all__ = ["PRDController", "PRDVersion", "PRDChangeEvent", "get_prd_controller"]

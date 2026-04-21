"""API Routes for BuildRunner Web UI.

Submodules are imported on demand (lazy) to avoid pulling heavy deps
(anthropic, openai) into microservice entry points like
api.routes.context:app that only need a single router.
"""

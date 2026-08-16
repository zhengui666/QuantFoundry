"""Compatibility alias plus the UX-001 control-plane bootstrap."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from app import control_plane as _control_plane
from app import generated_api_models as _control_models
from quantfoundry.api import app as _canonical
from quantfoundry.contracts.openapi import api_models as _canonical_models

_canonical.app.state.environment = _canonical.ENVIRONMENT
_canonical.app.state.domain_database_available = False
for _name in (
    "GeneralAccessKeyLoginRequest",
    "GeneralAccessKeyMetadata",
    "GeneralAccessKeyList",
    "GeneralAccessKeyCreateRequest",
    "GeneralAccessKeyRenameRequest",
    "GeneralAccessKeyIssued",
    "SessionBootstrapResponse",
    "SetupCompleteRequest",
    "OwnerSessionView",
    "ConfigurationCatalog",
    "ConfigurationActive",
    "ConfigurationCandidateRequest",
    "ConfigurationCandidate",
    "ConfigurationValidationResult",
    "ConfigurationActivateRequest",
    "ConfigurationRollbackRequest",
    "ConfigurationValueView",
    "ConfigurationConsumerState",
    "DatabaseConnectionCandidateRequest",
    "DatabaseConnectionCandidate",
    "DatabaseConnectionCheck",
    "DatabaseConnectionValidationResult",
    "DatabaseConnectionStatus",
    "ApiProblem",
    "CanonicalErrorCode",
    "FieldError",
    "ProblemContext",
):
    _canonical_models.SCHEMA_MODELS[_name] = getattr(_control_models, _name)
_control_router = _control_plane.build_router()
# Register the control routes directly so the canonical contract pass sees
# their operation metadata (FastAPI's included-router wrapper hides them).
_canonical.app.router.routes.extend(_control_router.routes)
# UX-001 owns setup completion through shared configuration activation.
_canonical.app.router.routes[:] = [
    route
    for route in _canonical.app.router.routes
    if not (
        getattr(route, "path", None) == "/api/v1/setup/complete"
        and getattr(getattr(route, "endpoint", None), "__module__", "")
        == "quantfoundry.api.app"
    )
]
_canonical._configure_contract_routes()
sys.modules[__name__] = _canonical

_control_plane.init_control_db()
_control_plane.restore_active_domain_database()

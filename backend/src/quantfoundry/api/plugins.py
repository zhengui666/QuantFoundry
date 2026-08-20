"""Plugin catalog and lifecycle API."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from quantfoundry.api.dependencies import get_session
from quantfoundry.db.repositories import (
    get_plugin_release,
    list_plugin_releases,
    plugin_catalog,
)
from quantfoundry.errors import QfError
from quantfoundry.events import append_event
from quantfoundry.plugins.manager import activate_release, deactivate_release

router = APIRouter(prefix="/api/v1", tags=["plugins"])


class PluginReleaseView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    plugin_id: str
    distribution_name: str
    version: str
    api_version: str
    state: str
    is_default: bool
    descriptor_snapshot: dict[str, Any]
    last_error: str | None


def _view(release: Any) -> PluginReleaseView:
    return PluginReleaseView(
        id=release.id,
        plugin_id=release.plugin_id,
        distribution_name=release.distribution_name,
        version=release.version,
        api_version=release.api_version,
        state=release.state,
        is_default=release.is_default,
        descriptor_snapshot=release.descriptor_snapshot,
        last_error=release.last_error,
    )


@router.get("/plugins")
def list_plugins(session: Session = Depends(get_session)) -> list[dict[str, Any]]:
    return plugin_catalog(session)


@router.get("/plugin-releases", response_model=list[PluginReleaseView])
def releases(session: Session = Depends(get_session)) -> list[PluginReleaseView]:
    return [_view(item) for item in list_plugin_releases(session)]


@router.get("/plugin-releases/{release_id}", response_model=PluginReleaseView)
def release(release_id: UUID, session: Session = Depends(get_session)) -> PluginReleaseView:
    item = get_plugin_release(session, release_id)
    if item is None:
        raise QfError("PLUGIN_UNKNOWN", "Plugin release does not exist.", 404)
    return _view(item)


@router.post("/plugin-releases/{release_id}/activate", response_model=PluginReleaseView)
def activate(release_id: UUID, session: Session = Depends(get_session)) -> PluginReleaseView:
    with session.begin():
        item = activate_release(session, release_id)
        append_event(
            session,
            kind="PLUGIN_RELEASE_ACTIVATED",
            aggregate_type="plugin_release",
            aggregate_id=item.id,
            payload={"plugin_id": item.plugin_id, "version": item.version},
            actor_kind="LOCAL_OPERATOR",
        )
    return _view(item)


@router.post("/plugin-releases/{release_id}/deactivate", response_model=PluginReleaseView)
def deactivate(release_id: UUID, session: Session = Depends(get_session)) -> PluginReleaseView:
    with session.begin():
        item = deactivate_release(session, release_id)
        append_event(
            session,
            kind="PLUGIN_RELEASE_DRAINING",
            aggregate_type="plugin_release",
            aggregate_id=item.id,
            payload={"plugin_id": item.plugin_id, "version": item.version},
            actor_kind="LOCAL_OPERATOR",
        )
    return _view(item)

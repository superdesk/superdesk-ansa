import logging

import superdesk
from superdesk import get_resource_service
from superdesk.signals import item_update
from apps.content import push_content_notification
from flask import current_app

logger = logging.getLogger(__name__)


def get_picture_stage_name():
    vocab = get_resource_service("vocabularies").find_one(
        req=None, _id=current_app.config.get("MOVE_PICTURE_STAGE_VOCABULARY_ID", "move_picture_stage")
    )
    if not vocab or not vocab.get("items"):
        return None
    for item in vocab["items"]:
        if item.get("is_active"):
            return item.get("name")
    return None


def is_desk_enabled(desk_id):
    """Check if the desk is enabled for picture moving.

    If move_picture_desks vocabulary has no active items, all desks are enabled.
    Otherwise, only desks whose name matches an active item are enabled.
    """
    vocab = get_resource_service("vocabularies").find_one(
        req=None, _id=current_app.config.get("MOVE_PICTURE_DESKS_VOCABULARY_ID", "move_picture_desks")
    )
    if not vocab or not vocab.get("items"):
        return True
    active_names = [item.get("name") for item in vocab["items"] if item.get("is_active") and item.get("name")]
    if not active_names:
        return True
    desk = get_resource_service("desks").find_one(req=None, _id=desk_id)
    if not desk:
        return False
    return desk.get("name") in active_names


def find_stage_by_name(desk_id, stage_name):
    stages = get_resource_service("stages").get(req=None, lookup={"desk": desk_id, "name": stage_name})
    for stage in stages:
        return stage
    return None


def on_item_create(sender, item, **kwargs):
    """Move picture to photo archive stage when it's created on a desk."""
    if item.get("type") != "picture":
        return
    desk_id = item.get("task", {}).get("desk")
    if not desk_id or not is_desk_enabled(desk_id):
        return
    _set_picture_stage(item, desk_id)


def on_item_update(sender, updates, original, **kwargs):
    """Move picture when it's added as an association to an article on a desk."""
    desk_id = original.get("task", {}).get("desk")
    if not desk_id or not is_desk_enabled(desk_id):
        return

    new_associations = updates.get("associations") or {}
    old_associations = original.get("associations") or {}

    for key, assoc in new_associations.items():
        if not assoc or assoc.get("type") != "picture":
            continue
        old_assoc = old_associations.get(key)
        if old_assoc and old_assoc.get("_id") == assoc.get("_id"):
            continue
        _move_associated_picture(assoc, desk_id)


def _set_picture_stage(item, desk_id):
    """Set picture's stage in-place before DB save."""
    stage_name = get_picture_stage_name()
    if not stage_name:
        return

    stage = find_stage_by_name(desk_id, stage_name)
    if not stage:
        return

    if str(item.get("task", {}).get("stage") or "") == str(stage["_id"]):
        return

    logger.info(
        'move_picture_to_desk: setting picture "%s" to stage "%s"',
        item.get("headline") or item.get("slugline") or item.get("_id"),
        stage_name,
    )

    item.setdefault("task", {}).update(
        {
            "stage": stage["_id"],
        }
    )


def _move_associated_picture(assoc, desk_id):
    """Move an already-existing picture to the photo archive stage via system_update."""
    stage_name = get_picture_stage_name()
    if not stage_name:
        return

    picture_id = assoc.get("_id")
    if not picture_id:
        return

    stage = find_stage_by_name(desk_id, stage_name)
    if not stage:
        return

    archive_service = get_resource_service("archive")
    picture = archive_service.find_one(req=None, _id=picture_id)
    if not picture:
        return

    if str(picture.get("task", {}).get("stage") or "") == str(stage["_id"]):
        return

    logger.info(
        'move_picture_to_desk: moving associated picture "%s" to stage "%s"',
        picture_id,
        stage_name,
    )

    updated_task = dict(picture.get("task") or {})
    updated_task.update({"desk": desk_id, "stage": stage["_id"]})
    updates = {"task": updated_task}
    archive_service.system_update(picture_id, updates, picture)

    updated = picture.copy()
    updated.update(updates)
    push_content_notification([picture, updated])


def init_app(app):
    superdesk.item_create.connect(on_item_create)
    item_update.connect(on_item_update)

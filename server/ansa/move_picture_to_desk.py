import logging

import superdesk
from superdesk import get_resource_service
from superdesk.signals import item_update, item_publish


VOCABULARY_ID = "move_picture_destination"

logger = logging.getLogger(__name__)


def get_destination_desk():
    vocab = get_resource_service("vocabularies").find_one(req=None, _id=VOCABULARY_ID)
    if not vocab or not vocab.get("items"):
        return None
    for item in vocab["items"]:
        if item.get("is_active"):
            desk_name = item.get("name")
            if desk_name:
                return get_resource_service("desks").find_one(req=None, name=desk_name)
    return None


def on_item_create(sender, item, **kwargs):
    """Move picture to destination desk when it's being created."""
    if item.get("type") != "picture":
        return
    _move_picture_in_place(item)


def on_item_update(sender, updates, original, **kwargs):
    """Move picture when it's added as an association to an article."""
    from_personal = not original.get("task", {}).get("desk") and updates.get("task", {}).get("desk")
    if not original.get("task", {}).get("desk") and not from_personal:
        return
    _move_new_picture_associations(updates, original, move_existing=from_personal)


def on_item_publish(sender, item, updates, **kwargs):
    """Move pictures when article is published from personal space."""
    if item.get("task", {}).get("desk"):
        return
    associations = item.get("associations") or {}
    for key, assoc in associations.items():
        if assoc and assoc.get("type") == "picture":
            _move_associated_picture(assoc)


def _move_new_picture_associations(updates, original, move_existing=False):
    new_associations = updates.get("associations") or {}
    old_associations = original.get("associations") or {}
    for key, assoc in new_associations.items():
        if not assoc or assoc.get("type") != "picture":
            continue
        old_assoc = old_associations.get(key)
        if old_assoc and old_assoc.get("_id") == assoc.get("_id"):
            if move_existing:
                _move_associated_picture(assoc)
            continue
        _move_associated_picture(assoc)


def _move_picture_in_place(item):
    """Move a picture item by modifying its task in-place (before DB save)."""
    if not item.get("task", {}).get("desk"):
        return

    dest_desk = get_destination_desk()
    if not dest_desk:
        return

    current_desk_id = str(item.get("task", {}).get("desk") or "")
    dest_desk_id = str(dest_desk["_id"])

    if current_desk_id == dest_desk_id:
        return

    logger.info(
        'move_picture_to_desk: moving picture "%s" to desk "%s"',
        item.get("headline") or item.get("slugline") or item.get("_id"),
        dest_desk.get("name"),
    )

    item.setdefault("task", {}).update(
        {
            "desk": dest_desk["_id"],
            "stage": dest_desk.get("working_stage"),
        }
    )


def _move_associated_picture(assoc):
    """Move an already-existing picture item via system_update."""
    dest_desk = get_destination_desk()
    if not dest_desk:
        return

    picture_id = assoc.get("_id")
    if not picture_id:
        return

    archive_service = get_resource_service("archive")
    picture = archive_service.find_one(req=None, _id=picture_id)
    if not picture:
        return

    current_desk_id = str(picture.get("task", {}).get("desk") or "")
    dest_desk_id = str(dest_desk["_id"])

    if current_desk_id == dest_desk_id:
        return

    logger.info(
        'move_picture_to_desk: moving associated picture "%s" to desk "%s"',
        picture_id,
        dest_desk.get("name"),
    )

    archive_service.system_update(
        picture_id,
        {"task": {"desk": dest_desk["_id"], "stage": dest_desk.get("working_stage")}},
        picture,
    )


def init_app(app):
    superdesk.item_create.connect(on_item_create)
    item_update.connect(on_item_update)
    item_publish.connect(on_item_publish)

import logging

import superdesk
from superdesk import get_resource_service
from superdesk.signals import item_create, item_update, item_updated


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
    """Fires before item is saved to DB. Modify task in-place."""
    logger.info(
        "move_picture_to_desk: item_create signal received, type=%s, id=%s, headline=%s, task=%s",
        item.get("type"),
        item.get("_id"),
        item.get("headline") or item.get("slugline"),
        item.get("task"),
    )
    if item.get("type") != "picture":
        return
    _move_picture(item)


def on_item_update(sender, updates, original, **kwargs):
    """Fires before item update is saved. Check for new picture associations."""
    logger.info(
        "move_picture_to_desk: item_update signal received, type=%s, id=%s",
        original.get("type"),
        original.get("_id"),
    )
    new_associations = updates.get("associations") or {}
    old_associations = original.get("associations") or {}
    for key, assoc in new_associations.items():
        if not assoc or assoc.get("type") != "picture":
            continue
        old_assoc = old_associations.get(key)
        if old_assoc and old_assoc.get("_id") == assoc.get("_id"):
            continue
        logger.info(
            "move_picture_to_desk: new picture association found, key=%s, picture_id=%s",
            key,
            assoc.get("_id"),
        )
        _move_associated_picture(assoc)


def on_item_updated(sender, item, original, **kwargs):
    """Fires after item update is saved."""
    logger.info(
        "move_picture_to_desk: item_updated signal received, type=%s, id=%s",
        original.get("type"),
        original.get("_id"),
    )


def _move_picture(item):
    """Move a picture item by modifying its task in-place (before save)."""
    dest_desk = get_destination_desk()
    if not dest_desk:
        logger.warning("move_picture_to_desk: no destination desk configured")
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

    item.setdefault("task", {}).update({
        "desk": dest_desk["_id"],
        "stage": dest_desk.get("working_stage"),
    })


def _move_associated_picture(assoc):
    """Move an already-existing picture item via system_update."""
    dest_desk = get_destination_desk()
    if not dest_desk:
        logger.warning("move_picture_to_desk: no destination desk configured")
        return

    picture_id = assoc.get("_id")
    if not picture_id:
        return

    archive_service = get_resource_service("archive")
    picture = archive_service.find_one(req=None, _id=picture_id)
    if not picture:
        logger.warning("move_picture_to_desk: picture %s not found in archive", picture_id)
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
    item_updated.connect(on_item_updated)

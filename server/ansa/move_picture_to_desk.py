import logging

import superdesk
from superdesk import get_resource_service


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
    """Move picture to destination desk right when it's being created.

    Fires before the item is saved to DB, so we modify the task in-place.
    """
    if item.get("type") != "picture":
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

    item.setdefault("task", {}).update({
        "desk": dest_desk["_id"],
        "stage": dest_desk.get("working_stage"),
    })


def init_app(app):
    superdesk.item_create.connect(on_item_create)

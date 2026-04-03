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


def move_picture_handler(sender, item, **kwargs):
    if item.get("type") != "picture":
        return

    dest_desk = get_destination_desk()
    if not dest_desk:
        return

    current_desk_id = str(item.get("task", {}).get("desk") or "")
    dest_desk_id = str(dest_desk["_id"])

    if current_desk_id == dest_desk_id:
        return

    dest_stage_id = dest_desk.get("working_stage")
    logger.info(
        'move_picture_to_desk: moving picture "%s" to desk "%s"',
        item.get("headline") or item.get("slugline") or item.get("_id"),
        dest_desk.get("name"),
    )

    updates = {
        "task": {
            "desk": dest_desk["_id"],
            "stage": dest_stage_id,
        }
    }

    get_resource_service("archive").system_update(
        item[superdesk.config.ID_FIELD], updates, item
    )


def init_app(app):
    superdesk.item_fetched.connect(move_picture_handler)
    superdesk.item_moved.connect(move_picture_handler)

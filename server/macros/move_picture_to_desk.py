# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013-2024 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from superdesk import get_resource_service
from superdesk.logging import logger


VOCABULARY_ID = "move_picture_destination"


def get_destination_desk_name():
    vocab = get_resource_service("vocabularies").find_one(req=None, _id=VOCABULARY_ID)
    if vocab and vocab.get("items"):
        for item in vocab["items"]:
            if item.get("is_active"):
                return item.get("name")
    return None


def move_picture_to_desk(item, desk=None, task=None, **kwargs):
    """Move picture items to a configured destination desk.

    The destination desk name is read from the vocabulary 'move_picture_destination'.
    Only items of type 'picture' are moved; other types are returned unchanged.
    """
    if item.get("type") != "picture":
        return item

    if not task:
        logger.warning("move_picture_to_desk: no task for item %s", item.get("_id"))
        return item

    dest_desk_name = get_destination_desk_name()
    if not dest_desk_name:
        logger.warning("move_picture_to_desk: no destination desk configured in vocabulary '%s'", VOCABULARY_ID)
        return item

    dest_desk = get_resource_service("desks").find_one(req=None, name=dest_desk_name)
    if not dest_desk:
        logger.warning("move_picture_to_desk: destination desk '%s' not found", dest_desk_name)
        return item

    current_desk_id = str(item.get("task", {}).get("desk", ""))
    if current_desk_id == str(dest_desk["_id"]):
        return item

    logger.info(
        'move_picture_to_desk: moving picture "%s" to desk "%s"',
        item.get("headline") or item.get("slugline") or item.get("_id"),
        dest_desk_name,
    )

    task_update = {"desk": dest_desk["_id"], "stage": dest_desk.get("working_stage")}
    task.update(task_update)
    item.setdefault("task", {}).update(task_update)

    return item


name = "move_picture_to_desk"
label = "Move Picture to Desk"
callback = move_picture_to_desk
access_type = "backend"
action_type = "direct"

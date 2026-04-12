import logging
import superdesk

from superdesk.signals import item_publish
from superdesk.metadata.item import PUBLISH_STATES

from .constants import PRODUCTS_ID

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def on_update(resource, updates, original):
    if resource == "archive_publish":
        on_publish(updates, original)
        return


def on_publish(updates, original):
    assign_product_to_pictures(updates, original)
    move_associated_pictures_from_personal_space(updates, original)


def assign_product_to_pictures(updates, original):
    """When item is published with associated pictures
    make sure these have product assigned.
    """
    associations = updates.get("associations")
    if not associations:
        return
    for key, item in associations.items():
        if not item or item.get("type") != "picture" or item.get("state") in PUBLISH_STATES:
            continue
        subject = item.setdefault("subject", [])
        product = next((subj for subj in subject if subj.get("scheme") == PRODUCTS_ID), None)
        if not product:
            subject.append(
                {
                    "name": "Browser Allegati",
                    "qcode": "0050000100002",
                    "scheme": PRODUCTS_ID,
                }
            )
        item["auto_publish"] = True
        if original:
            original.setdefault("associations", {}).update({key: item})


def move_associated_pictures_from_personal_space(updates, original):
    """When publishing from personal space, move associated pictures to the target desk.

    Pictures are moved to the stage defined in move_picture_stage vocabulary.
    """
    from .move_picture_to_desk import get_picture_stage_name, find_stage_by_name

    # only handle personal space (no desk on original)
    if original and original.get("task", {}).get("desk"):
        return

    # get the target desk - read from request args since set_desk hasn't run yet
    from flask import request

    desk_id = updates.get("task", {}).get("desk")
    if not desk_id and request and request.args:
        desk_id = request.args.get("desk_id")
    if not desk_id:
        return

    stage_name = get_picture_stage_name()
    if not stage_name:
        return

    stage = find_stage_by_name(desk_id, stage_name)
    if not stage:
        return

    associations = updates.get("associations") or original.get("associations") or {}
    archive_service = superdesk.get_resource_service("archive")

    for key, assoc in associations.items():
        if not assoc or assoc.get("type") != "picture":
            continue
        if assoc.get("state") in PUBLISH_STATES:
            continue

        picture_id = assoc.get("_id")
        if not picture_id:
            continue

        picture = archive_service.find_one(req=None, _id=picture_id)
        if not picture:
            continue

        # skip if already on this desk/stage
        if str(picture.get("task", {}).get("desk") or "") == str(desk_id) and str(
            picture.get("task", {}).get("stage") or ""
        ) == str(stage["_id"]):
            continue

        logger.info(
            'move_associated_pictures_from_personal_space: moving picture "%s" to desk "%s" stage "%s"',
            picture_id,
            desk_id,
            stage_name,
        )

        archive_service.system_update(
            picture_id,
            {"task": {"desk": desk_id, "stage": stage["_id"]}},
            picture,
        )


def udpate_sign_off(sender, item, **kwargs):
    """When item is auto published add -RED to sign_off."""
    if item.get("auto_publish"):
        if not item.get("sign_off"):
            item["sign_off"] = "RED"


def init_app(app):
    superdesk.privilege(name="ansa_metasearch", label="ANSA - metasearch", decsription="")

    superdesk.privilege(name="ansa_live_assistant", label="ANSA - live assistant", decsription="")

    superdesk.privilege(name="ansa_ai_news", label="ANSA - ai news", decsription="")

    app.on_update += on_update
    item_publish.connect(udpate_sign_off)

    priority_to_profile_mapping = {}
    for key, val in app.config["PRIORITY_TO_PROFILE_MAPPING"].items():
        with app.app_context():
            profile = app.data.find_one("content_types", req=None, label=val)
        if profile:
            priority_to_profile_mapping[key] = str(profile["_id"])

    app.client_config.update(
        {
            "ansa": {
                "priority_to_profile_mapping": priority_to_profile_mapping,
            },
        }
    )

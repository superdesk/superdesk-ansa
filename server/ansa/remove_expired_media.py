import logging

from flask import current_app as app
from superdesk import get_resource_service
from superdesk.signals import archived_item_removed

logger = logging.getLogger(__name__)


def populate_renditions(renditions, item):
    """Collect removable media and return the view-image IDs kept for the legal archive."""
    rendition_sets = [item.get("renditions") or {}]
    rendition_sets.extend(
        association["renditions"]
        for association in (item.get("associations") or {}).values()
        if association and association.get("renditions")
    )
    kept_media = {
        str(item_renditions["viewImage"]["media"])
        for item_renditions in rendition_sets
        if item_renditions.get("viewImage") and item_renditions["viewImage"].get("media")
    }

    seen_media = kept_media.copy()
    for item_renditions in rendition_sets:
        for rendition in item_renditions.values():
            if rendition and rendition.get("media"):
                media_id = str(rendition["media"])
                if media_id not in seen_media:
                    seen_media.add(media_id)
                    renditions.append({"media": media_id})
    return kept_media


def remove_expired_media(archived_service, item, dry=False, **kwargs):
    other = archived_service.find_one(req=None, item_id=item["item_id"])
    if other is not None:
        logger.info("Skip removing media for item %s", item["item_id"])
        return
    production_item = get_resource_service("archive").find_one(req=None, _id=item["item_id"])
    if production_item is not None:
        logger.info("Keeping media for item %s still available in production", item["item_id"])
        return
    renditions = []
    kept_media = populate_renditions(renditions, item)
    if renditions and not dry:
        logger.info("Removing %d media files for item %s", len(renditions), item.get("guid"))
    elif not dry:
        logger.info("No media to be removed for item %s", item.get("guid"))

    media_references = get_resource_service("media_references")
    if not dry:
        media_references.delete_action(
            lookup={
                "item_id": item["item_id"],
                "media_id": {"$nin": list(kept_media)},
            }
        )

    for rend in renditions:
        try:
            references = media_references.get(
                req=None,
                lookup={
                    "media_id": str(rend["media"]),
                },
            )
            if dry:
                has_references = any(ref.get("item_id") != item["item_id"] for ref in references)
            else:
                has_references = references.count() > 0

            if not has_references:
                if dry:
                    print(rend["media"])
                else:
                    logger.info("removing %s", rend["media"])
                    app.media.delete(str(rend["media"]))
            else:
                logger.info("keeping %s due to references", rend["media"])
        except Exception:
            logger.exception("Failed to remove media %s", rend["media"])


def init_app(_app):
    archived_item_removed.connect(remove_expired_media)

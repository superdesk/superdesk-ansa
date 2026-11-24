from contextlib import redirect_stdout
from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from superdesk import get_resource_service
from superdesk.tests import TestCase
from superdesk.utc import utcnow

from ansa.commands.remove_expired_media import RemoveExpiredMediaCommand
from ansa.remove_expired_media import populate_renditions, remove_expired_media


class RemoveExpiredMediaTestCase(TestCase):
    def setUp(self):
        self.item = {
            "item_id": "expired-item",
            "renditions": {
                "viewImage": {"media": "view-image"},
                "thumbnail": {"media": "thumbnail"},
            },
            "associations": {
                "featuremedia": {
                    "renditions": {
                        "viewImage": {"media": "associated-view-image"},
                        "original": {"media": "associated-original"},
                    }
                }
            },
        }
        self.archived_service = get_resource_service("archived")
        self.references = get_resource_service("media_references")
        self.app.data.insert(
            "media_references",
            [
                {"item_id": self.item["item_id"], "media_id": media_id, "published": True}
                for media_id in ("view-image", "thumbnail", "associated-view-image", "associated-original")
            ],
        )

    def test_populate_renditions_keeps_view_images_and_collects_associated_media(self):
        renditions = []

        populate_renditions(renditions, self.item)

        self.assertEqual(
            {"thumbnail", "associated-original"},
            {rendition["media"] for rendition in renditions},
        )

    def test_populate_renditions_keeps_media_shared_with_view_images(self):
        self.item["renditions"]["thumbnail"]["media"] = "associated-view-image"
        renditions = []

        populate_renditions(renditions, self.item)

        self.assertEqual([{"media": "associated-original"}], renditions)

    def test_dry_run_does_not_delete_references_or_media(self):
        before = list(self.references.get_from_mongo(None, {"item_id": self.item["item_id"]}))
        output = StringIO()
        with patch.object(self.app.media, "delete") as delete_media, redirect_stdout(output):
            remove_expired_media(self.archived_service, self.item, dry=True)

        self.assertEqual(before, list(self.references.get_from_mongo(None, {"item_id": self.item["item_id"]})))
        delete_media.assert_not_called()
        self.assertCountEqual(["thumbnail", "associated-original"], output.getvalue().splitlines())

    def test_removes_unreferenced_media_but_keeps_view_images(self):
        with patch.object(self.app.media, "delete") as delete_media:
            remove_expired_media(self.archived_service, self.item)

        self.assertCountEqual(
            ["view-image", "associated-view-image"],
            [ref["media_id"] for ref in self.references.get_from_mongo(None, {"item_id": self.item["item_id"]})],
        )
        self.assertCountEqual(
            ["thumbnail", "associated-original"],
            [call.args[0] for call in delete_media.call_args_list],
        )

    def test_production_item_keeps_references_and_media(self):
        self.app.data.insert("archive", [{"_id": self.item["item_id"], "type": "picture"}])
        before = list(self.references.get_from_mongo(None, {"item_id": self.item["item_id"]}))

        with patch.object(self.app.media, "delete") as delete_media:
            remove_expired_media(self.archived_service, self.item)

        self.assertEqual(before, list(self.references.get_from_mongo(None, {"item_id": self.item["item_id"]})))
        delete_media.assert_not_called()

    def test_command_processes_items_with_associations_only(self):
        self.app.data.insert(
            "legal_archive",
            [
                {
                    "_id": self.item["item_id"],
                    "versioncreated": utcnow() - timedelta(days=60),
                    "associations": self.item["associations"],
                },
            ],
        )
        with patch.object(self.app.media, "delete") as delete_media:
            RemoveExpiredMediaCommand().run(days=50, skip=0, limit=0)

        delete_media.assert_called_once_with("associated-original")
        self.assertCountEqual(
            ["associated-view-image"],
            [ref["media_id"] for ref in self.references.get_from_mongo(None, {"item_id": self.item["item_id"]})],
        )

    def test_command_keeps_associated_view_image_shared_with_later_item(self):
        later_item_id = "later-expired-item"
        shared_media_id = "associated-view-image"
        expired_at = utcnow() - timedelta(days=60)
        self.app.data.insert(
            "legal_archive",
            [
                {
                    "_id": self.item["item_id"],
                    "versioncreated": expired_at,
                    "associations": self.item["associations"],
                },
                {
                    "_id": later_item_id,
                    "versioncreated": expired_at,
                    "renditions": {"thumbnail": {"media": shared_media_id}},
                },
            ],
        )
        self.app.data.insert(
            "media_references",
            [{"item_id": later_item_id, "media_id": shared_media_id, "published": True}],
        )

        with patch.object(self.app.media, "delete") as delete_media:
            RemoveExpiredMediaCommand().run(days=50, skip=0, limit=0)

        delete_media.assert_called_once_with("associated-original")
        self.assertEqual(
            [self.item["item_id"]],
            [ref["item_id"] for ref in self.references.get_from_mongo(None, {"media_id": shared_media_id})],
        )

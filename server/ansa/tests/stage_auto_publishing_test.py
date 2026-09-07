import unittest
from unittest.mock import patch, AsyncMock, MagicMock

from ansa.stage_auto_publishing import (
    publish_item_on_auto_publish_stage,
    unlink_update_on_auto_publish,
    AUTO_PUBLISH_FIELD,
)
from superdesk.resource_fields import ID_FIELD


class UnlinkUpdateOnAutoPublishTestCase(unittest.TestCase):
    @patch("ansa.stage_auto_publishing.superdesk")
    def test_no_rewrite_of_is_noop(self, superdesk_mock):
        updates = {}
        unlink_update_on_auto_publish({}, updates)
        superdesk_mock.get_resource_service.assert_not_called()
        self.assertEqual({}, updates)

    @patch("ansa.stage_auto_publishing.superdesk")
    def test_unlinks_when_main_not_published(self, superdesk_mock):
        archive_service = MagicMock()
        archive_service.find_one.return_value = {"_id": "main-id", "state": "submitted"}
        superdesk_mock.get_resource_service.return_value = archive_service

        updates = {}
        unlink_update_on_auto_publish({"rewrite_of": "main-id"}, updates)

        self.assertIsNone(updates["rewrite_of"])
        archive_service.system_update.assert_called_once_with(
            "main-id", {"rewritten_by": None}, archive_service.find_one.return_value
        )


class PublishItemOnAutoPublishStageTestCase(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        patcher = patch("ansa.stage_auto_publishing.superdesk")
        self.superdesk_mock = patcher.start()
        self.addCleanup(patcher.stop)

        self.stages_service = MagicMock()
        self.macros_service = MagicMock()
        self.macros_service.execute_macro = AsyncMock()
        self.archive_publish_service = MagicMock()
        self.archive_publish_service.patch_async = AsyncMock()

        services = {
            "stages": self.stages_service,
            "macros": self.macros_service,
            "archive_publish": self.archive_publish_service,
        }
        self.superdesk_mock.get_resource_service.side_effect = lambda name: services[name]

        self.item = {ID_FIELD: "item-1", "task": {"stage": "stage-1"}}

    async def test_no_stage_id_is_noop(self):
        await publish_item_on_auto_publish_stage({ID_FIELD: "item-1"})
        self.stages_service.find_one.assert_not_called()

    async def test_stage_without_auto_publish_is_noop(self):
        self.stages_service.find_one.return_value = {AUTO_PUBLISH_FIELD: False}
        await publish_item_on_auto_publish_stage(self.item)
        self.archive_publish_service.patch_async.assert_not_awaited()

    async def test_publishes_via_patch_async(self):
        self.stages_service.find_one.return_value = {AUTO_PUBLISH_FIELD: True, "name": "stage"}

        await publish_item_on_auto_publish_stage(self.item)

        self.macros_service.execute_macro.assert_not_awaited()
        self.archive_publish_service.patch_async.assert_awaited_once_with("item-1", {"auto_publish": True})

    async def test_runs_incoming_macro_before_publish(self):
        self.stages_service.find_one.return_value = {
            AUTO_PUBLISH_FIELD: True,
            "name": "stage",
            "incoming_macro": "some_macro",
        }

        await publish_item_on_auto_publish_stage(self.item)

        self.macros_service.execute_macro.assert_awaited_once_with({"auto_publish": True}, "some_macro")
        self.archive_publish_service.patch_async.assert_awaited_once()

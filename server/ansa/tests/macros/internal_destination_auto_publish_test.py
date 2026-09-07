import unittest
from unittest.mock import patch, AsyncMock, MagicMock

from ansa.macros.internal_destination_auto_publish import internal_destination_auto_publish
from superdesk.errors import StopDuplication, InvalidStateTransitionError
from superdesk.resource_fields import ID_FIELD
from superdesk.metadata.item import ITEM_STATE, CONTENT_STATE, PUBLISH_SCHEDULE, SCHEDULE_SETTINGS, PROCESSED_FROM
from apps.archive.common import ITEM_OPERATION
from apps.publish.content.common import ITEM_PUBLISH


def make_item(**overrides):
    item = {
        ID_FIELD: "item-1",
        ITEM_STATE: CONTENT_STATE.PUBLISHED,
        ITEM_OPERATION: ITEM_PUBLISH,
        PUBLISH_SCHEDULE: None,
        SCHEDULE_SETTINGS: {},
        "task": {"desk": "desk-1"},
    }
    item.update(overrides)
    return item


class InternalDestinationAutoPublishTestCase(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        patcher = patch("ansa.macros.internal_destination_auto_publish.get_resource_service")
        self.get_resource_service_mock = patcher.start()
        self.addCleanup(patcher.stop)

        self.archive_service = MagicMock()
        self.archive_publish_service = MagicMock()
        services = {
            "archive": self.archive_service,
            "archive_publish": self.archive_publish_service,
        }
        self.get_resource_service_mock.side_effect = lambda name: services[name]

        cursor = MagicMock()
        cursor.next = AsyncMock(side_effect=StopAsyncIteration)
        self.archive_service.get_from_mongo_async = AsyncMock(return_value=cursor)
        self.archive_service.duplicate_content = AsyncMock(return_value="new-id")
        self.archive_publish_service.patch_async = AsyncMock()

    async def test_raises_when_item_not_yet_published(self):
        item = make_item(**{ITEM_STATE: CONTENT_STATE.SUBMITTED})
        with self.assertRaises(InvalidStateTransitionError):
            await internal_destination_auto_publish(item)

    async def test_publishes_duplicate_via_patch_async(self):
        item = make_item()

        with self.assertRaises(StopDuplication):
            await internal_destination_auto_publish(item)

        self.archive_service.duplicate_content.assert_awaited_once()
        self.archive_publish_service.patch_async.assert_awaited_once()
        _, kwargs = self.archive_publish_service.patch_async.await_args
        self.assertEqual("new-id", kwargs["id"])
        self.assertEqual(item[ID_FIELD], kwargs["updates"][PROCESSED_FROM])

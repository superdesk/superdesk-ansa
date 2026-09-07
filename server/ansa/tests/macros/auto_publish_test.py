import unittest
from unittest.mock import patch, AsyncMock

from ansa.macros.auto_publish import auto_publish
from superdesk.resource_fields import ID_FIELD
from superdesk.metadata.item import ITEM_STATE, CONTENT_STATE


class AutoPublishTestCase(unittest.IsolatedAsyncioTestCase):
    @patch("ansa.macros.auto_publish.get_resource_service")
    async def test_publishes_via_patch_async(self, get_resource_service_mock):
        service_mock = get_resource_service_mock.return_value
        service_mock.patch_async = AsyncMock()

        item = {ID_FIELD: "123"}
        result = await auto_publish(item)

        get_resource_service_mock.assert_called_with("archive_publish")
        service_mock.patch_async.assert_awaited_once_with(
            id="123", updates={ITEM_STATE: CONTENT_STATE.PUBLISHED, "auto_publish": True}
        )
        self.assertIs(item, result)

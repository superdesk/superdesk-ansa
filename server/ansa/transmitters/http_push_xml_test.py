import hmac
import json
import unittest
from unittest import mock

import flask
from superdesk.errors import PublishHTTPPushClientError
from superdesk.publish import registered_transmitters, registered_transmitters_list

from ansa.transmitters import ANSAHTTPPushService

XML = '<?xml version="1.0" encoding="UTF-8"?>\n<newsMessage xmlns="http://iptc.org/std/nar/2006-10-01/"/>'
POST = "ansa.transmitters.http_push_xml.requests.post"


def make_queue_item(formatted_item, **config):
    destination = {"delivery_type": "http_push", "config": {"resource_url": "http://example.com/push", **config}}
    return {
        "formatted_item": formatted_item,
        "encoded_item": formatted_item.encode("utf-8"),
        "item_id": "urn:test",
        "item_version": 2,
        "destination": destination,
    }


def ok_response():
    return mock.Mock(status_code=201, raise_for_status=mock.Mock())


class ANSAHTTPPushTestCase(unittest.TestCase):
    def setUp(self):
        self.app = flask.Flask(__name__)
        self.ctx = self.app.app_context()
        self.ctx.push()
        self.service = ANSAHTTPPushService()

    def tearDown(self):
        self.ctx.pop()

    def test_replaces_core_transmitter(self):
        self.assertIsInstance(registered_transmitters["http_push"], ANSAHTTPPushService)
        self.assertEqual(1, len([t for t in registered_transmitters_list if t["type"] == "http_push"]))

    def test_push_xml_signed(self):
        with mock.patch(POST, return_value=ok_response()) as post:
            self.service._transmit(make_queue_item(XML, secret_token="foo"), {})
        post.assert_called_once()
        args, kwargs = post.call_args
        self.assertEqual("http://example.com/push", args[0])
        self.assertEqual(XML.encode("utf-8"), kwargs["data"])
        self.assertEqual((5, 30), kwargs["timeout"])
        headers = kwargs["headers"]
        self.assertEqual("application/xml; charset=utf-8", headers["Content-type"])
        expected = "sha1=" + hmac.new(b"foo", XML.encode("utf-8"), "sha1").hexdigest()
        self.assertEqual(expected, headers["x-superdesk-signature"])

    def test_custom_content_type(self):
        self.app.config["HTTP_PUSH_XML_CONTENT_TYPE"] = "application/vnd.iptc.g2.newsmessage+xml"
        with mock.patch(POST, return_value=ok_response()) as post:
            self.service._transmit(make_queue_item(XML), {})
        headers = post.call_args[1]["headers"]
        self.assertEqual("application/vnd.iptc.g2.newsmessage+xml; charset=utf-8", headers["Content-type"])
        self.assertNotIn("x-superdesk-signature", headers)

    def test_xml_skipped_when_packaged(self):
        queue_item = make_queue_item(XML, packaged=True)
        queue_item["published_in_package"] = "pkg"
        with mock.patch(POST) as post:
            self.service._transmit(queue_item, {})
        post.assert_not_called()

    def test_xml_copies_media_when_assets_url_set(self):
        item = {"guid": "urn:test", "renditions": {}}
        with (
            mock.patch(POST, return_value=ok_response()) as post,
            mock.patch.object(self.service, "_get_published_item", return_value=item) as get_item,
            mock.patch.object(self.service, "_copy_published_media_files") as copy_media,
        ):
            self.service._transmit(make_queue_item(XML, assets_url="http://example.com/assets"), {})
        get_item.assert_called_once()
        copy_media.assert_called_once_with(item, mock.ANY)
        post.assert_called_once()

    def test_xml_no_media_lookup_without_assets_url(self):
        with mock.patch(POST, return_value=ok_response()), mock.patch.object(
            self.service, "_get_published_item"
        ) as get_item:
            self.service._transmit(make_queue_item(XML), {})
        get_item.assert_not_called()

    def test_client_error_raised(self):
        response = mock.Mock(status_code=400, text="bad")
        response.raise_for_status.side_effect = Exception("400")
        with mock.patch(POST, return_value=response), mock.patch("superdesk.errors.update_notifiers"):
            with self.assertRaises(PublishHTTPPushClientError):
                self.service._transmit(make_queue_item(XML), {})

    def test_json_uses_core_behaviour(self):
        with mock.patch("superdesk.publish.transmitters.http_push.HTTPPushService._transmit") as core_transmit:
            self.service._transmit(make_queue_item(json.dumps({"guid": "x"})), {})
        core_transmit.assert_called_once()

# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2026 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

"""HTTP Push that also works with XML formats (eg. ANSA NewsML G2).

The core ``http_push`` transmitter assumes the formatted item is JSON
(it calls ``json.loads`` on it) so it fails with any XML formatter.

This transmitter replaces the core one under the same ``http_push`` type,
so the destination form in the UI (resource url, assets url, secret token,
packaged) keeps working:

* JSON formats (NINJS...) are handled exactly like before
* XML formats are POSTed as they are to the resource url, signed with
  ``x-superdesk-signature`` when a secret token is set. Media files are
  pushed to the assets url first (if configured), using the published item
  to find the renditions.

Settings:

* ``HTTP_PUSH_XML_CONTENT_TYPE`` - content type for XML items, default ``application/xml``
* ``HTTP_PUSH_TIMEOUT`` - (connect, read) timeout, same as core, default ``(5, 30)``
"""

import json
import logging

import requests
import superdesk

from flask import current_app as app
from superdesk.publish import register_transmitter, registered_transmitters_list
from superdesk.publish.publish_queue import PUBLISHED_IN_PACKAGE
from superdesk.publish.transmitters.http_push import HTTPPushService, errors

logger = logging.getLogger(__name__)

DEFAULT_XML_CONTENT_TYPE = "application/xml"


def is_json(formatted_item) -> bool:
    if not isinstance(formatted_item, str):
        return False
    try:
        json.loads(formatted_item)
    except ValueError:
        return False
    return True


class ANSAHTTPPushService(HTTPPushService):
    NAME = "HTTP Push"

    def _transmit(self, queue_item, subscriber):
        if is_json(queue_item.get("formatted_item")):
            return super()._transmit(queue_item, subscriber)
        return self._transmit_xml(queue_item)

    def _transmit_xml(self, queue_item):
        destination = queue_item.get("destination", {})

        assets_url = self._get_assets_url(destination)
        if isinstance(assets_url, str) and assets_url.strip():
            item = self._get_published_item(queue_item)
            if item:
                self._copy_published_media_files(item, destination)

        packaged = destination.get("config", {}).get("packaged", False)
        if queue_item.get(PUBLISHED_IN_PACKAGE) and packaged:
            return

        data = self._get_body(queue_item)
        headers = self._get_headers(data, destination, self._get_xml_headers(queue_item))
        resource_url = self._get_resource_url(destination)
        response = requests.post(resource_url, data=data, headers=headers, timeout=self._get_timeout())

        try:
            response.raise_for_status()
        except Exception as ex:
            logger.exception(ex)
            message = "Error pushing item %s: %s" % (response.status_code, response.text)
            self._raise_publish_error(response.status_code, Exception(message), destination)

    def _get_body(self, queue_item) -> bytes:
        if queue_item.get("encoded_item"):
            return queue_item["encoded_item"]
        encoding = queue_item.get("item_encoding", "utf-8")
        return queue_item["formatted_item"].encode(encoding, errors="replace")

    def _get_xml_headers(self, queue_item):
        content_type = app.config.get("HTTP_PUSH_XML_CONTENT_TYPE") or DEFAULT_XML_CONTENT_TYPE
        charset = queue_item.get("item_encoding") or "utf-8"
        return {"Content-type": "{}; charset={}".format(content_type, charset), "Accept": "*/*"}

    def _get_published_item(self, queue_item):
        try:
            return superdesk.get_resource_service("published").find_one(
                req=None,
                item_id=queue_item["item_id"],
                _current_version=queue_item["item_version"],
            )
        except Exception:
            logger.exception("HTTPPush: can't load published item %s", queue_item.get("item_id"))
            return None


def register():
    # drop the core entry so the UI doesn't list "HTTP Push" twice
    registered_transmitters_list[:] = [t for t in registered_transmitters_list if t["type"] != "http_push"]
    register_transmitter("http_push", ANSAHTTPPushService(), errors)

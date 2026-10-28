from .http_push_xml import ANSAHTTPPushService, register

register()


def init_app(_app):
    pass


__all__ = ["ANSAHTTPPushService"]

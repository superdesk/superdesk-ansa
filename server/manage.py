#!/usr/bin/env python
# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014, 2015 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

"""Superdesk Manager"""

import superdesk
import superdesk.commands
from app import get_app

from ansa.commands.remove_expired_media import RemoveExpiredMediaCommand


app = get_app(init_elastic=True)

superdesk.register_command(RemoveExpiredMediaCommand)


if __name__ == "__main__":
    import sys

    from quart.cli import ScriptInfo
    from superdesk.commands import cli

    cli.add_command(RemoveExpiredMediaCommand())

    original_load_app = ScriptInfo.load_app
    ScriptInfo.load_app = lambda self: app
    try:
        cli(prog_name="python manage.py", args=sys.argv[1:])
    finally:
        ScriptInfo.load_app = original_load_app

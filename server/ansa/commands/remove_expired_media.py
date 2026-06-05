import click
import superdesk

from datetime import datetime, timedelta

from superdesk.commands import cli

from ansa.remove_expired_media import remove_expired_media


@cli.command("ansa:remove_expired_media")
@click.option("--days", "days", type=int, default=50)
@click.option("--skip", "skip", type=int, default=0)
@click.option("--limit", "limit", type=int, default=0)
@click.option("--dry-run", "dry", is_flag=True, default=False)
def remove_expired_media_command(days, skip, limit, dry):
    """Remove media of legal archive items older than ``--days`` days."""
    now = datetime.now()
    stop = now - timedelta(days=days)
    legal = superdesk.get_resource_service("legal_archive")
    cursor = (
        legal.get_from_mongo(req=None, lookup={"versioncreated": {"$lte": stop}})
        .sort("_id")
        .skip(skip)
        .limit(limit)
    )

    archived_service = superdesk.get_resource_service("archived")

    i = 0
    for item in cursor:
        if item.get("renditions"):
            i += 1
            item["item_id"] = item["_id"]
            remove_expired_media(archived_service, item, dry=dry)

    print("checked", i, "items")

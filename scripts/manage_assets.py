#!/usr/bin/env python3
"""
PixVerse Asset Alias Manager

Manages the ~/.claude/pixverse_assets.json registry.
Supports both image and video assets.
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

DEFAULT_DB_PATH = Path.home() / ".claude" / "pixverse_assets.json"


def init_db(db_path: Path = DEFAULT_DB_PATH) -> dict:
    """Initialize the database file if it doesn't exist."""
    if db_path.exists():
        with open(db_path, 'r', encoding='utf-8') as f:
            db = json.load(f)
            # Migrate old format to new format if needed
            db = _migrate_db(db)
            return db

    db = {
        "assets": {},
        "settings": {
            "confirm_before_replace": True
        }
    }
    db_path.parent.mkdir(parents=True, exist_ok=True)
    save_db(db, db_path)
    return db


def _migrate_db(db: dict) -> dict:
    """Migrate old format (image_id/image_url) to new format (type/id/url)."""
    if "assets" not in db:
        db["assets"] = {}

    migrated = False
    for alias, info in db["assets"].items():
        # Skip if already in new format
        if "type" in info:
            continue

        # Detect type from old data
        if "image_id" in info or "image_url" in info:
            info["type"] = "image"
            info["id"] = info.pop("image_id", None) or info.get("id", "")
            info["url"] = info.pop("image_url", None) or info.get("url", "")
            migrated = True
        elif "video_id" in info or "video_url" in info:
            info["type"] = "video"
            info["id"] = info.pop("video_id", None) or info.get("id", "")
            info["url"] = info.pop("video_url", None) or info.get("url", "")
            migrated = True

    if migrated:
        save_db(db)
        print("✓ Migrated database to new format (type/id/url)", file=sys.stderr)

    return db


def save_db(db: dict, db_path: Path = DEFAULT_DB_PATH):
    """Save the database to file."""
    with open(db_path, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=2)


def add_alias(alias: str, asset_type: str, asset_id: str, url: str,
              cover_url: str = None, duration: int = None,
              db_path: Path = DEFAULT_DB_PATH):
    """Add a new alias to the database."""
    db = init_db(db_path)

    if alias in db["assets"]:
        print(f"Error: Alias '{alias}' already exists.", file=sys.stderr)
        print(f"Use 'update' to change it, or 'remove' then 'add'.", file=sys.stderr)
        sys.exit(1)

    entry = {
        "type": asset_type,  # "image" or "video"
        "id": asset_id,
        "url": url,
        "created_at": datetime.now().isoformat()
    }

    if cover_url:
        entry["cover_url"] = cover_url
    if duration:
        entry["duration"] = duration

    db["assets"][alias] = entry
    save_db(db, db_path)

    url_display = url[:50] + "..." if len(url) > 50 else url
    print(f"✓ Added alias '{alias}' -> type: {asset_type}, id: {asset_id}, url: {url_display}")


def add_from_pixverse_output(alias: str, json_output: str, db_path: Path = DEFAULT_DB_PATH):
    """Add alias from pixverse create output JSON."""
    try:
        data = json.loads(json_output)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON output: {e}", file=sys.stderr)
        sys.exit(1)

    # Determine type and extract fields
    if "image_id" in data or ("image_url" in data and "video_id" not in data):
        asset_type = "image"
        asset_id = str(data.get("image_id", ""))
        url = data.get("image_url", "")
        cover_url = None
        duration = None
        source = "create"
    elif "video_id" in data or "video_url" in data:
        asset_type = "video"
        asset_id = str(data.get("video_id", ""))
        url = data.get("video_url", "")
        cover_url = data.get("cover_url")
        duration = data.get("duration")
        source = "create"
    else:
        print("Error: Cannot determine asset type from output (no image_id or video_id found)", file=sys.stderr)
        print("JSON keys found: " + ", ".join(data.keys()), file=sys.stderr)
        sys.exit(1)

    if not asset_id or not url:
        print(f"Error: Missing required fields (id={asset_id}, url={url})", file=sys.stderr)
        sys.exit(1)

    # Use the new add_alias_with_source function
    add_alias_with_source(alias, asset_type, asset_id, url, source, cover_url, duration, db_path)


def add_from_upload_output(alias: str, json_output: str, db_path: Path = DEFAULT_DB_PATH):
    """Add alias from pixverse asset upload output JSON."""
    import re

    try:
        data = json.loads(json_output)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON output: {e}", file=sys.stderr)
        sys.exit(1)

    # Extract fields from upload output
    # upload output format: asset_id, asset_type (0=image, 1=video), url, width, height, etc.
    asset_id = str(data.get("asset_id", ""))
    asset_type_code = data.get("asset_type", 0)  # 0 = image, 1 = video
    url = data.get("url", "")

    if not asset_id:
        print(f"Error: Missing asset_id in upload output", file=sys.stderr)
        sys.exit(1)

    # Determine type
    asset_type = "video" if asset_type_code == 1 else "image"

    # Extract optional fields
    cover_url = data.get("cover")
    width = data.get("width")
    height = data.get("height")

    add_alias_with_source(alias, asset_type, asset_id, url, "upload", cover_url, None, db_path,
                          width=width, height=height)


def add_alias_with_source(alias: str, asset_type: str, asset_id: str, url: str,
                          source: str = "create", cover_url: str = None, duration: int = None,
                          db_path: Path = DEFAULT_DB_PATH, **extra_fields):
    """Add a new alias to the database with source tracking."""
    db = init_db(db_path)

    if alias in db["assets"]:
        print(f"Error: Alias '{alias}' already exists.", file=sys.stderr)
        print(f"Use 'update' to change it, or 'remove' then 'add'.", file=sys.stderr)
        sys.exit(1)

    entry = {
        "type": asset_type,  # "image" or "video"
        "id": asset_id,
        "url": url,
        "source": source,  # "upload" or "create"
        "created_at": datetime.now().isoformat()
    }

    if cover_url:
        entry["cover_url"] = cover_url
    if duration:
        entry["duration"] = duration
    if extra_fields:
        entry.update({k: v for k, v in extra_fields.items() if v is not None})

    db["assets"][alias] = entry
    save_db(db, db_path)

    url_display = url[:50] + "..." if len(url) > 50 else url
    print(f"✓ Added alias '{alias}' -> type: {asset_type}, id: {asset_id}, source: {source}, url: {url_display}")


def list_aliases(format_type: str = "table", asset_type: str = None, db_path: Path = DEFAULT_DB_PATH):
    """List all aliases in the database."""
    db = init_db(db_path)

    if not db["assets"]:
        print("No aliases registered yet.")
        return

    # Filter by type if specified
    assets = db["assets"]
    if asset_type:
        assets = {k: v for k, v in assets.items() if v.get("type") == asset_type}

    if format_type == "json":
        print(json.dumps(assets, ensure_ascii=False, indent=2))
    else:
        print(f"{'Alias':<20} {'Type':<8} {'ID':<18} {'URL (truncated)':<40}")
        print("-" * 90)
        for alias, info in assets.items():
            t = info.get('type', 'image')
            asset_id = info.get('id', 'N/A') or 'N/A'
            url = info.get('url', '')
            url_display = url[:37] + "..." if len(url) > 40 else (url or 'N/A')
            print(f"{alias:<20} {t:<8} {asset_id:<18} {url_display:<40}")


def remove_alias(alias: str, db_path: Path = DEFAULT_DB_PATH):
    """Remove an alias from the database."""
    db = init_db(db_path)

    if alias not in db["assets"]:
        print(f"Error: Alias '{alias}' not found.", file=sys.stderr)
        sys.exit(1)

    del db["assets"][alias]
    save_db(db, db_path)
    print(f"✓ Removed alias '{alias}'")


def update_alias(alias: str, new_alias: str = None, new_id: str = None,
                 new_url: str = None, new_type: str = None,
                 db_path: Path = DEFAULT_DB_PATH):
    """Update an alias properties."""
    db = init_db(db_path)

    if alias not in db["assets"]:
        print(f"Error: Alias '{alias}' not found.", file=sys.stderr)
        sys.exit(1)

    if new_alias and new_alias != alias:
        if new_alias in db["assets"]:
            print(f"Error: Alias '{new_alias}' already exists.", file=sys.stderr)
            sys.exit(1)
        db["assets"][new_alias] = db["assets"].pop(alias)
        alias = new_alias
        print(f"✓ Renamed alias to '{new_alias}'")

    if new_type:
        db["assets"][alias]["type"] = new_type
        print(f"✓ Updated type to '{new_type}'")

    if new_id:
        db["assets"][alias]["id"] = new_id
        print(f"✓ Updated id to '{new_id}'")

    if new_url:
        db["assets"][alias]["url"] = new_url
        db["assets"][alias]["updated_at"] = datetime.now().isoformat()
        print(f"✓ Updated url")

    save_db(db, db_path)


def get_alias(alias: str, db_path: Path = DEFAULT_DB_PATH) -> dict:
    """Get alias info. Returns None if not found."""
    db = init_db(db_path)
    return db["assets"].get(alias)


def get_url(alias: str, db_path: Path = DEFAULT_DB_PATH):
    """Print the url for an alias."""
    info = get_alias(alias, db_path)
    if info and info.get("url"):
        print(info["url"])
    else:
        print(f"Error: Alias '{alias}' not found or has no url.", file=sys.stderr)
        sys.exit(1)


def get_id(alias: str, db_path: Path = DEFAULT_DB_PATH):
    """Print the id for an alias."""
    info = get_alias(alias, db_path)
    if info and info.get("id"):
        print(info["id"])
    else:
        print(f"Error: Alias '{alias}' not found or has no id.", file=sys.stderr)
        sys.exit(1)


def get_type(alias: str, db_path: Path = DEFAULT_DB_PATH):
    """Print the type for an alias."""
    info = get_alias(alias, db_path)
    if info and info.get("type"):
        print(info["type"])
    else:
        print(f"Error: Alias '{alias}' not found or has no type.", file=sys.stderr)
        sys.exit(1)


def resolve_alias(alias: str = None, asset_id: str = None, db_path: Path = DEFAULT_DB_PATH):
    """
    Resolve alias by querying PixVerse to find missing URL.
    Can work with either alias name (lookup ID first) or direct ID.
    Supports pagination to handle >100 assets.
    """
    import subprocess

    db = init_db(db_path)

    # Get ID either from alias or directly
    if alias and not asset_id:
        if alias not in db["assets"]:
            print(f"Error: Alias '{alias}' not found.", file=sys.stderr)
            sys.exit(1)
        info = db["assets"][alias]
        asset_id = info.get("id")
        if not asset_id:
            print(f"Error: Alias '{alias}' has no ID.", file=sys.stderr)
            sys.exit(1)
        current_type = info.get("type", "unknown")
    elif asset_id:
        # Find alias by ID if exists
        found_alias = None
        current_type = None
        for a, info in db["assets"].items():
            if info.get("id") == asset_id:
                found_alias = alias
                alias = a
                current_type = info.get("type")
                break
        if not alias:
            alias = f"resolved_{asset_id}"
    else:
        print("Error: Must provide either --alias or --id", file=sys.stderr)
        sys.exit(1)

    print(f"Resolving ID: {asset_id}...")

    # Try to find with pagination support
    found = False
    resolved_url = None
    resolved_type = None
    source = None

    for src in ["upload", "create"]:
        for type_filter in ["image", "video"]:
            page = 1
            while True:
                try:
                    result = subprocess.run(
                        ["pixverse", "asset", "list", "--source", src, "--type", type_filter,
                         "--limit", "100", "--page", str(page), "--json"],
                        capture_output=True,
                        text=True,
                        timeout=60
                    )

                    if result.returncode != 0:
                        break

                    data = json.loads(result.stdout)
                    items = data.get("items", [])

                    if not items:
                        break

                    for item in items:
                        if str(item.get("asset_id")) == str(asset_id):
                            resolved_url = item.get("url")
                            resolved_type = "video" if item.get("asset_type") == 1 else "image"
                            source = src
                            found = True
                            break

                    if found:
                        break

                    # Check if there are more pages
                    has_more = data.get("has_more", False)
                    if not has_more:
                        break

                    page += 1

                except Exception as e:
                    break

            if found:
                break

        if found:
            break

    # If not found in list, or URL is null, try asset info command (for I2I assets)
    if not found or not resolved_url:
        print(f"  Not found in asset list or URL is null, trying asset info...")
        for type_filter in ["image", "video"]:
            try:
                result = subprocess.run(
                    ["pixverse", "asset", "info", str(asset_id), "--type", type_filter, "--json"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                if result.returncode == 0:
                    data = json.loads(result.stdout)
                    # Try image_url first (for I2I), then video_url, then url
                    resolved_url = data.get("image_url") or data.get("video_url") or data.get("url")
                    if resolved_url:
                        # Determine type from response
                        if "image_id" in data or "image_url" in data:
                            resolved_type = "image"
                        elif "video_id" in data or "video_url" in data:
                            resolved_type = "video"
                        else:
                            resolved_type = type_filter
                        # I2I assets are "create" source
                        source = "create"
                        found = True
                        print(f"  Found via asset info!")
                        break
            except Exception as e:
                continue

    if not found or not resolved_url:
        print(f"Error: Could not find asset with ID {asset_id} in PixVerse.", file=sys.stderr)
        sys.exit(1)

    # Update database
    if alias in db["assets"]:
        db["assets"][alias]["url"] = resolved_url
        db["assets"][alias]["source"] = source
        if resolved_type:
            db["assets"][alias]["type"] = resolved_type
        db["assets"][alias]["resolved_at"] = datetime.now().isoformat()
        action = "Updated"
    else:
        # Create new entry
        db["assets"][alias] = {
            "type": resolved_type or current_type or "image",
            "id": str(asset_id),
            "url": resolved_url,
            "source": source,
            "created_at": datetime.now().isoformat(),
            "resolved_at": datetime.now().isoformat()
        }
        action = "Created"

    save_db(db, db_path)

    url_display = resolved_url[:50] + "..." if len(resolved_url) > 50 else resolved_url
    print(f"✓ {action} alias '{alias}' -> type: {resolved_type or current_type}, source: {source}, url: {url_display}")


def saved_add(aliases: list, folder_id: str = "default", db_path: Path = DEFAULT_DB_PATH):
    """Add aliases to saved folder."""
    import subprocess

    db = init_db(db_path)

    for alias in aliases:
        if alias not in db["assets"]:
            print(f"Error: Alias '{alias}' not found. Skipping.", file=sys.stderr)
            continue

        info = db["assets"][alias]
        asset_id = info.get("id")
        asset_type = info.get("type", "image")

        if not asset_id:
            print(f"Error: Alias '{alias}' has no ID. Skipping.", file=sys.stderr)
            continue

        try:
            result = subprocess.run(
                ["pixverse", "saved", "add", asset_id, "--folder", folder_id, "--type", asset_type],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                print(f"✓ Added '{alias}' (ID: {asset_id}, type: {asset_type}) to saved folder {folder_id}")
            else:
                print(f"Error adding '{alias}': {result.stderr}", file=sys.stderr)
        except Exception as e:
            print(f"Error adding '{alias}': {e}", file=sys.stderr)


def saved_remove(aliases: list, folder_id: str = "default", db_path: Path = DEFAULT_DB_PATH):
    """Remove aliases from saved folder."""
    import subprocess

    db = init_db(db_path)

    for alias in aliases:
        if alias not in db["assets"]:
            print(f"Error: Alias '{alias}' not found. Skipping.", file=sys.stderr)
            continue

        info = db["assets"][alias]
        asset_id = info.get("id")
        asset_type = info.get("type", "image")

        if not asset_id:
            print(f"Error: Alias '{alias}' has no ID. Skipping.", file=sys.stderr)
            continue

        try:
            result = subprocess.run(
                ["pixverse", "saved", "remove", asset_id, "--folder", folder_id, "--type", asset_type],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                print(f"✓ Removed '{alias}' (ID: {asset_id}, type: {asset_type}) from saved folder {folder_id}")
            else:
                print(f"Error removing '{alias}': {result.stderr}", file=sys.stderr)
        except Exception as e:
            print(f"Error removing '{alias}': {e}", file=sys.stderr)


def set_setting(key: str, value: str, db_path: Path = DEFAULT_DB_PATH):
    """Set a setting value."""
    db = init_db(db_path)

    # Convert string values to appropriate types
    if value.lower() in ('true', 'false'):
        value = value.lower() == 'true'
    elif value.isdigit():
        value = int(value)

    db["settings"][key] = value
    save_db(db, db_path)
    print(f"✓ Set {key} = {value}")


def get_setting(key: str, db_path: Path = DEFAULT_DB_PATH):
    """Get a setting value."""
    db = init_db(db_path)
    value = db["settings"].get(key)
    if value is not None:
        print(value)
    else:
        print(f"Error: Setting '{key}' not found.", file=sys.stderr)
        sys.exit(1)


def import_aliases(file_path: str, db_path: Path = DEFAULT_DB_PATH, update_existing: bool = False):
    """
    Import aliases from a JSON or CSV file.
    Supports both old format (image_id/image_url) and new format (type/id/url).
    """
    import csv

    db = init_db(db_path)
    file_path = Path(file_path)

    if not file_path.exists():
        print(f"Error: File not found: {file_path}", file=sys.stderr)
        sys.exit(1)

    aliases_to_import = []

    # Parse file based on extension
    if file_path.suffix.lower() == '.json':
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                aliases_to_import = data
            elif isinstance(data, dict) and 'assets' in data:
                # Handle format: {"assets": {"alias": {...}}}
                for alias, info in data['assets'].items():
                    entry = {'alias': alias}
                    entry.update(info)
                    aliases_to_import.append(entry)
            else:
                print("Error: JSON must be a list or have 'assets' key", file=sys.stderr)
                sys.exit(1)

    elif file_path.suffix.lower() == '.csv':
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            aliases_to_import = list(reader)
    else:
        print(f"Error: Unsupported file format: {file_path.suffix}", file=sys.stderr)
        print("Supported formats: .json, .csv", file=sys.stderr)
        sys.exit(1)

    imported = 0
    updated = 0
    skipped = 0

    for entry in aliases_to_import:
        alias = entry.get('alias')
        if not alias:
            print(f"Warning: Skipping entry without alias: {entry}")
            skipped += 1
            continue

        # Support both old and new format
        if 'type' in entry:
            # New format
            asset_type = entry.get('type', 'image')
            asset_id = entry.get('id', '')
            url = entry.get('url', '')
            cover_url = entry.get('cover_url')
        else:
            # Old format - detect type
            if 'image_id' in entry:
                asset_type = 'image'
                asset_id = entry.get('image_id', '')
                url = entry.get('image_url', '')
                cover_url = None
            elif 'video_id' in entry:
                asset_type = 'video'
                asset_id = entry.get('video_id', '')
                url = entry.get('video_url', '')
                cover_url = entry.get('cover_url')
            else:
                # Default to image
                asset_type = 'image'
                asset_id = entry.get('id', '')
                url = entry.get('url', '')
                cover_url = None

        # Check if alias exists
        if alias in db['assets']:
            if not update_existing:
                print(f"Skipping existing alias: {alias}")
                skipped += 1
                continue
            # Update existing
            db['assets'][alias].update({
                'type': asset_type,
                'id': asset_id,
                'url': url,
                'cover_url': cover_url,
                'updated_at': datetime.now().isoformat()
            })
            updated += 1
            print(f"✓ Updated: {alias}")
        else:
            # Add new
            db['assets'][alias] = {
                'created_at': datetime.now().isoformat(),
                'type': asset_type,
                'id': asset_id,
                'url': url,
            }
            if cover_url:
                db['assets'][alias]['cover_url'] = cover_url
            imported += 1
            print(f"✓ Added: {alias}")

    save_db(db, db_path)
    print(f"\n✓ Import complete: {imported} added, {updated} updated, {skipped} skipped")


def export_aliases(file_path: str, format_type: str = 'json', db_path: Path = DEFAULT_DB_PATH):
    """Export aliases to a JSON or CSV file."""
    import csv

    db = init_db(db_path)

    if not db['assets']:
        print("No aliases to export.")
        return

    file_path = Path(file_path)

    if format_type.lower() == 'json':
        export_data = {
            'exported_at': datetime.now().isoformat(),
            'count': len(db['assets']),
            'assets': db['assets']
        }
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, ensure_ascii=False, indent=2)

    elif format_type.lower() == 'csv':
        fieldnames = ['alias', 'type', 'id', 'url', 'cover_url', 'created_at']
        with open(file_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for alias, info in db['assets'].items():
                row = {'alias': alias}
                row.update(info)
                writer.writerow(row)
    else:
        print(f"Error: Unsupported format: {format_type}", file=sys.stderr)
        print("Supported formats: json, csv", file=sys.stderr)
        sys.exit(1)

    print(f"✓ Exported {len(db['assets'])} alias(es) to {file_path}")


def sync_aliases(db_path: Path = DEFAULT_DB_PATH, dry_run: bool = False):
    """
    Sync local aliases with PixVerse online assets.
    One-way sync: Remove local aliases if their corresponding online asset is deleted.
    """
    import subprocess

    db = init_db(db_path)

    if not db["assets"]:
        print("No local aliases to sync.")
        return

    print(f"Found {len(db['assets'])} local alias(es)")
    print("Fetching online assets from PixVerse...")

    try:
        result = subprocess.run(
            ["pixverse", "asset", "list", "--limit", "1000", "--json"],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            print(f"Error fetching online assets: {result.stderr}", file=sys.stderr)
            sys.exit(1)

        online_data = json.loads(result.stdout)
        online_assets = online_data.get("items", [])

        # Build set of online asset IDs
        online_ids = set()
        for asset in online_assets:
            if asset.get("asset_id"):
                online_ids.add(str(asset["asset_id"]))
            if asset.get("video_id"):
                online_ids.add(str(asset["video_id"]))
            if asset.get("img_id"):
                online_ids.add(str(asset["img_id"]))

        print(f"Found {len(online_assets)} online asset(s)")

        # Find aliases to remove
        aliases_to_remove = []

        for alias, info in db["assets"].items():
            asset_id = info.get("id")

            # Check if this alias exists online
            exists_online = False

            if asset_id and str(asset_id) in online_ids:
                exists_online = True

            # Additional check: try to fetch asset info directly
            if not exists_online and asset_id:
                try:
                    check_result = subprocess.run(
                        ["pixverse", "asset", "info", str(asset_id), "--json"],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    if check_result.returncode == 0:
                        exists_online = True
                except:
                    pass

            if not exists_online:
                aliases_to_remove.append(alias)

        if not aliases_to_remove:
            print("✓ All local aliases are synced with online assets.")
            return

        print(f"\nFound {len(aliases_to_remove)} alias(es) that no longer exist online:")
        for alias in aliases_to_remove:
            info = db["assets"][alias]
            print(f"  - {alias} (type: {info.get('type', 'unknown')}, id: {info.get('id', 'N/A')})")

        if dry_run:
            print("\n[DRY RUN] No changes made. Use without --dry-run to actually remove.")
            return

        # Remove stale aliases
        print("\nRemoving stale aliases...")
        for alias in aliases_to_remove:
            del db["assets"][alias]
            print(f"  ✓ Removed '{alias}'")

        save_db(db, db_path)
        print(f"\n✓ Sync complete. Removed {len(aliases_to_remove)} stale alias(es).")

    except subprocess.TimeoutExpired:
        print("Error: Timeout while fetching online assets.", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Failed to parse PixVerse response: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error during sync: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Manage PixVerse asset aliases (supports image and video)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Add image alias
  %(prog)s add --alias 萧千灵_v1 --type image --id 395126274650554 --url "https://..."

  # Add video alias
  %(prog)s add --alias 战斗场景_01 --type video --id 123456 --url "https://..." --cover-url "https://..."

  # Add from pixverse create output (pipe JSON)
  pixverse create image --prompt "..." --json | %(prog)s add-from-json --alias 萧千灵_v1

  # List all aliases
  %(prog)s list

  # List only video aliases
  %(prog)s list --type video

  # Get URL for alias
  %(prog)s get-url --alias 萧千灵_v1

  # Remove alias
  %(prog)s remove --alias 萧千灵_v1

  # Update alias
  %(prog)s update --alias 萧千灵_v1 --new-alias 萧千灵_v2 --new-url "https://..."
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Add command
    add_parser = subparsers.add_parser('add', help='Add a new alias')
    add_parser.add_argument('--alias', required=True, help='Alias name')
    add_parser.add_argument('--type', choices=['image', 'video'], required=True, help='Asset type')
    add_parser.add_argument('--id', required=True, help='PixVerse asset ID (image_id or video_id)')
    add_parser.add_argument('--url', required=True, help='PixVerse asset URL')
    add_parser.add_argument('--cover-url', help='Cover URL (for videos)')
    add_parser.add_argument('--duration', type=int, help='Duration in seconds (for videos)')

    # Add from JSON command
    add_json_parser = subparsers.add_parser('add-from-json', help='Add alias from pixverse create JSON output')
    add_json_parser.add_argument('--alias', required=True, help='Alias name')
    add_json_parser.add_argument('--file', help='Read JSON from file (default: stdin)')

    # List command
    list_parser = subparsers.add_parser('list', help='List all aliases')
    list_parser.add_argument('--format', choices=['table', 'json'], default='table', help='Output format')
    list_parser.add_argument('--type', choices=['image', 'video'], help='Filter by asset type')

    # Remove command
    remove_parser = subparsers.add_parser('remove', help='Remove an alias')
    remove_parser.add_argument('--alias', required=True, help='Alias to remove')

    # Update command
    update_parser = subparsers.add_parser('update', help='Update an alias')
    update_parser.add_argument('--alias', required=True, help='Current alias name')
    update_parser.add_argument('--new-alias', help='New alias name')
    update_parser.add_argument('--new-type', choices=['image', 'video'], help='New asset type')
    update_parser.add_argument('--new-id', help='New asset ID')
    update_parser.add_argument('--new-url', help='New URL')

    # Get URL command
    geturl_parser = subparsers.add_parser('get-url', help='Get URL for an alias')
    geturl_parser.add_argument('--alias', required=True, help='Alias name')

    # Get ID command
    getid_parser = subparsers.add_parser('get-id', help='Get ID for an alias')
    getid_parser.add_argument('--alias', required=True, help='Alias name')

    # Get type command
    gettype_parser = subparsers.add_parser('get-type', help='Get type for an alias')
    gettype_parser.add_argument('--alias', required=True, help='Alias name')

    # Set command
    set_parser = subparsers.add_parser('set', help='Set a setting')
    set_parser.add_argument('--key', required=True, help='Setting key')
    set_parser.add_argument('--value', required=True, help='Setting value')

    # Get setting command
    getset_parser = subparsers.add_parser('get-setting', help='Get a setting value')
    getset_parser.add_argument('--key', required=True, help='Setting key')

    # Import command
    import_parser = subparsers.add_parser('import', help='Import aliases from JSON or CSV')
    import_parser.add_argument('--file', required=True, help='Path to import file')
    import_parser.add_argument('--update', action='store_true', help='Update existing aliases')

    # Export command
    export_parser = subparsers.add_parser('export', help='Export aliases to JSON or CSV')
    export_parser.add_argument('--file', required=True, help='Path to export file')
    export_parser.add_argument('--format', choices=['json', 'csv'], help='Export format')

    # Sync command
    sync_parser = subparsers.add_parser('sync', help='Sync with PixVerse (remove stale)')
    sync_parser.add_argument('--dry-run', action='store_true', help='Preview changes')

    # Resolve command - new in 1.1.0
    resolve_parser = subparsers.add_parser('resolve', help='Resolve alias URL by querying PixVerse (for upload assets)')
    resolve_parser.add_argument('--alias', help='Alias name to resolve')
    resolve_parser.add_argument('--id', help='Asset ID to resolve (creates new alias if not exists)')

    # Add from upload command - new in 1.1.0
    add_upload_parser = subparsers.add_parser('add-from-upload', help='Add alias from pixverse asset upload JSON output')
    add_upload_parser.add_argument('--alias', help='Alias name (default: auto-detect from filename)')
    add_upload_parser.add_argument('--file', help='Read JSON from file (default: stdin)')

    # Saved command group - new in 1.1.0
    saved_parser = subparsers.add_parser('saved', help='Manage saved folders (PixVerse CLI 1.1.0+)')
    saved_subparsers = saved_parser.add_subparsers(dest='saved_command', help='Saved folder commands')

    # saved add
    saved_add_parser = saved_subparsers.add_parser('add', help='Add aliases to saved folder')
    saved_add_parser.add_argument('--alias', action='append', required=True, help='Alias(es) to add (can be used multiple times)')
    saved_add_parser.add_argument('--folder', default='default', help='Folder ID (default: default)')

    # saved remove
    saved_remove_parser = saved_subparsers.add_parser('remove', help='Remove aliases from saved folder')
    saved_remove_parser.add_argument('--alias', action='append', required=True, help='Alias(es) to remove (can be used multiple times)')
    saved_remove_parser.add_argument('--folder', default='default', help='Folder ID (default: default)')

    args = parser.parse_args()

    if args.command == 'add':
        add_alias(args.alias, args.type, args.id, args.url, args.cover_url, args.duration)
    elif args.command == 'add-from-json':
        if args.file:
            with open(args.file, 'r') as f:
                json_output = f.read()
        else:
            json_output = sys.stdin.read()
        add_from_pixverse_output(args.alias, json_output)
    elif args.command == 'list':
        list_aliases(args.format, args.type)
    elif args.command == 'remove':
        remove_alias(args.alias)
    elif args.command == 'update':
        if not args.new_alias and not args.new_id and not args.new_url and not args.new_type:
            print("Error: Must specify at least one field to update", file=sys.stderr)
            sys.exit(1)
        update_alias(args.alias, args.new_alias, args.new_id, args.new_url, args.new_type)
    elif args.command == 'get-url':
        get_url(args.alias)
    elif args.command == 'get-id':
        get_id(args.alias)
    elif args.command == 'get-type':
        get_type(args.alias)
    elif args.command == 'set':
        set_setting(args.key, args.value)
    elif args.command == 'get-setting':
        get_setting(args.key)
    elif args.command == 'import':
        import_aliases(args.file, update_existing=args.update)
    elif args.command == 'export':
        export_format = args.format or Path(args.file).suffix.lstrip('.')
        export_aliases(args.file, format_type=export_format)
    elif args.command == 'sync':
        sync_aliases(dry_run=args.dry_run)
    elif args.command == 'resolve':
        resolve_alias(alias=args.alias, asset_id=args.id)
    elif args.command == 'add-from-upload':
        if args.file:
            with open(args.file, 'r') as f:
                json_output = f.read()
        else:
            json_output = sys.stdin.read()
        # If alias not provided, try to extract from JSON
        if args.alias:
            add_from_upload_output(args.alias, json_output)
        else:
            # Extract filename from JSON and use as alias
            try:
                data = json.loads(json_output)
                path = data.get("path", "")
                filename = path.split("/")[-1].split(".")[0] if path else "uploaded_asset"
                add_from_upload_output(filename, json_output)
            except:
                add_from_upload_output("uploaded_asset", json_output)
    elif args.command == 'saved':
        if args.saved_command == 'add':
            saved_add(args.alias, args.folder)
        elif args.saved_command == 'remove':
            saved_remove(args.alias, args.folder)
        else:
            saved_parser.print_help()
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()

---
name: pixverse-asset-alias
description: |
  Manage PixVerse CLI assets (images and videos) with human-readable aliases. Use this skill when:
  1. User wants to save pixverse create results as aliases
  2. User says "save this result as ..." after pixverse create command
  3. User wants to use pvcreate wrapper for automatic alias saving
  4. User wants to manage image/video aliases (add, list, remove, update)
  5. User mentions mapping asset names to URLs for PixVerse
  6. User wants to batch import/export aliases
  
  This skill supports both image and video assets with automatic type detection.
---

# PixVerse Asset Alias Manager

This skill helps you manage PixVerse image and video assets using human-readable aliases instead of long IDs or URLs.

**Core mapping:** `alias` → `type` → `id` → `url`

## Features

1. **Automatic alias saving**: Use `pvcreate` wrapper or say "save as ..." after create command
2. **Image & Video support**: Unified format for both asset types
3. **Command alias expansion**: Convert `--alias_name` to `--image <url>` in pixverse commands
4. **Batch operations**: Import/export aliases in JSON/CSV format
5. **Sync with PixVerse**: Remove local aliases if online asset is deleted
6. **Resolve upload assets**: Query PixVerse by ID to find URL for uploaded assets
7. **Upload with alias**: Auto-save alias when uploading assets (PixVerse CLI 1.1.0+)
8. **Saved folder support**: Add/remove aliases to saved folders (PixVerse CLI 1.1.0+)

> **重要提示：所有 PixVerse CLI 命令必须基于官方文档**
> - 使用 `pixverse --help` 或 `pixverse <command> --help` 查看官方命令格式
> - **不许自己瞎编命令参数或行为假设**，所有用法必须经实际 CLI 输出验证
> - 本 SKILL.md 文档基于 PixVerse CLI 1.1.0+ 版本，CLI 更新时请以实际 help 输出为准

## Storage Format

Assets are stored in `~/.claude/pixverse_assets.json`:

```json
{
  "assets": {
    "萧千灵_v1": {
      "type": "image",
      "id": "395126274650554",
      "url": "https://media.pixverse.ai/pixverse%2Fi2i%2Fori%2Fxxx.png",
      "created_at": "2024-01-15T10:30:00Z"
    },
    "战斗场景_01": {
      "type": "video",
      "id": "123456789",
      "url": "https://media.pixverse.ai/...",
      "cover_url": "https://media.pixverse.ai/...",
      "duration": 5,
      "created_at": "2024-01-15T10:35:00Z"
    }
  },
  "settings": {
    "confirm_before_replace": true
  }
}
```

## Usage Patterns

### 1. Automatic alias saving (pvcreate wrapper)

When creating assets and want to auto-save as alias:

```bash
pvcreate image --prompt "A sunset" --save-alias 日落_v1 --json
pvcreate video --prompt "Animate this" --image ./photo.jpg --save-alias 动画_01 --json
```

Steps:
1. Use `pvcreate` instead of `pixverse create`
2. Add `--save-alias <name>` to auto-save after generation
3. The wrapper automatically calls the management script

**pvcreate commands:**
```bash
pvcreate image --prompt "..." --save-alias <name> [--json]
pvcreate video --prompt "..." --save-alias <name> [--json]
pvcreate transition --prompt "..." --save-alias <name> [--json]
pvcreate reference --images ... --save-alias <name> [--json]
# ... all other pixverse create subcommands
```

### 2. Interactive alias saving

When user runs normal pixverse create command:

```
User: pixverse create image --prompt "A beautiful landscape" --json
[JSON output shown]
User: save this as 风景_v1
```

Steps:
1. User runs `pixverse create` command
2. Claude sees JSON output in conversation
3. User says "save this as <alias>" or "save as <alias>"
4. Parse the JSON output to extract:
   - `image_id` → type=image
   - `video_id` → type=video
   - Corresponding URL field
5. Add to database with `add-from-json` command

**Commands:**
```bash
# Parse from stdin (pipe)
pixverse create image --prompt "..." --json | python manage_assets.py add-from-json --alias "名称"

# Parse from file
pixverse create video --prompt "..." --json > /tmp/result.json
python manage_assets.py add-from-json --alias "名称" --file /tmp/result.json
```

### 3. Manual alias management

**Add image alias:**
```bash
python manage_assets.py add --alias "萧千灵_v1" --type image --id "395126274650554" --url "https://..."
```

**Add video alias:**
```bash
python manage_assets.py add --alias "战斗场景_01" --type video --id "123456" --url "https://..." --cover-url "https://..."
```

**List all aliases:**
```bash
python manage_assets.py list
```

**List only videos:**
```bash
python manage_assets.py list --type video
```

**Get URL for alias:**
```bash
python manage_assets.py get-url --alias "萧千灵_v1"
```

**Remove alias:**
```bash
python manage_assets.py remove --alias "萧千灵_v1"
```

**Update alias:**
```bash
python manage_assets.py update --alias "萧千灵_v1" --new-alias "萧千灵_v2"
python manage_assets.py update --alias "萧千灵_v1" --new-url "https://..."
```

### 4. Command alias expansion

When user runs pixverse create with alias syntax:

**Image alias:**
```
User: pixverse create video --prompt "Slow zoom in" --image --萧千灵_v1
```

**Video alias:**
```
User: pixverse create extend --video --战斗场景_01
```

Steps:
1. Detect `--<alias>` pattern in the command
2. Look up in `~/.claude/pixverse_assets.json`
3. If found, get `url` and `type`
4. Replace with appropriate parameter (`--image` for images, `--video` for videos)
5. Execute the converted command

### 5. Batch operations

**Export aliases:**
```bash
# Export to JSON
python manage_assets.py export --file ./backup.json

# Export to CSV
python manage_assets.py export --file ./backup.csv
```

**Import aliases:**
```bash
# Import from JSON (skip existing)
python manage_assets.py import --file ./backup.json

# Import with update
python manage_assets.py import --file ./updates.csv --update
```

**Supported formats:**
- JSON with `assets` key: `{"assets": {"alias": {...}}}`
- JSON list: `[{"alias": "name", "type": "image", ...}]`
- CSV with headers: `alias,type,id,url,cover_url,created_at`

### 6. Sync aliases with PixVerse

```bash
# Preview what would be removed
python manage_assets.py sync --dry-run

# Actually remove stale aliases
python manage_assets.py sync
```

## Management Script API

```bash
# Add new alias
python manage_assets.py add --alias <name> --type <image|video> --id <id> --url <url> [--cover-url <url>]

# Add from pixverse JSON output
python manage_assets.py add-from-json --alias <name> [--file <path>]

# List all aliases
python manage_assets.py list [--format table|json] [--type image|video]

# Get URL/ID/type for alias
python manage_assets.py get-url --alias <name>
python manage_assets.py get-id --alias <name>
python manage_assets.py get-type --alias <name>

# Remove alias
python manage_assets.py remove --alias <name>

# Update alias
python manage_assets.py update --alias <name> [--new-alias <name>] [--new-type <type>] [--new-id <id>] [--new-url <url>]

# Settings
python manage_assets.py set --key confirm_before_replace --value false

# Sync with PixVerse
python manage_assets.py sync [--dry-run]

# Export/Import
python manage_assets.py export --file <path>
python manage_assets.py import --file <path> [--update]

# Resolve upload assets (PixVerse CLI 1.1.0+)
python manage_assets.py resolve --id <asset_id>                    # Create new alias from ID
python manage_assets.py resolve --alias <name>                     # Update existing alias

# Upload with alias (PixVerse CLI 1.1.0+)
pixverse asset upload ./image.png --json | python manage_assets.py add-from-upload
pixverse asset upload ./image.png --json | python manage_assets.py add-from-upload --alias 我的图片

# Saved folder operations (PixVerse CLI 1.1.0+)
python manage_assets.py saved add --alias <name> --folder <folder_id>
python manage_assets.py saved add --alias <name1> --alias <name2> --folder <folder_id>
python manage_assets.py saved remove --alias <name> --folder <folder_id>
```

## Important Notes

- **New format**: Uses `type`, `id`, `url` fields (old `image_id`/`image_url` auto-migrated)
- **Auto-type detection**: Automatically detects image vs video from pixverse output
- **pvcreate wrapper**: Use `--save-alias` for automatic saving
- **Interactive saving**: Say "save this as <name>" after any pixverse create command
- **Alias uniqueness**: Each alias must be unique across all asset types

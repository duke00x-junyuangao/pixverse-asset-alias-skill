# PixVerse Asset Alias Manager

A Claude Code skill for managing [PixVerse](https://pixverse.ai) CLI assets (images and videos) with human-readable aliases. Stop copy-pasting long asset IDs and URLs — assign memorable names and reference them directly in commands.

---

## What It Does

PixVerse CLI returns assets as opaque IDs and URLs. This skill introduces a lightweight alias registry so you can:

- Save generated assets as `sunset_v1` instead of memorizing `395126274650554`
- Reference aliases directly in `pixverse create` commands
- Manage a local catalog of images and videos with batch import/export
- Sync local aliases against live PixVerse assets to remove stale entries

**Core mapping:** `alias` → `type` → `id` → `url`

---

## Features

| Feature | Description |
|:---|:---|
| **Automatic alias saving** | Wrap `pixverse create` with `pvcreate --save-alias <name>` to generate and save in one step |
| **Interactive saving** | Say "save this as `<name>`" after any `pixverse create --json` output |
| **Command alias expansion** | Use `--<alias>` in commands; the skill resolves it to `--image <url>` or `--video <url>` |
| **Image & video support** | Unified format for both asset types with automatic type detection |
| **Batch operations** | Import/export aliases in JSON or CSV format |
| **Cloud sync** | Remove local aliases when the corresponding online asset has been deleted |
| **Upload tracking** | Auto-save aliases when uploading local files via `pixverse asset upload` |
| **Saved folder integration** | Add or remove aliases from PixVerse saved folders (CLI 1.1.0+) |
| **Resolve by ID** | Query PixVerse for the URL of an uploaded asset when only the ID is known |

---

## Prerequisites

- **PixVerse CLI** >= 1.1.0
  ```bash
  npm install -g pixverse
  ```
- **Python** >= 3.8
- **Bash** (for the `pvcreate` wrapper)
- A PixVerse account with active subscription (CLI requires subscription)

---

## Installation

This skill is automatically available when placed in your Claude Code skills directory:

```bash
# Clone into the skills directory
git clone https://github.com/duke00x-junyuangao/pixverse-asset-alias-skill.git \
  ~/.claude/skills/pixverse-asset-alias
```

No additional build step is required.

---

## Quick Start

### 1. Generate and auto-save

```bash
# Create an image and save it as "sunset_v1"
pvcreate image --prompt "A sunset over mountains" --json --save-alias sunset_v1

# Create a video and save it as "ocean_clip"
pvcreate video --prompt "Ocean waves crashing on rocks" --json --save-alias ocean_clip
```

### 2. List your aliases

```bash
python scripts/manage_assets.py list
```

### 3. Use an alias in a new command

```bash
# Reference an image alias with --<alias>
pixverse create video --prompt "Slow zoom in" --image --sunset_v1

# Reference a video alias
pixverse create extend --video --ocean_clip
```

### 4. Save after the fact

```bash
# Run a normal create command
pixverse create image --prompt "A beautiful landscape" --json > result.json

# Then save the result interactively
python scripts/manage_assets.py add-from-json --alias landscape_v1 --file result.json
```

---

## Management Script API

### Add aliases

```bash
# Manual add
python scripts/manage_assets.py add \
  --alias "character_v1" \
  --type image \
  --id "395126274650554" \
  --url "https://media.pixverse.ai/..."

# Add from pixverse JSON output
python scripts/manage_assets.py add-from-json --alias "scene_01"

# Add from uploaded asset
pixverse asset upload ./photo.png --json | python scripts/manage_assets.py add-from-upload --alias my_photo
```

### Query aliases

```bash
python scripts/manage_assets.py list                    # All aliases
python scripts/manage_assets.py list --type video       # Only videos
python scripts/manage_assets.py get-url --alias sunset_v1
python scripts/manage_assets.py get-id --alias sunset_v1
python scripts/manage_assets.py get-type --alias sunset_v1
```

### Modify aliases

```bash
python scripts/manage_assets.py update --alias sunset_v1 --new-alias sunset_v2
python scripts/manage_assets.py remove --alias sunset_v1
```

### Sync with PixVerse

```bash
python scripts/manage_assets.py sync --dry-run   # Preview stale entries
python scripts/manage_assets.py sync              # Remove stale entries
```

### Batch import/export

```bash
# Export
python scripts/manage_assets.py export --file ./backup.json
python scripts/manage_assets.py export --file ./backup.csv

# Import
python scripts/manage_assets.py import --file ./backup.json
python scripts/manage_assets.py import --file ./updates.csv --update
```

### Saved folder operations (CLI 1.1.0+)

```bash
python scripts/manage_assets.py saved add --alias sunset_v1 --folder 12345
python scripts/manage_assets.py saved remove --alias sunset_v1 --folder 12345
```

### Resolve upload assets (CLI 1.1.0+)

```bash
# Create a new alias from an asset ID
python scripts/manage_assets.py resolve --id 395126274650554

# Update an existing alias by ID
python scripts/manage_assets.py resolve --alias character_v1
```

---

## Storage Format

Aliases are stored in `~/.claude/pixverse_assets.json`:

```json
{
  "assets": {
    "sunset_v1": {
      "type": "image",
      "id": "395126274650554",
      "url": "https://media.pixverse.ai/...",
      "created_at": "2024-01-15T10:30:00Z"
    },
    "ocean_clip": {
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

The database is automatically migrated if an older format (`image_id`/`image_url`) is detected.

---

## Supported Import/Export Formats

| Format | Structure |
|:---|:---|
| **JSON (nested)** | `{"assets": {"alias": {type, id, url, ...}}}` |
| **JSON (list)** | `[{"alias": "name", "type": "image", "id": "...", ...}]` |
| **CSV** | Headers: `alias,type,id,url,cover_url,created_at` |

---

## Settings

```bash
# Disable confirmation before overwriting an existing alias
python scripts/manage_assets.py set --key confirm_before_replace --value false
```

---

## Dependencies

| Dependency | Version | Purpose |
|:---|:---|:---|
| `pixverse` | >= 1.1.0 | PixVerse CLI for asset generation, upload, and cloud queries |
| `python3` | >= 3.8 | Runtime for `manage_assets.py` |
| `bash` | any | Required by the `pvcreate` wrapper script |

No external Python packages are required — the script uses only the standard library (`argparse`, `json`, `os`, `sys`, `datetime`, `pathlib`, `typing`).

---

## Related Skills

- [`pixverse-ai-image-and-video-generator`](https://github.com/PixVerseAI/skills) — Core PixVerse CLI skill for generating videos and images
- `pixverse-batch-producer` — Batch generation of first-frame images and videos from storyboards

---

## License

MIT

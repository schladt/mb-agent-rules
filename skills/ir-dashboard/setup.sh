#!/usr/bin/env bash
# Sets up the IR Dashboard in a project that uses the incident-response memory bank profile.
# Run from the mb-agent-rules repo: bash skills/ir-dashboard/setup.sh /path/to/project
set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")" && pwd)"

usage() {
  echo "Usage: $0 <project-root> [options]"
  echo ""
  echo "Options:"
  echo "  --title <title>       Dashboard title (default: IR Dashboard)"
  echo "  --brand <brand>       Brand text in header (optional)"
  echo "  --accent <hex>        Accent color (default: #3b82f6)"
  echo "  --logo <path-or-data> /static/ path or data:image URL (optional)"
  echo "  --shared-group        Use group-readable evidence modes (0770/0660)"
  echo "  --with-sample-data    Copy sample data into incoming/ for demo"
  echo "  --help                Show this help"
  exit 1
}

if [ $# -lt 1 ] || [ "$1" = "--help" ]; then
  usage
fi

PROJECT_ROOT="$1"
shift

TITLE="IR Dashboard"
BRAND=""
ACCENT="#3b82f6"
LOGO=""
SAMPLE_DATA=false
SHARED_GROUP=false
SHARED_GROUP_SET=false

while [ $# -gt 0 ]; do
  case "$1" in
    --title|--brand|--accent|--logo)
      [ $# -ge 2 ] || { echo "Option $1 requires a value"; exit 2; }
      case "$1" in
        --title) TITLE="$2" ;;
        --brand) BRAND="$2" ;;
        --accent) ACCENT="$2" ;;
        --logo) LOGO="$2" ;;
      esac
      shift 2
      ;;
    --shared-group) SHARED_GROUP=true; SHARED_GROUP_SET=true; shift ;;
    --with-sample-data) SAMPLE_DATA=true; shift ;;
    *) echo "Unknown option: $1"; usage ;;
  esac
done

if [ ! -d "$PROJECT_ROOT" ]; then
  echo "Error: Project root '$PROJECT_ROOT' does not exist."
  exit 1
fi

python3 - "$ACCENT" "$LOGO" <<'PYVALIDATE'
import re
import sys

accent, logo = sys.argv[1:]
if not re.fullmatch(r"#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?(?:[0-9a-fA-F]{2})?", accent):
    raise SystemExit("--accent must be a 3, 6, or 8 digit hex color")
if logo and not (logo.startswith("/static/") or logo.startswith("data:image/")):
    raise SystemExit("--logo must be a /static/ path or data:image URL")
PYVALIDATE

CONFIG_FILE="$PROJECT_ROOT/dashboard.config.json"
if [ "$SHARED_GROUP_SET" = false ] && [ -f "$CONFIG_FILE" ]; then
  SHARED_GROUP="$(python3 - "$CONFIG_FILE" <<'PYREAD'
import json
import sys
try:
    with open(sys.argv[1], encoding="utf-8") as handle:
        config = json.load(handle)
    value = config.get("shared_group_access", False) is True
except (OSError, ValueError, AttributeError):
    value = False
print("true" if value else "false")
PYREAD
)"
fi

echo ""
echo "============================================================"
echo "  IR Dashboard Setup"
echo "============================================================"
echo "  Project    : $PROJECT_ROOT"
echo "  Title      : $TITLE"
echo "  Accent     : $ACCENT"
if [ -n "$BRAND" ]; then echo "  Brand      : $BRAND"; fi
if [ -n "$LOGO" ];  then echo "  Logo       : $LOGO"; fi
echo "============================================================"
echo ""

# Copy dashboard
if [ -d "$PROJECT_ROOT/dashboard" ]; then
  echo "  ⚠  dashboard/ already exists — skipping (delete it first to reinstall)"
else
  cp -r "$SKILL_DIR/dashboard" "$PROJECT_ROOT/dashboard"
  chmod +x "$PROJECT_ROOT/dashboard/start.sh"
  echo "  ✓  Copied dashboard/"
fi

# Copy scripts (merge if exists)
mkdir -p "$PROJECT_ROOT/scripts"
for script in intake.py sync_check.py; do
  if [ ! -f "$PROJECT_ROOT/scripts/$script" ]; then
    cp "$SKILL_DIR/scripts/$script" "$PROJECT_ROOT/scripts/$script"
    echo "  ✓  Copied scripts/$script"
  else
    echo "  ⚠  scripts/$script already exists — skipping"
  fi
done

# Create sensitive directories with explicit deployment-appropriate modes.
for sensitive_dir in "$PROJECT_ROOT/incoming" "$PROJECT_ROOT/artifacts"; do
  if [ -L "$sensitive_dir" ]; then
    echo "Error: sensitive directory must not be a symlink: $sensitive_dir"
    exit 1
  fi
done
mkdir -p "$PROJECT_ROOT/incoming" "$PROJECT_ROOT/artifacts"
if [ "$SHARED_GROUP" = true ]; then
  find "$PROJECT_ROOT/incoming" "$PROJECT_ROOT/artifacts" -type d -exec chmod 0770 {} +
  find "$PROJECT_ROOT/incoming" "$PROJECT_ROOT/artifacts" -type f -exec chmod 0660 {} +
else
  find "$PROJECT_ROOT/incoming" "$PROJECT_ROOT/artifacts" -type d -exec chmod 0700 {} +
  find "$PROJECT_ROOT/incoming" "$PROJECT_ROOT/artifacts" -type f -exec chmod 0600 {} +
fi
echo "  ✓  Created incoming/ and artifacts/"

# Create dashboard.config.json
if [ ! -f "$CONFIG_FILE" ]; then
  python3 - "$CONFIG_FILE" "$TITLE" "$BRAND" "$ACCENT" "$LOGO" "$SHARED_GROUP" <<'PYCONFIG'
import json
import sys

path, title, brand, accent, logo, shared = sys.argv[1:]
with open(path, "w", encoding="utf-8") as handle:
    json.dump({
        "title": title,
        "brand": brand,
        "accent_color": accent,
        "logo_url": logo,
        "css_overrides": {},
        "shared_group_access": shared == "true",
        "atomic_max_file_bytes": 104857600,
        "atomic_max_records": 250000,
        "atomic_max_fields": 250,
    }, handle, indent=2)
    handle.write("\n")
PYCONFIG
  echo "  ✓  Created dashboard.config.json"
else
  if [ "$SHARED_GROUP_SET" = true ]; then
    python3 - "$CONFIG_FILE" <<'PYUPDATE'
import json
import os
import sys
import tempfile

path = sys.argv[1]
with open(path, encoding="utf-8") as handle:
    config = json.load(handle)
if not isinstance(config, dict):
    raise SystemExit("dashboard.config.json must contain an object")
config["shared_group_access"] = True
directory = os.path.dirname(path) or "."
fd, temporary = tempfile.mkstemp(prefix=".dashboard.config.", dir=directory, text=True)
try:
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(config, handle, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
finally:
    if os.path.exists(temporary):
        os.unlink(temporary)
PYUPDATE
    echo "  ✓  Enabled shared_group_access in existing dashboard.config.json"
  fi
  echo "  ⚠  dashboard.config.json already exists — skipping"
fi

# Create reviewQueue.md if it doesn't exist
RQ_FILE="$PROJECT_ROOT/memory-bank/reviewQueue.md"
if [ -d "$PROJECT_ROOT/memory-bank" ] && [ ! -f "$RQ_FILE" ]; then
  cat > "$RQ_FILE" << 'EOFRQ'
# Review Queue

Tracks all pending judgment calls and downstream updates.
Items are added by `intake.py` or manually. Checked off by the analyst/AI after completion.

Status values: `PENDING` | `IN_PROGRESS` | `DONE`

---

## Pending Review

(No pending items)

---

## Done

EOFRQ
  echo "  ✓  Created memory-bank/reviewQueue.md"
fi

# Exclude sensitive and generated runtime state from version control.
GITIGNORE="$PROJECT_ROOT/.gitignore"
touch "$GITIGNORE"
for ignored in artifacts/ incoming/ dashboard/certs/ dashboard/venv/ dashboard/cache/; do
  grep -qxF "$ignored" "$GITIGNORE" 2>/dev/null || echo "$ignored" >> "$GITIGNORE"
done
echo "  ✓  Ensured evidence and dashboard runtime state are in .gitignore"

if [ ! -f "$PROJECT_ROOT/.agents/skills/evidence-review/SKILL.md" ] && [ ! -f "$PROJECT_ROOT/.claude/skills/evidence-review/SKILL.md" ]; then
  echo "  ⚠  evidence-review skill is not installed in this project."
  echo "     Re-run init-agent-rules incident-response so agents can process the review queue."
fi

# Copy sample data
if [ "$SAMPLE_DATA" = true ]; then
  cp "$SKILL_DIR/sample-data/"*.json "$PROJECT_ROOT/incoming/"
  if [ "$SHARED_GROUP" = true ]; then
    chmod 0660 "$PROJECT_ROOT/incoming/"*.json
  else
    chmod 0600 "$PROJECT_ROOT/incoming/"*.json
  fi
  echo "  ✓  Copied sample data to incoming/ (run intake to process)"
fi

echo ""
echo "  Setup complete. Start the dashboard:"
echo ""
echo "    cd $PROJECT_ROOT/dashboard"
echo "    bash start.sh --port 8443"
echo ""
echo "  Or supply a specific password through the environment:"
echo ""
echo "    DASHBOARD_PASSWORD='use-a-secret-manager' bash start.sh --port 8443"
echo ""
if [ "$SAMPLE_DATA" = true ]; then
  echo "  Sample data is in incoming/. Click 'Sync Check' → 'Run Intake'"
  echo "  in the dashboard to process it, or run:"
  echo ""
  echo "    python scripts/intake.py"
  echo ""
fi
echo "============================================================"

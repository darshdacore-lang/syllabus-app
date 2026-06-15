#!/usr/bin/env python3
"""Generate the app icon for the Electron app."""

import sys
from pathlib import Path

# Add the app directory to the path so we can import the icon generator
root = Path(__file__).parent.parent
sys.path.insert(0, str(root))

from app.ui.app_icon import write_png

# Generate the icon
assets_dir = root / "assets"
assets_dir.mkdir(exist_ok=True)

icon_path = assets_dir / "icon.png"
write_png(icon_path, size=1024)
print(f"✅ Generated icon at {icon_path}")

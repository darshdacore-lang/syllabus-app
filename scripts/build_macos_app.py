#!/usr/bin/env python3

import os
import plistlib
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.metadata import APP_NAME, BUNDLE_ID, EXECUTABLE_NAME
from app.ui.app_icon import write_png

BUNDLE_NAME = f"{APP_NAME}.app"
ICON_NAME = "AppIcon.icns"
FALLBACK_ICNS = Path(
    "/System/Library/CoreServices/CoreTypes.bundle/Contents/Resources/Clock.icns"
)

DIST_DIR = ROOT / "dist"
BUNDLE_DIR = DIST_DIR / BUNDLE_NAME
CONTENTS_DIR = BUNDLE_DIR / "Contents"
MACOS_DIR = CONTENTS_DIR / "MacOS"
RESOURCES_DIR = CONTENTS_DIR / "Resources"
APPSRC_DIR = RESOURCES_DIR / "appsrc"


def run(command):
    subprocess.run(
        command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )


def build_icon():
    with tempfile.TemporaryDirectory(prefix="pomodoro-icon-") as temp_dir:
        temp_path = Path(temp_dir)
        iconset_dir = temp_path / "AppIcon.iconset"
        iconset_dir.mkdir()
        write_png(RESOURCES_DIR / "AppIcon.png", size=1024)

        for size in (16, 32, 128, 256, 512):
            for scale in (1, 2):
                pixel_size = size * scale
                suffix = "@2x" if scale == 2 else ""
                output = iconset_dir / f"icon_{size}x{size}{suffix}.png"
                write_png(output, size=pixel_size)

        try:
            run(
                [
                    "iconutil",
                    "-c",
                    "icns",
                    str(iconset_dir),
                    "-o",
                    str(RESOURCES_DIR / ICON_NAME),
                ]
            )
        except subprocess.CalledProcessError:
            shutil.copyfile(FALLBACK_ICNS, RESOURCES_DIR / ICON_NAME)

        shutil.copyfile(RESOURCES_DIR / ICON_NAME, DIST_DIR / ICON_NAME)
        shutil.copyfile(RESOURCES_DIR / "AppIcon.png", DIST_DIR / "AppIcon.png")


def copy_source():
    target_app_dir = APPSRC_DIR / "app"
    shutil.copytree(
        ROOT / "app",
        target_app_dir,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "study_data.json"),
    )


def write_info_plist():
    plist_data = {
        "CFBundleName": APP_NAME,
        "CFBundleDisplayName": APP_NAME,
        "CFBundleExecutable": EXECUTABLE_NAME,
        "CFBundleIdentifier": BUNDLE_ID,
        "CFBundleVersion": "1.0",
        "CFBundleShortVersionString": "1.0",
        "CFBundlePackageType": "APPL",
        "CFBundleIconName": ICON_NAME.replace(".icns", ""),
        "CFBundleIconFile": ICON_NAME,
        "LSMinimumSystemVersion": "12.0",
        "NSHighResolutionCapable": True,
    }
    with (CONTENTS_DIR / "Info.plist").open("wb") as file:
        plistlib.dump(plist_data, file)


def write_launcher():
    launcher = MACOS_DIR / EXECUTABLE_NAME
    script = f"""#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
RESOURCES_DIR="$SCRIPT_DIR/../Resources"
APP_SUPPORT_DIR="$HOME/Library/Application Support/{APP_NAME}"
mkdir -p "$APP_SUPPORT_DIR"

export PYTHONPATH="$RESOURCES_DIR/appsrc${{PYTHONPATH:+:$PYTHONPATH}}"
export SYLLABUS_APP_DATA_PATH="$APP_SUPPORT_DIR/study_data.json"

exec /usr/bin/env python3 -m app
"""
    launcher.write_text(script, encoding="utf-8")
    launcher.chmod(launcher.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def main():
    if BUNDLE_DIR.exists():
        shutil.rmtree(BUNDLE_DIR)

    MACOS_DIR.mkdir(parents=True, exist_ok=True)
    RESOURCES_DIR.mkdir(parents=True, exist_ok=True)
    APPSRC_DIR.mkdir(parents=True, exist_ok=True)

    copy_source()
    build_icon()
    write_info_plist()
    write_launcher()

    print(BUNDLE_DIR)
    print(f"Open it with: open '{BUNDLE_DIR}'")
    print(f"Icon files: {DIST_DIR / ICON_NAME}, {DIST_DIR / 'AppIcon.png'}")


if __name__ == "__main__":
    main()

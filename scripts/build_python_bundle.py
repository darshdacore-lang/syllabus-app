#!/usr/bin/env python3
"""
Build Python bundle using PyInstaller for Electron app.
Creates a standalone Python executable that can be distributed with the app.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def run_command(cmd):
    """Run shell command and handle errors."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(script_dir.parent))
    if result.returncode != 0:
        print(f"Error: Command failed with code {result.returncode}")
        sys.exit(1)

script_dir = Path(__file__).parent
root_dir = script_dir.parent
build_dir = root_dir / "dist" / "python_build"
output_dir = root_dir / "resources" / "python"

print("🔨 Building Python bundle with PyInstaller...")

# Clean previous builds
if build_dir.exists():
    shutil.rmtree(build_dir)
if output_dir.exists():
    shutil.rmtree(output_dir)

build_dir.mkdir(parents=True, exist_ok=True)
output_dir.mkdir(parents=True, exist_ok=True)

# Install PyInstaller if not present
print("📦 Checking PyInstaller...")
run_command([sys.executable, "-m", "pip", "install", "-q", "pyinstaller"])

# Build with PyInstaller
spec_file = script_dir / "build_python_app.spec"

if not spec_file.exists():
    # Create spec file if it doesn't exist
    print("📝 Creating PyInstaller spec file...")
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

block_cipher = None

a = Analysis(
    ['app/api_server.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('app/data/study_data.json', 'app/data'),
    ],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludedimports=['matplotlib', 'numpy', 'scipy', 'pandas'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='python-api-server',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
'''
    spec_file.write_text(spec_content)

# Run PyInstaller
run_command([
    sys.executable, "-m", "PyInstaller",
    "--distpath", str(output_dir.parent),
    "--buildpath", str(build_dir),
    "--specpath", str(script_dir),
    str(spec_file)
])

# Move output to correct location
dist_python = root_dir / "dist" / "python-api-server"
if dist_python.exists():
    # Move to resources/python
    if output_dir.exists():
        shutil.rmtree(output_dir)
    shutil.move(str(dist_python), str(output_dir))

print("✅ Python bundle built successfully!")
print(f"Output: {output_dir}")

# List contents
if output_dir.exists():
    print("\n📁 Contents:")
    for item in output_dir.iterdir():
        print(f"  {item.name}")

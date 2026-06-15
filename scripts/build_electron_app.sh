#!/usr/bin/env zsh
set -euo pipefail

cd "$(cd "$(dirname "$0")" && pwd)/.."

echo "📦 Building Electron app for macOS..."

# Generate icon if it doesn't exist
if [ ! -f "assets/icon.png" ]; then
    echo "🎨 Generating app icon..."
    python3 scripts/generate_icon.py
fi

# Install dependencies
echo "📥 Installing dependencies..."
npm install

# Build the app
echo "🔨 Building the app..."
npm run build

echo "✅ Build complete! Check the dist/ folder for the .dmg and .app files."

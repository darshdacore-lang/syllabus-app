# Pomodoro Syllabus - Electron App Build Guide

## Overview

This is a professional Electron application with an integrated Python backend, configured with `electron-builder` for creating macOS, Windows, and Linux distributions. The app combines:

- **Electron** - Native desktop application framework
- **Python backend** - SessionEngine, TaskManager, and Agent for business logic  
- **HTTP API** - IPC communication between frontend and Python
- **PyInstaller** - Packages Python code for distribution

## Project Structure

```
├── app/
│   ├── main.js                 # Electron main process (spawns Python)
│   ├── preload.js              # Security bridge for IPC
│   ├── index.html              # UI with API integration
│   ├── api_server.py           # Python HTTP API server
│   ├── core/
│   │   ├── session_engine.py   # Focus session management
│   │   └── taskmanager.py      # Task lifecycle management
│   ├── data/
│   │   ├── agent.py            # Command-based interface
│   │   └── storage.py          # JSON data persistence
│   └── utils/
│       └── helpers.py          # Utilities
├── scripts/
│   ├── build_python_bundle.py  # PyInstaller bundler
│   └── build_electron_app.sh   # Build script
├── resources/
│   └── python/                 # PyInstaller output (created on build)
├── package.json                # NPM config with build settings
└── entitlements.mac.plist      # macOS signing config
```

## Prerequisites

- Node.js 16+ and npm
- Python 3.8+ (installed and in PATH)
- macOS 12.0+ (for building macOS apps)
- Xcode Command Line Tools (for code signing)

## Quick Start

### 1. Development Mode

```bash
npm install
npm start
```

This starts:
1. Python HTTP API server on `localhost:5555`
2. Electron app with DevTools open
3. Frontend connects to backend via IPC

### 2. Development with Live Reload

```bash
npm run dev
```

### 3. Build for Production

```bash
npm run build
```

This runs:
1. `build_python_bundle.py` - Packages Python with PyInstaller
2. `electron-builder` - Creates macOS app bundle and DMG

### 4. Build for Multiple Platforms

```bash
npm run build:all
```

## API Reference

The Python backend exposes commands via IPC. Use from the renderer process:

```javascript
// Generic command
const result = await window.api.command('command_name', { arg1: value1 });

// Or use convenience methods:
const active = await window.api.getActive();
await window.api.startFocus('Math', 25);
await window.api.pause();
await window.api.resume();
```

### Available Commands

**Session Management:**
- `getActive()` - Get current focus/break session
- `startFocus(subject, minutes, taskId?, tags?)` - Start a focus session
- `pause()` - Pause active session
- `resume()` - Resume paused session
- `tick()` - Update session (called during active session)
- `getBreakSettings()` - Get break time settings
- `saveBreakSettings(short, long, longAfter)` - Update settings

**Task Management:**
- `addTask(title, subject?, dueDate?, tags?, details?)` - Create task
- `listTasks(includeDone?)` - Get all tasks
- `markDone(taskId)` - Mark task as complete
- `deleteTask(taskId)` - Remove task
- `getSortedTasks()` - Get prioritized task list

**Smart Commands:**
- `suggestNextTask()` - Recommend next task
- `startTaskFocus(taskId, minutes)` - Start focus for a task

**Summary:**
- `dashboardSummary()` - Get overview stats
- `plannerSnapshot()` - Get planner view data

See [app/data/agent.py](app/data/agent.py) for all available commands.

## Build Output

After `npm run build`, find your app in `dist/`:

- **Pomodoro Syllabus-1.0.0-arm64.dmg** - macOS DMG (Apple Silicon)
- **Pomodoro Syllabus-1.0.0-x64.dmg** - macOS DMG (Intel)
- **Pomodoro Syllabus-1.0.0.zip** - macOS ZIP archive
- **Pomodoro Syllabus.app** - The actual app bundle

## Configuration

### App Details

Edit these files to customize your app:

- **package.json** - Version, name, description, build settings
- **app/metadata.py** - App name, bundle ID, executable name
- **entitlements.mac.plist** - macOS permissions/capabilities
- **BUILD_GUIDE.md** (this file) - Build instructions

### API Server Port

The Python API server runs on port `5555` by default. To change:

1. Edit `app/main.js` - Change `const API_PORT = 5555`
2. Edit `app/preload.js` if needed
3. Update any other references

### Python Dependencies

Add Python packages to `requirements.txt`. They'll be included in the PyInstaller bundle.

Current dependencies:
- None (uses only stdlib + app code)

To add a package:
```bash
pip install package_name
pip freeze > requirements.txt
```

## macOS Code Signing

To sign your app for distribution:

### 1. Create a Developer Certificate

```bash
# Get your Team ID
security find-identity -v -p codesigning

# Create provisioning profile at developer.apple.com
```

### 2. Configure Signing

Edit `package.json` build config:

```json
"mac": {
  "certificateFile": "path/to/cert.p12",
  "certificatePassword": "your_password",
  "signingIdentity": "Developer ID Application: Your Name (XXXXXXXXXX)"
}
```

Or set environment variable:

```bash
export CSC_NAME="Developer ID Application: Your Name (XXXXXXXXXX)"
npm run build
```

## Troubleshooting

### Python server fails to start

Check logs:
```bash
# Look for Python errors in console
npm start
```

**Common causes:**
- Port 5555 already in use
- Python not installed or not in PATH
- Missing dependencies in `requirements.txt`

**Solution:**
```bash
# Kill process on port
lsof -i :5555 | grep LISTEN | awk '{print $2}' | xargs kill -9

# Check Python
python3 --version

# Reinstall deps
pip install -r requirements.txt
```

### API calls fail

Ensure `window.api` is accessible:
```javascript
console.log(window.api);  // Should have command methods
```

If undefined, check `preload.js` is loading.

### App won't start in production

Add verbose logging:
```javascript
// In main.js
console.log('Debug:', pythonProcess.stdout, pythonProcess.stderr);
```

### Build fails

Common issues:
- Xcode not installed: `xcode-select --install`
- Node modules stale: `rm -rf node_modules && npm install`
- Python bundle error: `rm -rf dist resources/python && npm run build`

## Development Workflow

1. **Edit Python code** → Changes apply on next `npm start`
2. **Edit UI** → Reload app (Cmd+R)
3. **Add API command** → Add method to `Agent` class in [app/data/agent.py](app/data/agent.py), then expose in `preload.js`
4. **Test before build** → `npm start` thoroughly tests everything
5. **Build** → `npm run build` creates distributable app

## Distribution

### macOS App Store

1. Prepare app for App Store review
2. Create provisioning profile for App Store distribution
3. Build with App Store config in `electron-builder`
4. Submit via Transporter

### Direct Distribution

1. Build DMG: `npm run build:dmg`
2. Sign DMG for Gatekeeper: `codesign --timestamp --options=runtime -s "Developer ID Application" dist/*.dmg`
3. Notarize with Apple: `xcrun altool --notarize-app -f dist/*.dmg ...`
4. Host on your website

## Next Steps

- [ ] Add icon (replace `assets/icon.png`)
- [ ] Customize UI in `app/index.html`
- [ ] Add more Python commands to Agent
- [ ] Set up code signing for production release
- [ ] Create installer branding in `package.json` dmg config

## Support

For Electron docs: https://www.electronjs.org/docs
For PyInstaller docs: https://pyinstaller.org/


1. Update `package.json` build config with your certificate details:

```json
"mac": {
  "certificateFile": "path/to/your/cert.p12",
  "certificatePassword": "your-password"
}
```

2. Rebuild:

```bash
npm run build
```

## App Features

- ✅ Production-ready Electron setup
- ✅ Security best practices (context isolation, preload script)
- ✅ macOS universal builds (Apple Silicon + Intel)
- ✅ Native menu bar integration
- ✅ Hardened runtime enabled
- ✅ Custom app icon
- ✅ Auto-updatable with proper code signing

## Development Notes

- Dev Tools automatically open in dev mode (`--dev` flag)
- Production builds disable Dev Tools
- App menu includes Edit, View, and standard macOS app menu items
- Window can be resized with minimum dimensions of 800x600

## Troubleshooting

### Icon not showing

Run the icon generator:

```bash
python3 scripts/generate_icon.py
```

### Build fails with permission denied

Make the build script executable:

```bash
chmod +x scripts/build_electron_app.sh
```

### Need to clean build

Remove the dist folder and rebuild:

```bash
rm -rf dist && npm run build
```

## Next Steps

1. **Update App Icon** - Replace `assets/icon.png` with your custom icon
2. **Configure Code Signing** - Set up certificate for distribution
3. **Implement Auto-Update** - Use `electron-updater` for automatic updates
4. **Add More Menus** - Customize the app menu in `app/main.js`

For more information, visit:
- [Electron Documentation](https://www.electronjs.org/docs)
- [electron-builder Guide](https://www.electron.build/)

# Pomodoro Syllabus

A professional desktop Pomodoro timer with syllabus/task integration, built with Electron and Python.

## Features

✅ **Pomodoro Timer** - 25 min focus, customizable breaks  
✅ **Task Management** - Create, track, and prioritize tasks  
✅ **Focus Sessions** - Link tasks to focus sessions and track time  
✅ **Persistent Storage** - All data saved to JSON  
✅ **Native Desktop App** - Built with Electron for macOS, Windows, Linux  
✅ **Python Backend** - SessionEngine, TaskManager, and Agent for business logic  

## Quick Start

### Development

```bash
# Install dependencies
npm install

# Start app (spawns Python backend + Electron)
npm start
```

The app will:
1. Start Python HTTP API server on `localhost:5555`
2. Launch Electron with the UI
3. Connect frontend to backend via IPC

### Build for Distribution

```bash
# Build macOS app + DMG
npm run build

# Or build for all platforms
npm run build:all
```

Find your app in `dist/` folder.

## Architecture

```
┌─────────────────────────────┐
│  Electron Renderer (UI)     │
│  - HTML/CSS/JavaScript      │
│  - Window management        │
└──────────┬──────────────────┘
           │ IPC
┌──────────▼──────────────────┐
│  Electron Main Process      │
│  - Spawns Python server     │
│  - Makes HTTP calls         │
└──────────┬──────────────────┘
           │ HTTP
┌──────────▼──────────────────┐
│  Python API Server          │
│  - SessionEngine            │
│  - TaskManager              │
│  - Agent (commands)         │
│  - Storage (JSON)           │
└─────────────────────────────┘
```

## API Usage

From the renderer (frontend), use `window.api`:

```javascript
// Start a focus session
await window.api.startFocus('Math', 25);

// Get current session
const active = await window.api.getActive();

// Pause/resume
await window.api.pause();
await window.api.resume();

// Task management
await window.api.addTask('Study Chapter 5', 'Math');
const tasks = await window.api.listTasks();
await window.api.markDone(taskId);

// Smart commands
const suggested = await window.api.suggestNextTask();
await window.api.startTaskFocus(taskId, 25);
```

See [BUILD_GUIDE.md](BUILD_GUIDE.md) for complete API reference.

## Project Structure

```
syllabus-app/
├── app/
│   ├── main.js              # Electron main (spawns Python)
│   ├── preload.js           # IPC bridge
│   ├── index.html           # UI
│   ├── api_server.py        # Python HTTP API
│   ├── core/
│   │   ├── session_engine.py
│   │   └── taskmanager.py
│   └── data/
│       ├── agent.py
│       └── storage.py
├── scripts/
│   └── build_python_bundle.py
├── package.json
└── BUILD_GUIDE.md
```

## Development

### Adding a New API Command

1. **Add handler to Agent** - [app/data/agent.py](app/data/agent.py)
   ```python
   def _cmd_my_command(self, **kwargs):
       # Implementation
       return result
   ```

2. **Register in _register_commands**
   ```python
   self.commands = {
       # ...
       "my_command": self._cmd_my_command,
   }
   ```

3. **Expose in preload** - [app/preload.js](app/preload.js)
   ```javascript
   myCommand: (...args) =>
       ipcRenderer.invoke("api:command", "my_command", { arg1: val1 })
   ```

4. **Use in UI** - [app/index.html](app/index.html)
   ```javascript
   const result = await window.api.myCommand(val1);
   ```

### Debugging

1. **Frontend** - DevTools open automatically in dev mode (Cmd+Option+I)
2. **Backend** - Python output printed to console
3. **IPC** - Check main process console for API calls

### Testing

```bash
# Run Python unit tests
python3 -m pytest app/tests/
```

## Build for Production

See [BUILD_GUIDE.md](BUILD_GUIDE.md) for:
- macOS code signing
- App Store submission
- Notarization
- Platform-specific builds

## Requirements

- Node.js 16+
- Python 3.8+
- macOS 12+ (for building macOS apps)

## License

MIT

## Next Steps

- [ ] Customize UI theme
- [ ] Add more task features (attachments, due dates)
- [ ] Create analytics/stats dashboard
- [ ] Add notifications/reminders
- [ ] Implement multi-profile support
- [ ] Add export (CSV, PDF)

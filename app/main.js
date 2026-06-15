const { app, BrowserWindow, Menu, ipcMain } = require("electron");
const path = require("path");
const { spawn } = require("child_process");
const http = require("http");
const isDev = process.argv.includes("--dev");

let mainWindow;
let pythonProcess;
const API_PORT = 5555;
const API_URL = `http://localhost:${API_PORT}`;

/**
 * Spawn Python API server
 */
function spawnPythonServer() {
    return new Promise((resolve, reject) => {
        try {
            const pythonScript = path.join(__dirname, "api_server.py");
            let pythonPath = isDev ? "python3" : path.join(process.resourcesPath, "python");

            // If not in dev and the bundled python isn't present, fall back to PYTHON_PATH env or system python3
            if (!isDev) {
                try {
                    const fs = require('fs');
                    if (!fs.existsSync(pythonPath)) {
                        pythonPath = process.env.PYTHON_PATH || 'python3';
                        console.warn(`Bundled python not found; falling back to ${pythonPath}`);
                    }
                } catch (e) {
                    pythonPath = process.env.PYTHON_PATH || 'python3';
                }
            }

            pythonProcess = spawn(pythonPath, [pythonScript, String(API_PORT)], {
                stdio: ["pipe", "pipe", "pipe"],
                detached: false,
            });

            let serverReady = false;

            pythonProcess.stdout.on("data", (data) => {
                const message = data.toString().trim();
                console.log(`[Python] ${message}`);
                if (message === "READY" && !serverReady) {
                    serverReady = true;
                    // Wait a bit for server to fully initialize
                    setTimeout(() => resolve(pythonProcess), 500);
                }
            });

            pythonProcess.stderr.on("data", (data) => {
                console.error(`[Python Error] ${data.toString()}`);
            });

            pythonProcess.on("error", (err) => {
                console.error("Failed to start Python server:", err);
                reject(err);
            });

            pythonProcess.on("exit", (code) => {
                console.log(`Python process exited with code ${code}`);
            });

            // Timeout if server doesn't start in 20 seconds
            setTimeout(() => {
                if (!serverReady) {
                    reject(new Error("Python server startup timeout"));
                }
            }, 20000);

        } catch (err) {
            reject(err);
        }
    });
}

/**
 * Make HTTP request to Python API
 */
function makeAPICall(command, args = {}) {
    return new Promise((resolve, reject) => {
        const payload = JSON.stringify({ command, args });

        const options = {
            hostname: "localhost",
            port: API_PORT,
            path: "/api",
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Content-Length": Buffer.byteLength(payload),
            },
        };

        const req = http.request(options, (res) => {
            let data = "";
            res.on("data", (chunk) => { data += chunk; });
            res.on("end", () => {
                try {
                    const response = JSON.parse(data);
                    if (response.success) {
                        resolve(response.data);
                    } else {
                        reject(new Error(response.error || "API error"));
                    }
                } catch (err) {
                    reject(err);
                }
            });
        });

        req.on("error", reject);
        req.write(payload);
        req.end();
    });
}

/**
 * Setup IPC handlers for renderer process communication
 */
function setupIPC() {
    // Generic command handler
    ipcMain.handle("api:command", async (event, command, args) => {
        console.log(`IPC: ${command}`, args);
        try {
            const result = await makeAPICall(command, args);
            return { success: true, data: result };
        } catch (error) {
            console.error(`IPC Error: ${error.message}`);
            return { success: false, error: error.message };
        }
    });
}

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1200,
        height: 800,
        minWidth: 800,
        minHeight: 600,
        icon: path.join(__dirname, "assets/icon.png"),
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            enableRemoteModule: false,
            preload: path.join(__dirname, "preload.js"),
        },
    });

    const startUrl = isDev ? "http://localhost:3000" : `file://${path.join(__dirname, "index.html")}`;

    async function _loadAppropriate() {
        if (!isDev) {
            mainWindow.loadFile(path.join(__dirname, "index.html"));
            return;
        }

        // In dev, prefer a local dev server at localhost:3000, but fall back to the bundled file
        const devUrl = startUrl;
        const checkTimeout = 1000;

        const canConnect = await new Promise((res) => {
            const req = http.get(devUrl, { timeout: checkTimeout }, (r) => {
                r.resume();
                res(true);
            });
            req.on('error', () => res(false));
            req.on('timeout', () => { req.destroy(); res(false); });
        });

        if (canConnect) {
            mainWindow.loadURL(devUrl);
        } else {
            console.warn(`Dev server not reachable at ${devUrl}, loading local file instead.`);
            mainWindow.loadFile(path.join(__dirname, "index.html"));
        }
    }

    _loadAppropriate();

    if (isDev) {
        mainWindow.webContents.openDevTools();
    }

    mainWindow.on("closed", () => {
        mainWindow = null;
    });
}

// Create application menu
function createMenu() {
    const template = [
        {
            label: "Pomodoro Syllabus",
            submenu: [
                { role: "about" },
                { type: "separator" },
                { role: "quit" },
            ],
        },
        {
            label: "Edit",
            submenu: [
                { role: "undo" },
                { role: "redo" },
                { type: "separator" },
                { role: "cut" },
                { role: "copy" },
                { role: "paste" },
            ],
        },
        {
            label: "View",
            submenu: [
                { role: "reload" },
                { role: "forceReload" },
                { role: "toggleDevTools" },
                { type: "separator" },
                { role: "resetZoom" },
                { role: "zoomIn" },
                { role: "zoomOut" },
                { type: "separator" },
                { role: "togglefullscreen" },
            ],
        },
    ];

    const menu = Menu.buildFromTemplate(template);
    Menu.setApplicationMenu(menu);
}

app.on("ready", async () => {
    console.log("🍅 Electron app starting...");

    try {
        // Start Python API server
        await spawnPythonServer();
        console.log("✅ Python API server ready");

        // Setup IPC communication
        setupIPC();

        // Create window
        createWindow();
        createMenu();
    } catch (error) {
        console.error("Failed to start app:", error);
        app.quit();
    }
});

app.on("window-all-closed", () => {
    if (process.platform !== "darwin") {
        app.quit();
    }
});

app.on("activate", () => {
    if (mainWindow === null) {
        createWindow();
    }
});

app.on("quit", () => {
    // Kill Python process on app exit
    if (pythonProcess) {
        pythonProcess.kill();
    }
});
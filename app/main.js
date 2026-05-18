const { app, BrowserWindow } = require("electron");
const path = require("path");

let mainWindow;

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 900,
        height: 600,
        backgroundColor: "#111",
        show: false,
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true
        }
    });

    const filePath = path.join(__dirname, "index.html");
    console.log("LOADING FILE:", filePath);

    mainWindow.loadFile(filePath)
        .then(() => {
            console.log("LOAD SUCCESS");
        })
        .catch((error) => {
            console.error("LOAD ERROR:", error);
        });

    mainWindow.once("ready-to-show", () => {
        console.log("READY TO SHOW");
        mainWindow.center();
        mainWindow.show();
        mainWindow.focus();
        mainWindow.setVisibleOnAllWorkspaces(true);
        mainWindow.setAlwaysOnTop(true);
        app.focus();
    });

    mainWindow.on("show", () => {
        console.log("WINDOW SHOWN");
    });

    mainWindow.webContents.on("did-finish-load", () => {
        console.log("DID FINISH LOAD");
    });

    mainWindow.webContents.on("dom-ready", () => {
        console.log("DOM READY");
    });

    mainWindow.webContents.openDevTools({ mode: "detach" });

    mainWindow.webContents.on("did-fail-load", (event, errorCode, errorDescription) => {
        console.error("LOAD FAILED:", errorCode, errorDescription);
    });

    mainWindow.webContents.on("render-process-gone", (event, details) => {
        console.error("RENDER CRASH:", details);
    });

    mainWindow.on("closed", () => {
        mainWindow = null;
    });
}

app.whenReady().then(createWindow);

app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
        createWindow();
    }
});

app.on("window-all-closed", () => {
    if (process.platform !== "darwin") app.quit();
});

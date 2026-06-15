const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("electron", {
    nodeVersion: () => process.versions.node,
    chromeVersion: () => process.versions.chrome,
    electronVersion: () => process.versions.electron,
});

/**
 * API Bridge for communicating with Python backend
 * Usage: await window.api.command('start_focus', { subject: 'Math', minutes: 25 })
 */
contextBridge.exposeInMainWorld("api", {
    /**
     * Call a Python backend command via IPC
     * @param {string} command - The command name (e.g., 'start_focus', 'get_active')
     * @param {object} args - Arguments to pass to the command
     * @returns {Promise} Resolves with command result or rejects with error
     */
    command: (command, args = {}) => {
        return ipcRenderer.invoke("api:command", command, args);
    },

    /**
     * Convenience methods for common commands
     */

    // Session management
    getActive: () => ipcRenderer.invoke("api:command", "get_active"),
    startFocus: (subject, minutes, taskId = null, tags = null) =>
        ipcRenderer.invoke("api:command", "start_focus", { subject, minutes, task_id: taskId, tags }),
    pause: () => ipcRenderer.invoke("api:command", "pause"),
    resume: () => ipcRenderer.invoke("api:command", "resume"),
    tick: () => ipcRenderer.invoke("api:command", "tick"),
    getBreakSettings: () => ipcRenderer.invoke("api:command", "get_break_settings"),
    saveBreakSettings: (shortBreak, longBreak, longBreakAfter) =>
        ipcRenderer.invoke("api:command", "save_break_settings", {
            short_break: shortBreak,
            long_break: longBreak,
            long_break_after: longBreakAfter
        }),

    // Task management
    addTask: (title, subject = "General", dueDate = "", tags = null, details = "") =>
        ipcRenderer.invoke("api:command", "add_task", {
            title, subject, due_date: dueDate, tags, details
        }),
    listTasks: (includeDone = false) =>
        ipcRenderer.invoke("api:command", "list_tasks", { include_done: includeDone }),
    markDone: (taskId) =>
        ipcRenderer.invoke("api:command", "mark_done", { task_id: taskId }),
    deleteTask: (taskId) =>
        ipcRenderer.invoke("api:command", "delete_task", { task_id: taskId }),
    getSortedTasks: () =>
        ipcRenderer.invoke("api:command", "get_sorted_tasks"),

    // Smart commands
    suggestNextTask: () =>
        ipcRenderer.invoke("api:command", "suggest_next_task"),
    startTaskFocus: (taskId, minutes) =>
        ipcRenderer.invoke("api:command", "start_task_focus", { task_id: taskId, minutes }),

    // Summary commands
    dashboardSummary: () =>
        ipcRenderer.invoke("api:command", "dashboard_summary"),
    plannerSnapshot: () =>
        ipcRenderer.invoke("api:command", "planner_snapshot"),

    // Utility
    listCommands: () =>
        ipcRenderer.invoke("api:command", "list_commands"),
});


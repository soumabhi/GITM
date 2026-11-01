const { app, BrowserWindow, dialog, ipcMain } = require("electron");
const { spawn, execFileSync } = require("child_process");
const fs = require("fs");
const path = require("path");
const readline = require("readline");

const ROOT = path.resolve(__dirname, "..", "..");
const PYTHON = path.join(ROOT, ".venv", "Scripts", "python.exe");
const PYTHONW = path.join(ROOT, ".venv", "Scripts", "pythonw.exe");
const APP_ICON = path.join(ROOT, "assets", "icons", "app.ico");
const APP_ICON_PNG = path.join(ROOT, "assets", "icons", "app.png");

function resolveIcon() {
  if (fs.existsSync(APP_ICON)) return APP_ICON;
  if (fs.existsSync(APP_ICON_PNG)) return APP_ICON_PNG;
  return undefined;
}

let bridge = null;
let engineStarting = false;
const pending = [];

function call(payload) {
  return new Promise((resolve, reject) => {
    if (!bridge || !bridge.stdin.writable) {
      reject(new Error("bridge down"));
      return;
    }
    pending.push({ resolve, reject });
    bridge.stdin.write(JSON.stringify(payload) + "\n");
  });
}

function childEnv(extra = {}) {
  const env = { ...process.env, ...extra };
  // Agent/IDE shells often set QT_QPA_PLATFORM=offscreen; that hides the ghost.
  if (!env.QT_QPA_PLATFORM || env.QT_QPA_PLATFORM === "offscreen") {
    env.QT_QPA_PLATFORM = process.platform === "win32" ? "windows" : "xcb";
  }
  return env;
}

function startBridge() {
  stopMatching("app\\.studio_bridge");
  bridge = spawn(PYTHON, ["-m", "app.studio_bridge"], {
    cwd: ROOT,
    env: childEnv({ PYTHONIOENCODING: "utf-8" }),
    stdio: ["pipe", "pipe", "pipe"],
    windowsHide: true,
  });
  const lines = readline.createInterface({ input: bridge.stdout });
  lines.on("line", (line) => {
    const waiter = pending.shift();
    if (!waiter) return;
    try {
      waiter.resolve(JSON.parse(line));
    } catch (error) {
      waiter.reject(error);
    }
  });
  bridge.on("exit", () => {
    while (pending.length) pending.shift().reject(new Error("bridge closed"));
  });
}

function stopMatching(pattern) {
  const file = path.join(ROOT, ".tmp", "ghost-stop.ps1");
  const script = [
    "Get-CimInstance Win32_Process |",
    `  Where-Object { $_.CommandLine -and $_.CommandLine -match '${pattern}' } |`,
    "  ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }",
  ].join("\n");
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, script);
  try {
    execFileSync("powershell", ["-NoProfile", "-ExecutionPolicy", "Bypass", "-File", file], { windowsHide: true });
  } catch {
    /* nothing matched */
  }
}

function startEngine() {
  if (engineStarting) return;
  engineStarting = true;
  stopMatching("GIMM\\\\main\\.py");
  stopMatching("GhostInTheMachine\\.exe");
  stopMatching("GITM\\\\main\\.py");
  stopMatching("GITM\\.exe");
  // Give Windows a moment so the old engine releases the keyboard hook and mutex.
  const shellArg = app.isPackaged ? "" : path.resolve(__dirname, "..");
  setTimeout(() => {
    spawn(PYTHONW, [path.join(ROOT, "main.py"), "--engine"], {
      cwd: ROOT,
      env: childEnv({
        GHOST_SHELL: process.execPath,
        GHOST_SHELL_ARG: shellArg,
        GHOST_SHELL_CWD: shellArg || ROOT,
      }),
      detached: true,
      stdio: "ignore",
      windowsHide: true,
    }).unref();
    engineStarting = false;
  }, 800);
}

function createWindow() {
  const icon = resolveIcon();
  const win = new BrowserWindow({
    width: 1100,
    height: 760,
    minWidth: 860,
    minHeight: 560,
    backgroundColor: "#fbfbfa",
    title: "GITM",
    autoHideMenuBar: true,
    ...(icon ? { icon } : {}),
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  win.webContents.on("will-navigate", (event) => event.preventDefault());
  win.loadFile(path.join(__dirname, "..", "dist", "index.html"));
}

function bind() {
  const wrap = (op) => async (_event, body) => {
    try {
      return await call({ op, ...(body || {}) });
    } catch (error) {
      return { error: error instanceof Error ? error.message : "failed" };
    }
  };
  ipcMain.handle("state", wrap("state"));
  ipcMain.handle("projects", wrap("projects"));
  ipcMain.handle("createProject", wrap("createProject"));
  ipcMain.handle("deleteProject", wrap("deleteProject"));
  ipcMain.handle("prompt", wrap("prompt"));
  ipcMain.handle("save", wrap("save"));
  ipcMain.handle("import", wrap("import"));
  ipcMain.handle("gemma", wrap("gemma"));
  ipcMain.handle("models", wrap("models"));
  ipcMain.handle("useModel", wrap("useModel"));
  ipcMain.handle("pull", wrap("pull"));
  ipcMain.handle("deleteModel", wrap("deleteModel"));
  ipcMain.handle("power", wrap("power"));
  ipcMain.handle("look", wrap("look"));
  ipcMain.handle("line", wrap("line"));
  ipcMain.handle("petState", wrap("petState"));
  ipcMain.handle("petImage", wrap("petImage"));
  ipcMain.handle("petCare", wrap("petCare"));
  ipcMain.handle("browse", async () => {
    const result = await dialog.showOpenDialog({
      title: "Sprite sheet",
      filters: [{ name: "PNG", extensions: ["png"] }],
      properties: ["openFile"],
    });
    return result.canceled ? "" : result.filePaths[0] || "";
  });
}

const locked = app.requestSingleInstanceLock();
if (!locked) {
  app.quit();
} else {
  app.on("second-instance", () => {
    const win = BrowserWindow.getAllWindows()[0];
    if (!win) return;
    if (win.isMinimized()) win.restore();
    win.show();
    win.focus();
  });
  app.setName("GITM");
  if (process.platform === "win32") {
    app.setAppUserModelId("com.gitm.desktop");
  }
  app.whenReady().then(() => {
    startBridge();
    startEngine();
    bind();
    createWindow();
  });
  app.on("window-all-closed", () => app.quit());
  app.on("before-quit", () => {
    if (bridge && !bridge.killed) bridge.kill();
  });
}

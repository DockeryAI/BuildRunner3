const { app, BrowserWindow, ipcMain, shell } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const fs = require('fs').promises;

let mainWindow;
let claudeProcess;

// Enable live reload for Electron (disabled for now due to path issues)
// if (process.env.NODE_ENV === 'development') {
//   require('electron-reload')(__dirname, {
//     electron: path.join(__dirname, '..', 'node_modules', '.bin', 'electron'),
//     hardResetMethod: 'exit'
//   });
// }

function createWindow(initialURL) {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    },
    backgroundColor: '#0a0e27',
    icon: path.join(__dirname, 'icon.png')
  });

  // Load the React app - use provided URL or default to home
  const url = initialURL || 'http://localhost:3001';
  mainWindow.loadURL(url);

  mainWindow.webContents.openDevTools();
}

app.whenReady().then(() => {
  // Check for --url argument (e.g., --url=http://localhost:3001/project/foo)
  const urlArg = process.argv.find(arg => arg.startsWith('--url='));
  const initialURL = urlArg ? urlArg.split('=')[1] : null;
  createWindow(initialURL);
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});

// IPC Handlers for system operations
ipcMain.handle('execute-command', async (event, command, cwd) => {
  return new Promise((resolve, reject) => {
    const child = spawn(command, [], {
      shell: true,
      cwd: cwd || process.cwd()
    });

    let output = '';
    let error = '';

    child.stdout.on('data', (data) => {
      output += data.toString();
    });

    child.stderr.on('data', (data) => {
      error += data.toString();
    });

    child.on('close', (code) => {
      resolve({
        output,
        error,
        code
      });
    });

    child.on('error', (err) => {
      reject(err);
    });
  });
});

ipcMain.handle('launch-claude', async (event, projectName, prompt) => {
  try {
    const tempFile = `/tmp/br_claude_${Date.now()}.txt`;
    await fs.writeFile(tempFile, `Project: ${projectName}\n\n${prompt}`);

    if (process.platform === 'darwin') {
      // On macOS, open a new Terminal window with Claude
      const script = `
        tell application "Terminal"
          do script "claude --dangerously-skip-permissions ${tempFile}"
          activate
        end tell
      `;

      claudeProcess = spawn('osascript', ['-e', script]);
      return { success: true, method: 'terminal' };
    } else if (process.platform === 'win32') {
      // On Windows, open a new Command Prompt with Claude
      claudeProcess = spawn('cmd', ['/c', 'start', 'cmd', '/k', 'claude', '--dangerously-skip-permissions', tempFile]);
      return { success: true, method: 'terminal' };
    } else {
      // On Linux, try common terminal emulators
      const terminals = ['gnome-terminal', 'xterm', 'konsole', 'xfce4-terminal'];
      for (const term of terminals) {
        try {
          claudeProcess = spawn(term, ['--', 'claude', '--dangerously-skip-permissions', tempFile]);
          return { success: true, method: 'terminal' };
        } catch (e) {
          continue;
        }
      }
      throw new Error('No supported terminal found');
    }
  } catch (err) {
    return { success: false, error: err.message };
  }
});

ipcMain.handle('open-project-folder', async (event, path) => {
  shell.openPath(path);
});

ipcMain.handle('read-file', async (event, filePath) => {
  try {
    const content = await fs.readFile(filePath, 'utf8');
    return { success: true, content };
  } catch (err) {
    return { success: false, error: err.message };
  }
});

ipcMain.handle('write-file', async (event, filePath, content) => {
  try {
    await fs.writeFile(filePath, content);
    return { success: true };
  } catch (err) {
    return { success: false, error: err.message };
  }
});
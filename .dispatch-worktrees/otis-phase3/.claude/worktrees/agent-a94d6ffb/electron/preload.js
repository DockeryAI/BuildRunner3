const { contextBridge, ipcRenderer } = require('electron');

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld('electronAPI', {
  executeCommand: (command, cwd) => ipcRenderer.invoke('execute-command', command, cwd),
  launchClaude: (projectName, prompt) => ipcRenderer.invoke('launch-claude', projectName, prompt),
  openProjectFolder: (path) => ipcRenderer.invoke('open-project-folder', path),
  readFile: (filePath) => ipcRenderer.invoke('read-file', filePath),
  writeFile: (filePath, content) => ipcRenderer.invoke('write-file', filePath, content),
});
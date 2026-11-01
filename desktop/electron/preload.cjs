const { contextBridge, ipcRenderer, webUtils } = require("electron");

contextBridge.exposeInMainWorld("ghost", {
  state: (body) => ipcRenderer.invoke("state", body),
  projects: () => ipcRenderer.invoke("projects"),
  createProject: (body) => ipcRenderer.invoke("createProject", body),
  deleteProject: (body) => ipcRenderer.invoke("deleteProject", body),
  prompt: (body) => ipcRenderer.invoke("prompt", body),
  save: (body) => ipcRenderer.invoke("save", body),
  importSheet: (body) => ipcRenderer.invoke("import", body),
  tryGemma: (body) => ipcRenderer.invoke("gemma", body),
  models: () => ipcRenderer.invoke("models"),
  useModel: (body) => ipcRenderer.invoke("useModel", body),
  pullModel: (body) => ipcRenderer.invoke("pull", body),
  deleteModel: (body) => ipcRenderer.invoke("deleteModel", body),
  setPower: (body) => ipcRenderer.invoke("power", body),
  setLook: (body) => ipcRenderer.invoke("look", body),
  line: () => ipcRenderer.invoke("line"),
  petState: () => ipcRenderer.invoke("petState"),
  petImage: (body) => ipcRenderer.invoke("petImage", body),
  petCare: (body) => ipcRenderer.invoke("petCare", body),
  browse: () => ipcRenderer.invoke("browse"),
  pathForFile: (file) => webUtils.getPathForFile(file),
});

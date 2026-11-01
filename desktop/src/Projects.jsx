import { useEffect, useState } from "react";

export function Projects({ onOpen }) {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState("");
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");
  const [notes, setNotes] = useState("");
  const [pending, setPending] = useState(null);
  const [settings, setSettings] = useState(false);
  const [powered, setPowered] = useState(true);

  async function refresh() {
    const result = await window.ghost.projects();
    if (result?.error) {
      setStatus(result.error);
      setProjects([]);
    } else {
      setProjects(result.projects || []);
      setPowered(result.enabled !== false);
    }
    setLoading(false);
  }

  useEffect(() => {
    refresh();
  }, []);

  async function create() {
    const result = await window.ghost.createProject({ name, notes });
    if (result?.error || !result?.project) {
      setStatus(result?.error || "Could not create the project");
      return;
    }
    setOpen(false);
    setName("");
    setNotes("");
    onOpen(result.project);
  }

  async function togglePower() {
    const next = !powered;
    setPowered(next);
    const result = await window.ghost.setPower({ enabled: next });
    if (typeof result?.enabled === "boolean") setPowered(result.enabled);
  }

  async function remove() {
    if (!pending) return;
    const result = await window.ghost.deleteProject({ id: pending.id });
    if (result?.error) {
      setStatus(result.error);
      return;
    }
    setPending(null);
    await refresh();
  }

  return (
    <main className="projects">
      <div className="projects-head">
        <h1 className="stage-in" style={stage(0)}>
          {settings ? "Gemma" : "Projects"}
        </h1>
        <div className="head-actions stage-in" style={stage(1)}>
          <button type="button" className={powered ? "quiet" : "primary"} onMouseDown={(event) => event.preventDefault()} onClick={togglePower}>
            {powered ? "Disable" : "Enable"}
          </button>
          <button
            type="button"
            className={settings ? "gear on" : "gear"}
            aria-label="Settings"
            aria-pressed={settings}
            onMouseDown={(event) => event.preventDefault()}
            onClick={() => setSettings((openSettings) => !openSettings)}
          >
            <GearIcon />
          </button>
          <button className="primary" onClick={() => setOpen(true)}>
            New project
          </button>
        </div>
      </div>
      {settings ? <ModelSettings /> : null}
      {!settings && (loading ? (
        <p className="stage-in muted" style={stage(2)}>
          Loading…
        </p>
      ) : projects.length ? (
        <ul className="project-list">
          {projects.map((project, index) => (
            <li key={project.id} className="project-row stage-in" style={stage(index + 2)}>
              <button className="project-open" onClick={() => onOpen(project)}>
                <span className="project-name">{project.name}</span>
                <span className="project-notes">{project.notes}</span>
              </button>
              <button
                type="button"
                className="icon-btn"
                aria-label={`Delete ${project.name}`}
                onClick={() => setPending(project)}
              >
                <TrashIcon />
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <div className="empty stage-in" style={stage(2)}>
          <h2>No projects yet</h2>
          <p>Start a project, then name the ghost and drop a sprite sheet on each computer action.</p>
        </div>
      ))}
      {status ? <p className="muted projects-status">{status}</p> : null}
      {open ? (
        <Dialog title="New project" onClose={() => setOpen(false)}>
          <label className="field">
            <span>Name</span>
            <input type="text" autoFocus value={name} placeholder="Castle" onChange={(event) => setName(event.target.value)} />
          </label>
          <label className="field">
            <span>Notes</span>
            <textarea
              className="notes"
              value={notes}
              placeholder="Optional"
              onChange={(event) => setNotes(event.target.value)}
            />
          </label>
          <div className="dialog-actions">
            <button className="primary" disabled={!name.trim()} onClick={create}>
              Create
            </button>
          </div>
        </Dialog>
      ) : null}
      {pending ? (
        <Dialog title="Delete project" onClose={() => setPending(null)}>
          <p className="dialog-copy">
            Delete {pending.name}? Its place in the list is removed from this computer.
          </p>
          <div className="dialog-actions">
            <button className="quiet" onClick={() => setPending(null)}>
              Cancel
            </button>
            <button className="primary" onClick={remove}>
              Delete project
            </button>
          </div>
        </Dialog>
      ) : null}
    </main>
  );
}

function ModelSettings() {
  const [catalog, setCatalog] = useState({ choices: [], pull: {}, active: "gemma3:1b", enabled: true });
  const [ask, setAsk] = useState(null);
  const [note, setNote] = useState("");

  async function refresh() {
    const result = await window.ghost.models();
    if (result && !result.error) setCatalog(result);
  }

  useEffect(() => {
    refresh();
    const handle = setInterval(refresh, 1000);
    return () => clearInterval(handle);
  }, []);

  async function choose(id) {
    const result = await window.ghost.useModel({ model: id, enabled: catalog.enabled });
    if (result && !result.error) setCatalog(result);
  }

  async function confirm() {
    if (!ask) return;
    const item = ask.item;
    const kind = ask.kind;
    setAsk(null);
    if (kind === "download") {
      setNote("");
      const result = await window.ghost.pullModel({ model: item.id });
      if (result?.error) setNote(result.error);
      refresh();
      return;
    }
    const result = await window.ghost.deleteModel({ model: item.id });
    if (result?.error) setNote(result.error);
    else setCatalog(result);
  }

  const pull = catalog.pull || {};
  return (
    <div className="stack">
      <p className="muted">One model speaks at a time. Download 4B, or keep the smaller 1B. Files stay in this app folder on D:.</p>
      <label className="check">
        <input
          type="checkbox"
          checked={catalog.enabled !== false}
          onChange={(event) => {
            const enabled = event.target.checked;
            setCatalog((current) => ({ ...current, enabled }));
            window.ghost.useModel({ model: catalog.active, enabled });
          }}
        />
        Speak with Gemma
      </label>
      {(catalog.choices || []).map((item) => {
        const active = catalog.active === item.id;
        const pulling = pull.model === item.id && (pull.status === "pulling" || pull.status === "stalled");
        const total = Number(pull.total) || 0;
        const completed = Number(pull.completed) || 0;
        const percent = pulling && total > 0 ? Math.min(100, Math.round((completed * 100) / total)) : 0;
        return (
          <article key={item.id} className={active ? "model on" : "model"}>
            <div className="model-copy">
              <strong>{item.label}</strong>
              <span>{item.size}. {item.note}</span>
              {pulling ? (
                <span className="ready">
                  {percent ? `${percent}% · ${megabytes(completed)} of ${megabytes(total)}` : "Starting the download"}
                </span>
              ) : null}
            </div>
            <div className="model-actions">
              {active && item.ready ? <span className="pill">Active</span> : null}
              {!active && item.ready ? (
                <button type="button" className="quiet" onClick={() => choose(item.id)}>
                  Use this
                </button>
              ) : null}
              {!item.ready && !pulling ? (
                <button type="button" className="primary" onClick={() => setAsk({ kind: "download", item })}>
                  Download
                </button>
              ) : null}
              {item.ready ? (
                <button type="button" className="icon-btn" aria-label={`Delete ${item.label}`} onClick={() => setAsk({ kind: "delete", item })}>
                  <TrashIcon />
                </button>
              ) : null}
            </div>
            {pulling ? (
              <div className="bar" aria-hidden="true">
                <span style={{ width: `${percent || 8}%` }} />
              </div>
            ) : null}
          </article>
        );
      })}
      {note || pull.status === "error" ? <p className="muted">{note || pull.error}</p> : null}
      {ask ? (
        <Dialog title={ask.kind === "download" ? "Download model" : "Delete model"} onClose={() => setAsk(null)}>
          <p className="dialog-copy">
            {ask.kind === "download"
              ? `Download ${ask.item.label}? It is ${ask.item.size} and stays in this app folder on D:.`
              : `Delete ${ask.item.label} from this computer? The file is removed from the app folder.`}
          </p>
          <div className="dialog-actions">
            <button className="quiet" onClick={() => setAsk(null)}>
              Cancel
            </button>
            <button className="primary" onClick={confirm}>
              {ask.kind === "download" ? "Download" : "Delete model"}
            </button>
          </div>
        </Dialog>
      ) : null}
    </div>
  );
}

function megabytes(bytes) {
  const value = Number(bytes) || 0;
  if (value >= 1024 * 1024 * 1024) return `${(value / (1024 * 1024 * 1024)).toFixed(1)} GB`;
  return `${Math.max(1, Math.round(value / (1024 * 1024)))} MB`;
}

function stage(index) {
  return { animationDelay: `${index * 90}ms` };
}

function Dialog({ title, onClose, children }) {
  useEffect(() => {
    const onKey = (event) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  return (
    <div className="shade" onMouseDown={onClose}>
      <div
        className="dialog"
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="dialog-head">
          <h2>{title}</h2>
          <button type="button" className="icon-btn" aria-label="Close" onClick={onClose}>
            <CloseIcon />
          </button>
        </div>
        <div className="dialog-body">{children}</div>
      </div>
    </div>
  );
}

function GearIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

function TrashIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M3 6h18" />
      <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2" />
      <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6" />
      <path d="M10 11v6" />
      <path d="M14 11v6" />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" aria-hidden="true">
      <path d="M6 6l12 12M18 6L6 18" />
    </svg>
  );
}

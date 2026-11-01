import { useEffect, useRef, useState } from "react";
import { Motion } from "./Motion";
import { Projects } from "./Projects";

const EMPTY = {
  actions: [],
  catalog: [],
  gemma: { enabled: true, model: "gemma3:1b", url: "http://127.0.0.1:11434" },
};

export function App() {
  const [project, setProject] = useState(null);
  if (!project) return <Projects onOpen={setProject} />;
  return <Studio project={project} onBack={() => setProject(null)} />;
}

function CopyGlyph() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="9" y="9" width="11" height="11" rx="2" />
      <path d="M5 15V5a1 1 0 0 1 1-1h10" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M5 12.5 9.5 17 19 7" />
    </svg>
  );
}

function SheetIcon() {
  return (
    <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect x="3" y="3" width="18" height="18" rx="2" />
      <path d="M3 16l5-5 4 4 2-2 7 7" />
      <circle cx="8.5" cy="8.5" r="1.25" fill="currentColor" stroke="none" />
    </svg>
  );
}

function BackIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M15 6 9 12l6 6" />
    </svg>
  );
}

function Studio({ project, onBack }) {
  const [data, setData] = useState(EMPTY);
  const [ready, setReady] = useState(false);
  const [selected, setSelected] = useState("");
  const [prompt, setPrompt] = useState("");
  const [copied, setCopied] = useState(false);
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const [promptOpen, setPromptOpen] = useState(false);
  const [look, setLook] = useState({ size: 192, opacity: 100, x: 100, y: 0, ask: false, question: "", say: "", speed: 100 });
  const [looks, setLooks] = useState({});
  const looksRef = useRef({});

  useEffect(() => {
    setReady(false);
    window.ghost.state({ projectId: project.id }).then((next) => {
      if (next?.error) {
        setStatus(next.error);
        return;
      }
      setData(next);
      if (next.look) setLook(next.look);
      if (next.looks) {
        looksRef.current = next.looks;
        setLooks(next.looks);
      }
      setSelected(next.actions?.[0]?.id || "");
      setReady(true);
    });
  }, [project.id]);

  useEffect(() => {
    if (!ready) return;
    const handle = setTimeout(() => {
      window.ghost
        .save({
          projectId: project.id,
          actions: data.actions.map(({ id, name, show }) => ({ id, name, show })),
        })
        .then((result) => {
          if (result?.error) setStatus(result.error);
        });
    }, 400);
    return () => clearTimeout(handle);
  }, [ready, data, project.id]);

  const action = data.actions.find((item) => item.id === selected);

  useEffect(() => {
    if (!action) return;
    const handle = setTimeout(() => {
      window.ghost
        .prompt({
          id: action.id,
          name: action.name,
        })
        .then((result) => setPrompt(result.text || result.error || ""));
    }, 120);
    return () => clearTimeout(handle);
  }, [action]);

  function patchAction(id, patch) {
    setData((current) => ({
      ...current,
      actions: current.actions.map((item) => (item.id === id ? { ...item, ...patch } : item)),
    }));
  }

  async function take(filePath) {
    if (!action || !filePath) return;
    setBusy(true);
    const result = await window.ghost.importSheet({
      id: action.id,
      name: action.name,
      path: filePath,
    });
    setBusy(false);
    if (result.error) {
      setStatus(result.error);
      return;
    }
    patchAction(action.id, { preview: result.preview || "" });
    setStatus("Sheet saved");
  }

  async function onDrop(event) {
    event.preventDefault();
    const file = event.dataTransfer.files?.[0];
    if (!file || !file.name.toLowerCase().endsWith(".png")) {
      setStatus("PNG only");
      return;
    }
    await take(window.ghost.pathForFile(file));
  }

  async function browse() {
    await take(await window.ghost.browse());
  }

  async function copy() {
    await navigator.clipboard.writeText(prompt);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  return (
    <div className="studio">
      <aside className="side">
        <button type="button" className="back" onClick={onBack}>
          <BackIcon />
          Projects
        </button>
        <h1 className="title">{project.name}</h1>
        <div className="side-scroll">
          <p className="kicker">Actions</p>
          {data.actions.map((item) => (
            <button
              key={item.id}
              type="button"
              className={selected === item.id ? "action on" : "action"}
              onClick={() => setSelected(item.id)}
            >
              {item.title}
            </button>
          ))}
        </div>
        {status ? <p className="status">{status}</p> : null}
        <button type="button" className="prompt-link" onClick={() => setPromptOpen(true)}>
          Master prompt
        </button>
      </aside>
      {action ? (
        <ActionPage
          key={action.id}
          projectName={project.name}
          action={action}
          busy={busy}
          look={looks[action.id] || look}
          onLook={(next) => {
            const id = next.id || action.id;
            const merged = { ...(looksRef.current[id] || look), ...next, id };
            looksRef.current = { ...looksRef.current, [id]: merged };
            setLooks(looksRef.current);
            return window.ghost.setLook(merged);
          }}
          onShow={(show) => patchAction(action.id, { show })}
          onDrop={onDrop}
          onBrowse={browse}
          onStatus={setStatus}
        />
      ) : (
        <main className="page" />
      )}
      {promptOpen ? (
        <div className="shade" onMouseDown={() => setPromptOpen(false)}>
          <div className="dialog" role="dialog" aria-modal="true" aria-label="Master prompt" onMouseDown={(event) => event.stopPropagation()}>
            <div className="dialog-head">
              <h2>Master prompt</h2>
              <button type="button" className={copied ? "copy is-copied" : "copy"} onClick={copy}>
                <span className={copied ? "copy-check" : undefined}>{copied ? <CheckIcon /> : <CopyGlyph />}</span>
                <span className={copied ? "copy-label-in" : undefined}>{copied ? "Copied" : "Copy"}</span>
              </button>
            </div>
            <pre className="prompt-body">{prompt}</pre>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function Dialogue({ text }) {
  const [count, setCount] = useState(0);
  const [on, setOn] = useState(true);
  useEffect(() => {
    setCount(0);
    if (!text) return undefined;
    const id = setInterval(() => setCount((current) => (current >= text.length ? current : current + 1)), 32);
    return () => clearInterval(id);
  }, [text]);
  useEffect(() => {
    const id = setInterval(() => setOn((current) => !current), 480);
    return () => clearInterval(id);
  }, []);
  return (
    <div className="say" aria-live="polite">
      <p>
        {text ? text.slice(0, count) : ""}
        {text && count < text.length ? <i className={on ? "caret on" : "caret"} /> : null}
      </p>
    </div>
  );
}

function PetVisits({ speed, busy, onStatus }) {
  const [visits, setVisits] = useState([]);
  const [over, setOver] = useState(-1);

  function refresh() {
    return window.ghost.petState().then((next) => {
      if (next?.error) {
        onStatus?.(next.error);
        return;
      }
      setVisits(next.visits || []);
    });
  }

  useEffect(() => {
    refresh();
  }, []);

  async function put(slot, filePath) {
    if (!filePath) return;
    const result = await window.ghost.petImage({ slot: String(slot), path: filePath });
    if (result?.error) {
      onStatus?.(result.error);
      return;
    }
    setVisits(result.visits || []);
    onStatus?.("Visit sheet saved");
  }

  async function clear(slot) {
    const result = await window.ghost.petImage({ slot: String(slot), remove: true });
    if (result?.error) {
      onStatus?.(result.error);
      return;
    }
    setVisits(result.visits || []);
  }

  async function browse(slot) {
    await put(slot, await window.ghost.browse());
  }

  async function onDrop(slot, event) {
    event.preventDefault();
    setOver(-1);
    const file = event.dataTransfer.files?.[0];
    if (!file || !file.name.toLowerCase().endsWith(".png")) {
      onStatus?.("PNG only");
      return;
    }
    await put(slot, window.ghost.pathForFile(file));
  }

  const slots = visits.length ? visits : [
    { id: "0", title: "Visit 1", preview: null },
    { id: "1", title: "Visit 2", preview: null },
    { id: "2", title: "Visit 3", preview: null },
  ];

  return (
    <div className="pet-visits">
      <p className="pet-visit-help">
        Drop up to 3 PNGs. Triple-click to spawn or dismiss. It cycles those sheets, stays at the spawn spot, sometimes slowly walks near your mouse, then slowly goes home.
      </p>
      <div className="pet-visit-grid">
        {slots.map((slot, index) => {
          const stageClass = ["pet-visit", slot.preview ? "has" : "", busy ? "busy" : "", over === index ? "over" : ""]
            .filter(Boolean)
            .join(" ");
          return (
            <div key={slot.id} className={stageClass}>
              <header>
                <strong>{slot.title}</strong>
                {slot.preview ? (
                  <button type="button" className="pet-visit-clear" onClick={() => clear(slot.id)}>
                    Clear
                  </button>
                ) : null}
              </header>
              <button
                type="button"
                className="pet-visit-hit"
                aria-label={`${slot.title} sprite sheet`}
                onClick={() => browse(slot.id)}
                onDragOver={(event) => {
                  event.preventDefault();
                  setOver(index);
                }}
                onDragLeave={() => setOver(-1)}
                onDrop={(event) => onDrop(slot.id, event)}
              >
                {slot.preview?.src ? <Motion clip={slot.preview} speed={speed || 100} /> : <SheetIcon />}
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ActionPage({ projectName, action, busy, look, onLook, onShow, onDrop, onBrowse, onStatus }) {
  const [over, setOver] = useState(false);
  const [spoken, setSpoken] = useState("");
  const heard = useRef(undefined);
  const isPet = action?.id === "pet";
  useEffect(() => {
    const id = setInterval(() => {
      window.ghost.line().then((row) => {
        if (!row) return;
        if (heard.current === undefined) {
          heard.current = row.at || 0;
          return;
        }
        if (!row.text || row.at === heard.current) return;
        heard.current = row.at;
        setSpoken(row.text);
      }).catch(() => {});
    }, 250);
    return () => clearInterval(id);
  }, []);
  useEffect(() => {
    if (!spoken) return undefined;
    const id = setTimeout(() => setSpoken(""), spoken.length * 32 + 2000);
    return () => clearTimeout(id);
  }, [spoken]);
  if (!action) return <main className="page" />;
  const stageClass = ["stage", action.preview ? "has" : "", busy ? "busy" : "", over ? "over" : ""].filter(Boolean).join(" ");
  return (
    <main className="page">
      <div className="head">
        <div className="crumb">{projectName}&nbsp;&nbsp;/&nbsp;&nbsp;{action.title}</div>
        <label className="check">
          <input type="checkbox" checked={action.show} onChange={(event) => onShow(event.target.checked)} />
          Show
        </label>
      </div>
      {isPet ? (
        <PetVisits speed={look.speed} busy={busy} onStatus={onStatus} />
      ) : (
        <div
          className={stageClass}
          onDragOver={(event) => {
            event.preventDefault();
            setOver(true);
          }}
          onDragLeave={() => setOver(false)}
          onDrop={(event) => {
            setOver(false);
            onDrop(event);
          }}
        >
          {spoken ? <Dialogue text={spoken} /> : null}
          <button type="button" className="stage-hit" aria-label="Sprite sheet" onClick={onBrowse}>
            {action.preview?.src ? <Motion clip={action.preview} speed={look.speed} /> : <SheetIcon />}
          </button>
        </div>
      )}
      <Dials
        look={look}
        actionId={action.id}
        onLook={onLook}
        onAsking={() => setSpoken("")}
      />
    </main>
  );
}

function Dials({ look, actionId, onLook, onAsking }) {
  const [draft, setDraft] = useState(look);
  const draftRef = useRef(draft);
  const flight = useRef(false);
  const queued = useRef(null);
  const questionWait = useRef(0);
  function push(delay, asking) {
    const fire = () => {
      const currentDraft = draftRef.current;
      queued.current = {
        size: currentDraft.size,
        opacity: currentDraft.opacity,
        x: currentDraft.x,
        y: currentDraft.y,
        speed: currentDraft.speed || 100,
        ask: !!currentDraft.ask,
        question: currentDraft.question || "",
        id: actionId,
      };
      if (asking && currentDraft.ask && String(currentDraft.question || "").trim()) onAsking?.();
      if (flight.current) return;
      const run = () => {
        const current = queued.current;
        queued.current = null;
        if (!current) {
          flight.current = false;
          return;
        }
        flight.current = true;
        Promise.resolve(onLook(current)).finally(run);
      };
      run();
    };
    if (delay) {
      window.clearTimeout(questionWait.current);
      questionWait.current = window.setTimeout(fire, delay);
      return;
    }
    fire();
  }
  const placed = actionId !== "move" && actionId !== "idle" && actionId !== "pet" && actionId !== "typing";
  const rows = [
    ["size", "Size", 80, 420],
    ["opacity", "Opacity", 20, 100],
    placed ? ["x", "Across", 0, 100] : null,
    placed ? ["y", "Down", 0, 100] : null,
    ["speed", "Speed", 25, 200],
  ].filter(Boolean);
  return (
    <section className="dials">
      {rows.map(([key, label, min, max]) => (
        <label key={key} className="dial">
          <span>{label}</span>
          <input
            type="range"
            min={min}
            max={max}
            value={draft[key]}
            onChange={(event) => {
              const next = { ...draftRef.current, [key]: Number(event.target.value) };
              draftRef.current = next;
              setDraft(next);
              push(0);
            }}
          />
          <strong>{draft[key]}</strong>
        </label>
      ))}
      <div className="gemma-row">
        <button
          type="button"
          className={draft.ask ? "switch on" : "switch"}
          onClick={() => {
            const next = { ...draftRef.current, ask: !draft.ask };
            draftRef.current = next;
            setDraft(next);
            if (!next.ask) onAsking?.();
            push(0);
          }}
        >
          <i />
          Gemma
        </button>
        {draft.ask ? (
          <input
            className="question"
            value={draft.question || ""}
            placeholder="What should it talk about?"
            aria-label="Question for Gemma"
            onChange={(event) => {
              const next = { ...draftRef.current, question: event.target.value };
              draftRef.current = next;
              setDraft(next);
              push(450, true);
            }}
          />
        ) : null}
      </div>
    </section>
  );
}


import { useEffect, useState } from "react";
import { Motion } from "./Motion";

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

const CARE = [
  ["meal", "Meal"],
  ["snack", "Snack"],
  ["light", "Light"],
  ["play", "Play"],
  ["clean", "Clean"],
  ["medicine", "Medicine"],
  ["scold", "Scold"],
];

function Hearts({ label, value }) {
  return (
    <div className="meter">
      <span>{label}</span>
      <p>
        {[0, 1, 2, 3].map((index) => (
          <i key={index} className={index < value ? "heart on" : "heart"} />
        ))}
      </p>
    </div>
  );
}

function PlaceCard({ slot, over, onOver, onDrop, onAdd, onReplace, onRemove }) {
  const pictures = slot.pictures || [];
  const pick = slot.how === "pick";
  return (
    <article className={["pet-place", pictures.length ? "has" : "", over ? "over" : ""].filter(Boolean).join(" ")}>
      <header>
        <div>
          <strong>{slot.title}</strong>
          <span>{pick ? "Pet picks one" : "Plays in order"}</span>
        </div>
        <small>{slot.hint}</small>
      </header>
      <div
        className="pet-pics"
        onDragOver={(event) => {
          event.preventDefault();
          onOver(true);
        }}
        onDragLeave={() => onOver(false)}
        onDrop={(event) => {
          event.preventDefault();
          onOver(false);
          const file = event.dataTransfer.files?.[0];
          if (!file) return;
          onDrop(window.ghost.pathForFile(file));
        }}
      >
        {pictures.map((picture, index) => (
          <div key={`${slot.id}-${index}`} className="pet-pic">
            <button type="button" className="pet-pic-hit" aria-label={`Replace ${slot.title} ${index + 1}`} onClick={() => onReplace(index)}>
              {picture.src ? <Motion clip={picture} speed={100} maxH={64} maxW={88} /> : <i />}
              <em>{pick ? `Form ${index + 1}` : `Frame ${index + 1}`}</em>
            </button>
            <button type="button" className="pet-pic-x" aria-label={`Remove ${slot.title} ${index + 1}`} onClick={() => onRemove(index)}>
              ×
            </button>
          </div>
        ))}
        <button type="button" className="pet-add" onClick={onAdd}>
          <span>+</span>
          <em>Add PNG</em>
        </button>
      </div>
    </article>
  );
}

export function PetPage({ speed }) {
  const [state, setState] = useState(null);
  const [over, setOver] = useState("");
  const [note, setNote] = useState("");
  const [promptOpen, setPromptOpen] = useState(false);
  const [prompt, setPrompt] = useState("");
  const [copied, setCopied] = useState(false);

  async function refresh() {
    const next = await window.ghost.petState();
    if (next?.error) {
      setNote(next.error);
      return;
    }
    setState(next);
  }

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 1000);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    window.ghost.prompt({ id: "pet", name: "pet" }).then((result) => {
      setPrompt(result?.text || result?.error || "");
    });
  }, []);

  async function copyPrompt() {
    if (!prompt) return;
    await navigator.clipboard.writeText(prompt);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  async function give(action) {
    const result = await window.ghost.petCare({ action });
    if (result?.error) setNote(result.error);
    await refresh();
  }

  async function take(slot, filePath, index) {
    if (!filePath && index === undefined) return;
    const body = { slot };
    if (filePath) body.path = filePath;
    if (index !== undefined) body.index = index;
    const result = await window.ghost.petImage(body);
    if (result?.error) {
      setNote(result.error);
      return;
    }
    setNote("");
    setState(result);
  }

  async function remove(slot, index) {
    const result = await window.ghost.petImage({ slot, index, remove: true });
    if (result?.error) {
      setNote(result.error);
      return;
    }
    setNote("");
    setState(result);
  }

  const slots = state?.slots || [];
  const place = slots.find((slot) => slot.id === state?.place);
  const preview = place?.pictures?.[state?.placeIndex ?? 0] || place?.pictures?.[0];
  const playing = !!state?.game;
  const groups = [];
  for (const slot of slots) {
    const last = groups[groups.length - 1];
    if (!last || last.name !== slot.group) groups.push({ name: slot.group, items: [slot] });
    else last.items.push(slot);
  }

  return (
    <section className="pet-page">
      <div className="stage has pet-live">
        <div className="pet-top">
          <div className="pet-portrait">
            {preview?.src ? <Motion clip={preview} speed={speed || 100} maxH={140} maxW={160} /> : <span className="pet-empty">Add PNGs below</span>}
          </div>
          <div className="pet-facts">
            <p className="pet-blurb">{state?.blurb || "The live pet is on your desktop, not inside this page. Move the mouse near that pet to pull it."}</p>
            <p className="pet-help pet-desk">This window only holds the meters and PNGs. Follow, drag, and care buttons on the character happen on the desktop pet.</p>
            <Hearts label="Hungry" value={state?.hunger ?? 0} />
            <Hearts label="Happy" value={state?.happy ?? 0} />
            <Hearts label="Discipline" value={state?.discipline ?? 0} />
            <dl>
              <div><dt>Stage</dt><dd>{state?.stage || "egg"}</dd></div>
              <div><dt>Age</dt><dd>{state?.age ?? 0}</dd></div>
              <div><dt>Weight</dt><dd>{state?.weight ?? 0}</dd></div>
              <div><dt>Mistakes</dt><dd>{state?.mistakes ?? 0}</dd></div>
              <div><dt>Light</dt><dd>{state?.lights ? "On" : "Off"}</dd></div>
              <div><dt>Mess</dt><dd>{state?.poops ?? 0}</dd></div>
            </dl>
          </div>
        </div>
      </div>
      <div className="pet-care">
        {playing ? (
          <>
            <button type="button" className="quiet" onClick={() => give("left")}>Left</button>
            <button type="button" className="quiet" onClick={() => give("right")}>Right</button>
            <span className="pet-round">Round {state.gameRound} of 5 · {state.gameWins} right</span>
          </>
        ) : (
          CARE.map(([id, label]) => (
            <button key={id} type="button" className={state?.call && ((state.call === "hunger" && id === "meal") || (state.call === "happy" && (id === "snack" || id === "play")) || (state.call === "light" && id === "light") || (state.call === "discipline" && id === "scold")) ? "quiet need" : "quiet"} onClick={() => give(id)}>
              {label}
            </button>
          ))
        )}
        <button type="button" className="quiet" onClick={() => give("reset")}>
          New egg
        </button>
      </div>
      <article className="pet-prompt-place">
        <div>
          <strong>Master prompt</strong>
          <p>Lock the character first. Then say next for each place, one by one.</p>
        </div>
        <button type="button" className="quiet" onClick={() => setPromptOpen(true)}>
          Open
        </button>
      </article>
      {promptOpen ? (
        <div className="shade" onMouseDown={() => setPromptOpen(false)}>
          <div className="dialog" role="dialog" aria-modal="true" aria-label="Pet master prompt" onMouseDown={(event) => event.stopPropagation()}>
            <div className="dialog-head">
              <h2>Master prompt</h2>
              <button type="button" className={copied ? "copy is-copied" : "copy"} onClick={copyPrompt}>
                <span className={copied ? "copy-check" : undefined}>{copied ? <CheckIcon /> : <CopyGlyph />}</span>
                <span className={copied ? "copy-label-in" : undefined}>{copied ? "Copied" : "Copy"}</span>
              </button>
            </div>
            <pre className="prompt-body">{prompt}</pre>
          </div>
        </div>
      ) : null}
      {groups.map((group) => (
        <section key={group.name} className="pet-group">
          <p className="kicker pet-kicker">{group.name}</p>
          <p className="pet-help">
            {group.name === "Who it is"
              ? "Drop as many PNGs as you want on each age. Teen and Adult pick one PNG from care, same as the toy. Egg, Baby, Child, and Death play every PNG in order."
              : "Each moment has its own place. Add more PNGs and they play as the next frames of that moment."}
          </p>
          <div className="pet-places">
            {group.items.map((slot) => (
              <PlaceCard
                key={slot.id}
                slot={slot}
                over={over === slot.id}
                onOver={(on) => setOver(on ? slot.id : "")}
                onDrop={(path) => take(slot.id, path)}
                onAdd={async () => take(slot.id, await window.ghost.browse())}
                onReplace={async (index) => take(slot.id, await window.ghost.browse(), index)}
                onRemove={(index) => remove(slot.id, index)}
              />
            ))}
          </div>
        </section>
      ))}
      {note ? <p className="status">{note}</p> : null}
    </section>
  );
}

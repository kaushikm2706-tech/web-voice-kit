// web-voice-kit demo (UNOFFICIAL, not affiliated with Gnani AI)
//
// Lets you label what you actually meant (amount + day) next to what the speech-to-text returned,
// and download the pairs as eval-set.json. Stored only in this browser. No audio is kept.
// Use your own voice and made-up details only: no real phone numbers, account numbers or names.
import { useEffect, useState } from "react";

export interface EvalRecord {
  id: string;
  createdAt: string;
  lang: string;
  format: string;
  transcript: string;
  expectedAmount: number | null;
  expectedDay: string;
  note: string;
}

const KEY = "wvk-eval-set";

function load(): EvalRecord[] {
  try {
    const raw = localStorage.getItem(KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function save(records: EvalRecord[]) {
  try {
    localStorage.setItem(KEY, JSON.stringify(records));
  } catch {
    /* storage can be blocked; the panel still works for this session */
  }
}

interface Props {
  transcript: string;
  lang: string;
  format: string;
}

export default function EvalCollector({ transcript, lang, format }: Props) {
  const [records, setRecords] = useState<EvalRecord[]>(load);
  const [amount, setAmount] = useState("");
  const [day, setDay] = useState("");
  const [note, setNote] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => save(records), [records]);

  const canAdd = transcript.trim().length > 0;

  const add = () => {
    setFormError(null);
    let expectedAmount: number | null = null;
    if (amount.trim() !== "") {
      const n = Number(amount.replace(/[,₹\s]/g, ""));
      if (!Number.isFinite(n) || n < 0) {
        setFormError("Amount must be a number, like 2500.");
        return;
      }
      expectedAmount = n;
    }
    setRecords((prev) => [
      ...prev,
      {
        id: `${Date.now()}-${prev.length}`,
        createdAt: new Date().toISOString(),
        lang,
        format,
        transcript: transcript.trim(),
        expectedAmount,
        expectedDay: day.trim(),
        note: note.trim(),
      },
    ]);
    setAmount("");
    setDay("");
    setNote("");
  };

  const download = () => {
    const blob = new Blob([JSON.stringify(records, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "eval-set.json";
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  };

  return (
    <section data-testid="eval-panel">
      <h2>Eval set</h2>
      <p className="note">
        After you speak, type what you actually meant and save it. Stored only in this browser, no audio kept. Use
        your own voice and made-up details only.
      </p>
      <p className="muted" data-testid="eval-preview">
        {canAdd ? `Transcript to label: ${transcript}` : "Nothing to label yet. Speak first."}
      </p>
      <div className="row">
        <label>
          Amount I meant (number)
          <input value={amount} onChange={(e) => setAmount(e.target.value)} placeholder="2500" inputMode="numeric" />
        </label>
        <label>
          Day I meant (your words)
          <input value={day} onChange={(e) => setDay(e.target.value)} placeholder="next Friday" />
        </label>
        <label>
          Note (optional)
          <input value={note} onChange={(e) => setNote(e.target.value)} placeholder="quiet room" />
        </label>
      </div>
      {formError && <p className="error">{formError}</p>}
      <div className="row">
        <button onClick={add} disabled={!canAdd} data-testid="eval-add">
          Add to eval set
        </button>
        <button onClick={download} disabled={records.length === 0} data-testid="eval-download">
          Download eval-set.json
        </button>
        <button
          className="stop"
          onClick={() => {
            if (window.confirm("Delete all saved eval items from this browser?")) setRecords([]);
          }}
          disabled={records.length === 0}
        >
          Clear
        </button>
        <span className="pill" data-testid="eval-count">
          {records.length} saved
        </span>
      </div>
    </section>
  );
}

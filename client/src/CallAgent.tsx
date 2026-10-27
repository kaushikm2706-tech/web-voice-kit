// web-voice-kit example (UNOFFICIAL, not affiliated with Gnani AI)
//
// "Payment promise" call: the agent asks how much and on which day, reads it back, and waits for yes / no.
// The caller speaks Tamil-English (Tanglish); the agent speaks English with a Timbre v3.0 voice.
// Demo only: nothing is recorded or paid. Use your own voice and made-up details.
import { useCallback, useEffect, useRef, useState } from "react";
import { useGnaniSTT } from "./useGnaniSTT";
import { useGnaniTTS } from "./useGnaniTTS";
import { runCall, type CallDeps, type ConfirmResult, type Day, type Outcome, type TurnResult } from "./callFlow";

type Phase = "idle" | "agent speaking" | "listening" | "thinking" | "finished";
interface Line {
  who: "agent" | "caller";
  text: string;
}

const LISTEN_TIMEOUT_MS = 20000; // give up on a turn if nothing is heard
const JOIN_WINDOW_MS = 1500; // transcript pieces arriving within this window are one answer

function todayLocal(): string {
  const d = new Date();
  const p = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

async function postJson<T>(url: string, body: unknown): Promise<T> {
  const res = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  if (!res.ok) throw new Error(`The server returned ${res.status} for ${url}.`);
  return (await res.json()) as T;
}

export default function CallAgent() {
  const [phase, setPhase] = useState<Phase>("idle");
  const [lines, setLines] = useState<Line[]>([]);
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  const [error, setError] = useState<string | null>(null);

  const cancelled = useRef(false);
  const pending = useRef<{ parts: string[]; collect?: number; timeout?: number; resolve: (v: string | null) => void } | null>(null);

  const settle = useCallback((value: string | null) => {
    const p = pending.current;
    if (!p) return;
    pending.current = null;
    window.clearTimeout(p.collect);
    window.clearTimeout(p.timeout);
    p.resolve(value);
  }, []);

  const stt = useGnaniSTT({
    lang: "ta-IN",
    format: "transcribe",
    onTranscript: (text) => {
      const p = pending.current;
      if (!p) return;
      p.parts.push(text);
      window.clearTimeout(p.collect);
      p.collect = window.setTimeout(() => settle(p.parts.join(" ")), JOIN_WINDOW_MS);
    },
  });
  const tts = useGnaniTTS();

  // Always call the latest start/stop, never a stale copy from an earlier render.
  const sttRef = useRef(stt);
  sttRef.current = stt;
  const ttsRef = useRef(tts);
  ttsRef.current = tts;

  // If the microphone connection fails while we are waiting, stop waiting.
  useEffect(() => {
    if (stt.status === "error") {
      setError(stt.error);
      settle(null);
    }
  }, [stt.status, stt.error, settle]);

  const listen = useCallback(async (): Promise<string | null> => {
    if (cancelled.current) throw new Error("cancelled");
    setPhase("listening");
    const heard = await new Promise<string | null>((resolve) => {
      const p = { parts: [] as string[], resolve, collect: undefined as number | undefined, timeout: undefined as number | undefined };
      p.timeout = window.setTimeout(() => settle(p.parts.length ? p.parts.join(" ") : null), LISTEN_TIMEOUT_MS);
      pending.current = p;
      void sttRef.current.start();
    });
    sttRef.current.stop(); // microphone off while the agent talks, so it never hears itself
    if (cancelled.current) throw new Error("cancelled");
    setPhase("thinking");
    return heard;
  }, [settle]);

  const say = useCallback(async (text: string) => {
    if (cancelled.current) throw new Error("cancelled");
    setPhase("agent speaking");
    await ttsRef.current.speak(text, { language: "en-IN" });
    if (cancelled.current) throw new Error("cancelled");
  }, []);

  const startCall = useCallback(async () => {
    cancelled.current = false;
    setLines([]);
    setOutcome(null);
    setError(null);
    const deps: CallDeps = {
      say,
      listen,
      log: (who, text) => setLines((prev) => [...prev, { who, text }]),
      turn: (text, known) =>
        postJson<TurnResult>("/agent/turn", { text, amount: known.amount, day: known.day as Day, today: todayLocal() }),
      confirm: (text) => postJson<ConfirmResult>("/agent/confirm", { text }),
    };
    try {
      setOutcome(await runCall(deps));
      setPhase("finished");
    } catch (e) {
      if (!(e instanceof Error && e.message === "cancelled")) setError(e instanceof Error ? e.message : "The call failed.");
      setPhase("idle");
    }
  }, [listen, say]);

  const endCall = useCallback(() => {
    cancelled.current = true;
    settle(null);
    sttRef.current.stop();
    ttsRef.current.stop();
    setPhase("idle");
  }, [settle]);

  useEffect(() => () => {
    cancelled.current = true;
  }, []);

  const inCall = phase !== "idle" && phase !== "finished";

  return (
    <section data-testid="call-agent">
      <h2>Payment-promise call (demo)</h2>
      <p className="note">
        The agent asks how much you will pay and on which day, reads it back, and waits for yes or no. Speak Tamil-English.
        Stop the plain transcript demo above before you start. Nothing is recorded or paid.
      </p>
      <div className="row">
        {inCall ? (
          <button className="stop" onClick={endCall}>
            End call
          </button>
        ) : (
          <button onClick={() => void startCall()}>Start call</button>
        )}
        <span className="pill" data-testid="call-phase">
          {phase}
        </span>
      </div>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {tts.error && <p className="error">{tts.error}</p>}
      {lines.length > 0 && (
        <ul data-testid="call-lines">
          {lines.map((l, i) => (
            <li key={i}>
              <strong>{l.who === "agent" ? "Agent" : "You"}:</strong> {l.text}
            </li>
          ))}
        </ul>
      )}
      {outcome?.status === "confirmed" && (
        <p data-testid="call-result">
          <strong>Confirmed:</strong> {outcome.summary}
        </p>
      )}
      {outcome?.status === "gave_up" && <p data-testid="call-result">Call ended without a confirmed promise: {outcome.reason}</p>}
    </section>
  );
}

// web-voice-kit demo (UNOFFICIAL, not affiliated with Gnani AI)
import { useState } from "react";
import { useGnaniSTT } from "./useGnaniSTT";
import { useGnaniTTS } from "./useGnaniTTS";
import EvalCollector from "./EvalCollector";
import CallAgent from "./CallAgent";

const LANGS: [string, string][] = [
  ["en-IN", "English (India)"],
  ["hi-IN", "Hindi"],
  ["ta-IN", "Tamil"],
  ["te-IN", "Telugu"],
  ["kn-IN", "Kannada"],
  ["ml-IN", "Malayalam"],
  ["mr-IN", "Marathi"],
  ["bn-IN", "Bengali"],
  ["gu-IN", "Gujarati"],
  ["pa-IN", "Punjabi"],
];

export default function App() {
  const [lang, setLang] = useState("en-IN");
  const [format, setFormat] = useState<"verbatim" | "transcribe">("transcribe");
  const stt = useGnaniSTT({ lang, format });
  const tts = useGnaniTTS();
  const live = stt.status === "listening" || stt.status === "connecting";
  const last = stt.segments[stt.segments.length - 1];

  return (
    <main>
      <h1>web-voice-kit demo</h1>
      <p className="note">
        Unofficial community kit, not affiliated with Gnani AI. Your microphone audio goes to your own
        server, which relays it to Gnani. Use your own voice only.
      </p>

      <div className="row">
        <label>
          Language
          <select value={lang} onChange={(e) => setLang(e.target.value)} disabled={live}>
            {LANGS.map(([code, name]) => (
              <option key={code} value={code}>
                {name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Output
          <select value={format} onChange={(e) => setFormat(e.target.value as "verbatim" | "transcribe")} disabled={live}>
            <option value="transcribe">transcribe (numbers, dates, ₹ written out)</option>
            <option value="verbatim">verbatim (words as spoken)</option>
          </select>
        </label>
      </div>

      <div className="row">
        {live ? (
          <button className="stop" onClick={stt.stop}>
            Stop
          </button>
        ) : (
          <button onClick={() => void stt.start()}>Start listening</button>
        )}
        <span className={`pill ${stt.status}`} data-testid="status">
          {stt.status}
        </span>
      </div>

      {stt.error && (
        <p className="error" role="alert" data-testid="error">
          {stt.error}
        </p>
      )}

      <section>
        <h2>Transcript</h2>
        {stt.segments.length === 0 ? (
          <p className="muted">Nothing yet. Press Start listening and speak.</p>
        ) : (
          <ul data-testid="segments">
            {stt.segments.map((s) => (
              <li key={s.id}>
                {s.text}
                {s.latencyMs !== undefined && <small> ({s.latencyMs} ms)</small>}
              </li>
            ))}
          </ul>
        )}
      </section>

      {last && (
        <div className="row">
          <button onClick={() => void tts.speak(last.text, { language: lang })} disabled={tts.speaking}>
            {tts.speaking ? "Speaking…" : "Read the last line back (Timbre v3.0)"}
          </button>
          {tts.speaking && <button onClick={tts.stop}>Stop audio</button>}
        </div>
      )}
      {tts.error && <p className="error">{tts.error}</p>}

      <CallAgent />

      <EvalCollector transcript={stt.segments.map((s) => s.text).join(" ")} lang={lang} format={format} />
    </main>
  );
}

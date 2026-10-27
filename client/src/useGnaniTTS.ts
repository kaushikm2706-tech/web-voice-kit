// web-voice-kit (UNOFFICIAL, not affiliated with Gnani AI)
//
// React hook: text -> your server (/tts) -> Gnani Timbre -> audio played in the browser.
import { useCallback, useEffect, useRef, useState } from "react";

export interface SpeakOptions {
  voice?: string; // default "Shivani" (a timbre-v3.0 voice)
  language?: string; // a Gnani language code, or "auto"
}

export function useGnaniTTS(endpoint = "/tts") {
  const [speaking, setSpeaking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const urlRef = useRef<string | null>(null);
  const doneRef = useRef<(() => void) | null>(null);

  const release = useCallback(() => {
    audioRef.current?.pause();
    audioRef.current = null;
    if (urlRef.current) URL.revokeObjectURL(urlRef.current);
    urlRef.current = null;
    const done = doneRef.current; // wake up whoever is awaiting speak()
    doneRef.current = null;
    done?.();
  }, []);

  const speak = useCallback(
    async (text: string, opts: SpeakOptions = {}) => {
      release();
      setError(null);
      setSpeaking(true);
      const finished = new Promise<void>((resolve) => {
        doneRef.current = resolve;
      });
      try {
        const res = await fetch(endpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text, voice: opts.voice, language: opts.language }),
        });
        if (!res.ok) {
          let detail = `The server returned ${res.status}.`;
          try {
            const j = await res.json();
            if (typeof j?.detail === "string") detail = j.detail;
          } catch {
            /* keep the default message */
          }
          throw new Error(detail);
        }
        const blob = await res.blob();
        const objectUrl = URL.createObjectURL(blob);
        urlRef.current = objectUrl;
        const audio = new Audio(objectUrl);
        audioRef.current = audio;
        audio.onended = () => {
          setSpeaking(false);
          release();
        };
        await audio.play();
      } catch (e) {
        setError(e instanceof Error ? e.message : "Could not play the audio.");
        setSpeaking(false);
        release();
      }
      return finished; // resolves when playback ends, fails, or is stopped
    },
    [endpoint, release],
  );

  const stop = useCallback(() => {
    release();
    setSpeaking(false);
  }, [release]);

  useEffect(() => release, [release]);

  return { speak, stop, speaking, error };
}

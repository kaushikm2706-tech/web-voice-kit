// web-voice-kit (UNOFFICIAL, not affiliated with Gnani AI)
//
// React hook: microphone -> your web-voice-kit server (/stt) -> Gnani realtime STT.
// The API key never reaches the browser. Audio and transcripts are not stored or logged here.
import { useCallback, useEffect, useRef, useState } from "react";

export type STTStatus = "idle" | "connecting" | "listening" | "error";

export interface Segment {
  id: string;
  text: string;
  latencyMs?: number;
}

export interface UseGnaniSTTOptions {
  /** Gnani language code, e.g. "en-IN", "hi-IN", "ta-IN". Default "en-IN". */
  lang?: string;
  /** "transcribe" turns spoken numbers/dates/currency into written form. Default "verbatim". */
  format?: "verbatim" | "transcribe";
  /** WebSocket URL of the relay. Default: same host as the page, path /stt. */
  url?: string;
  /** Where the AudioWorklet file is served from. Default /pcm-worklet.js */
  workletUrl?: string;
}

// If more than ~1 s of audio is waiting in the browser's send buffer, drop frames
// instead of letting the delay grow.
const MAX_BUFFERED_BYTES = 32 * 1024;

function defaultUrl(): string {
  const proto = window.location.protocol === "https:" ? "wss" : "ws";
  return `${proto}://${window.location.host}/stt`;
}

export function useGnaniSTT(options: UseGnaniSTTOptions = {}) {
  const { lang = "en-IN", format = "verbatim", url, workletUrl = "/pcm-worklet.js" } = options;
  const [status, setStatus] = useState<STTStatus>("idle");
  const [segments, setSegments] = useState<Segment[]>([]);
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const ctxRef = useRef<AudioContext | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const nodeRef = useRef<AudioWorkletNode | null>(null);

  const cleanup = useCallback(() => {
    if (nodeRef.current) {
      nodeRef.current.port.onmessage = null;
      nodeRef.current.disconnect();
      nodeRef.current = null;
    }
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    void ctxRef.current?.close().catch(() => {});
    ctxRef.current = null;
    const ws = wsRef.current;
    wsRef.current = null;
    if (ws) {
      ws.onopen = ws.onmessage = ws.onerror = ws.onclose = null;
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) ws.close();
    }
  }, []);

  const fail = useCallback(
    (message: string) => {
      cleanup();
      setError(message);
      setStatus("error");
    },
    [cleanup],
  );

  const start = useCallback(async () => {
    if (wsRef.current || status === "connecting") return;
    setError(null);
    setSegments([]);
    setStatus("connecting");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true },
      });
      streamRef.current = stream;

      const ctx = new AudioContext();
      ctxRef.current = ctx;
      await ctx.resume();
      await ctx.audioWorklet.addModule(workletUrl);
      const source = ctx.createMediaStreamSource(stream);
      const node = new AudioWorkletNode(ctx, "pcm-frames");
      nodeRef.current = node;
      // Muted gain -> speakers, so the node is always pulled by the audio graph but you never hear yourself.
      const mute = ctx.createGain();
      mute.gain.value = 0;
      source.connect(node);
      node.connect(mute);
      mute.connect(ctx.destination);

      const base = url ?? defaultUrl();
      const ws = new WebSocket(`${base}?lang=${encodeURIComponent(lang)}&rate=16000&fmt=${format}`);
      ws.binaryType = "arraybuffer";
      wsRef.current = ws;
      let ready = false;

      // The server accepts the socket only after Gnani is connected, so onopen means "send audio now".
      ws.onopen = () => {
        ready = true;
        setStatus("listening");
      };
      node.port.onmessage = (e: MessageEvent<ArrayBuffer>) => {
        if (ready && ws.readyState === WebSocket.OPEN && ws.bufferedAmount < MAX_BUFFERED_BYTES) {
          ws.send(e.data);
        }
      };
      ws.onmessage = (ev: MessageEvent) => {
        if (typeof ev.data !== "string") return;
        let msg: { type?: string; text?: string; message?: string; segment_id?: string; segment_index?: number; latency?: number };
        try {
          msg = JSON.parse(ev.data);
        } catch {
          return;
        }
        if (msg.type === "transcript" && msg.text) {
          const id = msg.segment_id ?? String(msg.segment_index ?? Date.now());
          setSegments((prev) => [...prev, { id, text: msg.text as string, latencyMs: msg.latency }]);
        } else if (msg.type === "error") {
          fail(msg.message ?? "The server reported an error.");
        }
        // Other message types (connected, processing, ...) are ignored on purpose.
      };
      ws.onerror = () => fail("Could not connect to the server. Is it running?");
      ws.onclose = () => {
        cleanup();
        setStatus((s) => (s === "error" ? "error" : "idle"));
      };
    } catch (e) {
      const name = (e as { name?: string })?.name;
      if (name === "NotAllowedError") fail("Microphone permission was denied.");
      else if (name === "NotFoundError") fail("No microphone found.");
      else fail("Could not start the microphone.");
    }
  }, [cleanup, fail, format, lang, status, url, workletUrl]);

  const stop = useCallback(() => {
    cleanup();
    setStatus("idle");
  }, [cleanup]);

  useEffect(() => cleanup, [cleanup]);

  return { status, segments, error, start, stop };
}

// Unit test for the resampler in public/pcm-worklet.js. Run: node test/worklet.test.cjs
const assert = require("node:assert");
// Load the worklet file as a plain script (the way the browser does), not as an ES module.
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const sandbox = { module: { exports: {} }, Math, Int16Array, Float32Array };
vm.runInNewContext(fs.readFileSync(path.join(__dirname, "../public/pcm-worklet.js"), "utf8"), sandbox);
const { FrameMaker, FRAME_SAMPLES } = sandbox.module.exports;

function goertzel(samples, rate, freq) {
  const k = (2 * Math.PI * freq) / rate;
  let s0 = 0, s1 = 0, s2 = 0;
  const c = 2 * Math.cos(k);
  for (const x of samples) { s0 = x + c * s1 - s2; s2 = s1; s1 = s0; }
  return Math.sqrt(s1 * s1 + s2 * s2 - c * s1 * s2) / samples.length;
}

let failed = 0;
for (const inRate of [16000, 22050, 44100, 48000]) {
  const frames = [];
  const fm = new FrameMaker(inRate, (buf) => frames.push(buf));
  const seconds = 2;
  const total = inRate * seconds;
  // feed in 128-sample blocks, like a real AudioWorklet
  for (let off = 0; off < total; off += 128) {
    const n = Math.min(128, total - off);
    const block = new Float32Array(n);
    for (let i = 0; i < n; i++) block[i] = 0.5 * Math.sin((2 * Math.PI * 440 * (off + i)) / inRate);
    fm.push(block);
  }
  const expectedFrames = Math.floor((16000 * seconds) / FRAME_SAMPLES);
  const all = [];
  let sizesOk = true;
  for (const b of frames) {
    if (b.byteLength !== 1024) sizesOk = false;
    all.push(...new Int16Array(b));
  }
  const norm = all.map((v) => v / 32768);
  const peak = Math.max(...norm.map(Math.abs));
  const at440 = goertzel(norm, 16000, 440);
  const at1000 = goertzel(norm, 16000, 1000);
  const ok =
    sizesOk &&
    Math.abs(frames.length - expectedFrames) <= 1 &&
    peak > 0.45 && peak < 0.55 &&
    at440 > 0.2 && at1000 < 0.01;
  console.log(
    `${ok ? "PASS" : "FAIL"} in=${inRate} Hz  frames=${frames.length} (expect ${expectedFrames})  all 1024 bytes=${sizesOk}  peak=${peak.toFixed(3)}  440Hz amp=${at440.toFixed(3)}  1kHz amp=${at1000.toFixed(4)}`,
  );
  if (!ok) failed++;
}

// clipping must not wrap around
{
  const out = [];
  const fm = new FrameMaker(16000, (b) => out.push(...new Int16Array(b)));
  fm.push(new Float32Array(FRAME_SAMPLES).fill(2.0));
  assert.strictEqual(Math.max(...out), 32767, "clipping high");
  const out2 = [];
  const fm2 = new FrameMaker(16000, (b) => out2.push(...new Int16Array(b)));
  fm2.push(new Float32Array(FRAME_SAMPLES).fill(-2.0));
  assert.strictEqual(Math.min(...out2), -32768, "clipping low");
  console.log("PASS clipping clamps to int16 range");
}
process.exit(failed ? 1 : 0);

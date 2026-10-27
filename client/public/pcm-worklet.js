// web-voice-kit (UNOFFICIAL, not affiliated with Gnani AI)
//
// AudioWorklet that turns microphone audio at ANY sample rate (44.1k, 48k, ...)
// into what Gnani's realtime STT wants: 16 kHz, mono, signed 16-bit little-endian PCM,
// delivered in frames of EXACTLY 1024 bytes (512 samples = 32 ms).
//
// Resampling is a simple "box filter": each output sample is the average of the
// input samples it covers. It is good enough for speech and keeps this file dependency-free.
// Int16Array uses the machine's byte order; every browser platform in practice is little-endian.

const TARGET_RATE = 16000;
const FRAME_SAMPLES = 512; // 512 samples * 2 bytes = 1024 bytes

class FrameMaker {
  constructor(inRate, onFrame) {
    this.ratio = inRate / TARGET_RATE; // input samples per output sample
    this.onFrame = onFrame;
    this.need = this.ratio; // input still needed to finish the current output sample
    this.sum = 0;
    this.frame = new Int16Array(FRAME_SAMPLES);
    this.n = 0;
  }

  push(input) {
    for (let i = 0; i < input.length; i++) {
      const x = input[i];
      let remaining = 1;
      while (remaining > 1e-9) {
        const take = Math.min(this.need, remaining);
        this.sum += x * take;
        this.need -= take;
        remaining -= take;
        if (this.need <= 1e-9) {
          this._emit(this.sum / this.ratio);
          this.sum = 0;
          this.need = this.ratio;
        }
      }
    }
  }

  _emit(v) {
    const c = v > 1 ? 1 : v < -1 ? -1 : v;
    this.frame[this.n++] = c < 0 ? Math.round(c * 32768) : Math.round(c * 32767);
    if (this.n === FRAME_SAMPLES) {
      const buf = this.frame.buffer;
      this.frame = new Int16Array(FRAME_SAMPLES);
      this.n = 0;
      this.onFrame(buf);
    }
  }
}

if (typeof AudioWorkletProcessor !== "undefined") {
  class PcmFrames extends AudioWorkletProcessor {
    constructor() {
      super();
      // `sampleRate` is a global provided inside the AudioWorklet scope.
      this.maker = new FrameMaker(sampleRate, (buf) => this.port.postMessage(buf, [buf]));
    }
    process(inputs) {
      const ch = inputs[0] && inputs[0][0];
      if (ch) this.maker.push(ch);
      return true;
    }
  }
  registerProcessor("pcm-frames", PcmFrames);
}

// Lets Node load this file for unit tests. Inside the browser worklet `module` does not exist.
if (typeof module !== "undefined") module.exports = { FrameMaker, TARGET_RATE, FRAME_SAMPLES };

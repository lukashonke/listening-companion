// AudioWorklet processor — runs in audio rendering thread
// Collects Float32 samples, converts to 16-bit PCM, sends 200ms chunks to main thread
class AudioProcessor extends AudioWorkletProcessor {
  constructor() {
    super()
    // 200ms chunk: sampleRate * 0.2 (sampleRate is a global in AudioWorklet scope)
    this._chunkSamples = Math.round(sampleRate * 0.2)
    this._buffer = []
  }

  process(inputs) {
    const channel = inputs[0]?.[0] // mono channel, Float32Array
    if (!channel) return true

    for (let i = 0; i < channel.length; i++) {
      this._buffer.push(channel[i])
    }

    while (this._buffer.length >= this._chunkSamples) {
      const chunk = this._buffer.splice(0, this._chunkSamples)
      const pcm = new Int16Array(chunk.length)
      for (let i = 0; i < chunk.length; i++) {
        const clamped = Math.max(-1, Math.min(1, chunk[i]))
        pcm[i] = clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff
      }
      this.port.postMessage(pcm.buffer, [pcm.buffer])
    }

    return true
  }
}

registerProcessor('audio-processor', AudioProcessor)

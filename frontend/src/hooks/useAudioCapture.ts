import { useRef, useCallback } from 'react'

interface UseAudioCaptureOptions {
  onAudioChunk: (buffer: ArrayBuffer) => void
  sampleRate?: number
  chunkIntervalMs?: number
}

export function useAudioCapture({ onAudioChunk, sampleRate = 16_000, chunkIntervalMs = 200 }: UseAudioCaptureOptions) {
  const contextRef = useRef<AudioContext | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const workletNodeRef = useRef<AudioWorkletNode | null>(null)
  // keep ref stable
  const onAudioChunkRef = useRef(onAudioChunk)
  onAudioChunkRef.current = onAudioChunk

  const start = useCallback(async () => {
    console.log('[AudioCapture] Requesting mic access...')
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false })
    streamRef.current = stream
    console.log('[AudioCapture] Mic acquired:', stream.getAudioTracks()[0]?.label)

    const context = new AudioContext({ sampleRate })
    contextRef.current = context
    console.log('[AudioCapture] AudioContext created, sampleRate:', context.sampleRate, 'state:', context.state)

    try {
      await context.audioWorklet.addModule('/audio-processor.worklet.js')
      console.log('[AudioCapture] AudioWorklet module loaded successfully')
    } catch (err) {
      console.error('[AudioCapture] Failed to load AudioWorklet module:', err)
      throw err
    }

    const source = context.createMediaStreamSource(stream)
    const workletNode = new AudioWorkletNode(context, 'audio-processor')
    workletNodeRef.current = workletNode

    // Configure chunk interval before audio starts flowing
    workletNode.port.postMessage({ type: 'config', chunkMs: chunkIntervalMs })
    console.log('[AudioCapture] Configured chunk interval:', chunkIntervalMs, 'ms')

    let chunkCount = 0
    workletNode.port.onmessage = (e: MessageEvent<ArrayBuffer>) => {
      chunkCount++
      if (chunkCount <= 3) {
        console.log(`[AudioCapture] Audio chunk #${chunkCount} produced, byteLength:`, e.data.byteLength)
      }
      onAudioChunkRef.current(e.data)
    }

    source.connect(workletNode)

    // Connect to destination through a silent gain node so the AudioWorklet is
    // part of the rendering graph. Without this, the Web Audio API pull model
    // never schedules the worklet's process() and no audio data is produced.
    const silentGain = context.createGain()
    silentGain.gain.value = 0
    workletNode.connect(silentGain)
    silentGain.connect(context.destination)
    console.log('[AudioCapture] Audio graph connected: source → worklet → silentGain(0) → destination')
  }, [sampleRate, chunkIntervalMs])

  const stop = useCallback(() => {
    workletNodeRef.current?.disconnect()
    workletNodeRef.current = null
    streamRef.current?.getTracks().forEach((t) => t.stop())
    streamRef.current = null
    const ctx = contextRef.current
    contextRef.current = null
    ctx?.close()
  }, [])

  return { start, stop }
}

import { useRef, useCallback } from 'react'

interface UseAudioCaptureOptions {
  onAudioChunk: (buffer: ArrayBuffer) => void
  sampleRate?: number
}

export function useAudioCapture({ onAudioChunk, sampleRate = 16_000 }: UseAudioCaptureOptions) {
  const contextRef = useRef<AudioContext | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const workletNodeRef = useRef<AudioWorkletNode | null>(null)
  // keep ref stable
  const onAudioChunkRef = useRef(onAudioChunk)
  onAudioChunkRef.current = onAudioChunk

  const start = useCallback(async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false })
    streamRef.current = stream

    const context = new AudioContext({ sampleRate })
    contextRef.current = context

    await context.audioWorklet.addModule('/audio-processor.worklet.js')

    const source = context.createMediaStreamSource(stream)
    const workletNode = new AudioWorkletNode(context, 'audio-processor')
    workletNodeRef.current = workletNode

    workletNode.port.onmessage = (e: MessageEvent<ArrayBuffer>) => {
      onAudioChunkRef.current(e.data)
    }

    source.connect(workletNode)
    // Do NOT connect to destination — we don't want to hear our own mic
  }, [sampleRate])

  const stop = useCallback(() => {
    workletNodeRef.current?.disconnect()
    workletNodeRef.current = null
    streamRef.current?.getTracks().forEach((t) => t.stop())
    streamRef.current = null
    contextRef.current?.close()
    contextRef.current = null
  }, [])

  return { start, stop }
}

import { useRef, useCallback } from 'react'

export function useTTSPlayer() {
  const contextRef = useRef<AudioContext | null>(null)
  const queueRef = useRef<AudioBuffer[]>([])
  const playingRef = useRef(false)

  function getContext(): AudioContext {
    if (!contextRef.current || contextRef.current.state === 'closed') {
      contextRef.current = new AudioContext()
    }
    return contextRef.current
  }

  const playNext = useCallback(() => {
    if (queueRef.current.length === 0) {
      playingRef.current = false
      return
    }
    playingRef.current = true
    const ctx = getContext()
    const buffer = queueRef.current.shift()!
    const source = ctx.createBufferSource()
    source.buffer = buffer
    source.connect(ctx.destination)
    source.onended = playNext
    source.start()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const enqueue = useCallback(async (audio_b64: string) => {
    try {
      const ctx = getContext()
      const binary = atob(audio_b64)
      const bytes = new Uint8Array(binary.length)
      for (let i = 0; i < binary.length; i++) {
        bytes[i] = binary.charCodeAt(i)
      }
      const audioBuffer = await ctx.decodeAudioData(bytes.buffer)
      queueRef.current.push(audioBuffer)
      if (!playingRef.current) {
        playNext()
      }
    } catch (err) {
      console.error('TTS decode failed:', err)
    }
  }, [playNext])

  return { enqueue }
}

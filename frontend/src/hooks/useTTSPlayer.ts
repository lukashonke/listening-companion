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

  const playNext = useCallback(async () => {
    if (queueRef.current.length === 0) {
      playingRef.current = false
      return
    }
    playingRef.current = true
    const ctx = getContext()
    // Resume AudioContext if suspended (browser autoplay policy)
    if (ctx.state === 'suspended') {
      try {
        await ctx.resume()
      } catch (err) {
        console.error('AudioContext resume failed:', err)
      }
    }
    const buffer = queueRef.current.shift()!
    const source = ctx.createBufferSource()
    source.buffer = buffer
    source.connect(ctx.destination)
    source.onended = () => playNext()
    source.start()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const enqueue = useCallback(async (audio_b64: string) => {
    try {
      const ctx = getContext()
      // Resume AudioContext if suspended (browser autoplay policy)
      if (ctx.state === 'suspended') {
        await ctx.resume()
      }
      const binary = atob(audio_b64)
      const bytes = new Uint8Array(binary.length)
      for (let i = 0; i < binary.length; i++) {
        bytes[i] = binary.charCodeAt(i)
      }
      // Use slice to get a fresh ArrayBuffer (avoids detached buffer issues)
      const audioBuffer = await ctx.decodeAudioData(bytes.buffer.slice(0))
      queueRef.current.push(audioBuffer)
      if (!playingRef.current) {
        playNext()
      }
    } catch (err) {
      console.error('TTS decode/playback failed:', err)
    }
  }, [playNext])

  return { enqueue }
}

import { useState, useEffect, useRef } from 'react'
import { useAppContext } from '@/context/AppContext'
import { Maximize2, Minimize2 } from 'lucide-react'

/**
 * MainTab — "Live Stage" view.
 *
 * Designed to be displayed fullscreen on a large screen during meetings, D&D
 * sessions, lectures, etc. Shows:
 *
 * - The latest generated image as a large hero
 * - A thumbnail strip of previous images along the bottom
 * - A floating speech overlay when the AI speaks (subtitles-style)
 * - An agent-thinking pulse indicator
 */
export function MainTab() {
  const { state } = useAppContext()
  const { images, currentSpeech, isAgentThinking, config } = state

  // Which image is featured — defaults to latest
  const [pinnedIndex, setPinnedIndex] = useState<number | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const [isFullscreen, setIsFullscreen] = useState(false)

  // Auto-advance to latest image unless user has pinned one
  const featuredIdx = pinnedIndex !== null ? pinnedIndex : images.length - 1
  const featured = images.length > 0 ? images[featuredIdx] : null

  // When a new image arrives, unpin so it shows automatically
  useEffect(() => {
    setPinnedIndex(null)
  }, [images.length])

  // Speech fade-out timer
  const [visibleSpeech, setVisibleSpeech] = useState<string | null>(null)
  const [speechFading, setSpeechFading] = useState(false)
  const fadeTimerRef = useRef<ReturnType<typeof setTimeout>>(undefined)

  useEffect(() => {
    if (currentSpeech) {
      setVisibleSpeech(currentSpeech.text)
      setSpeechFading(false)
      // Clear previous timer
      if (fadeTimerRef.current) clearTimeout(fadeTimerRef.current)
      // Start fade-out after 6s (enough to read)
      fadeTimerRef.current = setTimeout(() => {
        setSpeechFading(true)
        // Remove after fade animation (1s)
        setTimeout(() => setVisibleSpeech(null), 1000)
      }, 6000)
    }
    return () => {
      if (fadeTimerRef.current) clearTimeout(fadeTimerRef.current)
    }
  }, [currentSpeech])

  // Fullscreen toggle
  const toggleFullscreen = () => {
    if (!containerRef.current) return
    if (!document.fullscreenElement) {
      containerRef.current.requestFullscreen().then(() => setIsFullscreen(true)).catch(() => {})
    } else {
      document.exitFullscreen().then(() => setIsFullscreen(false)).catch(() => {})
    }
  }

  useEffect(() => {
    const handler = () => setIsFullscreen(!!document.fullscreenElement)
    document.addEventListener('fullscreenchange', handler)
    return () => document.removeEventListener('fullscreenchange', handler)
  }, [])

  return (
    <div
      ref={containerRef}
      className="relative h-full w-full bg-black flex flex-col overflow-hidden select-none"
    >
      {/* ── Hero image area ─────────────────────────────────────── */}
      <div className="flex-1 relative overflow-hidden flex items-center justify-center">
        {featured ? (
          <img
            src={featured.url}
            alt={featured.prompt}
            className="max-h-full max-w-full object-contain transition-all duration-700 ease-in-out"
          />
        ) : (
          <div className="flex flex-col items-center gap-4 text-white/30">
            <div className="text-6xl">🎭</div>
            <p className="text-lg font-light">Waiting for the story to begin…</p>
            {config.theme && (
              <p className="text-sm text-white/20">{config.theme}</p>
            )}
          </div>
        )}

        {/* ── Agent thinking indicator ───────────────────────────── */}
        {isAgentThinking && (
          <div className="absolute top-4 right-4 flex items-center gap-2 bg-black/60 backdrop-blur-sm rounded-full px-4 py-2">
            <div className="flex gap-1">
              <span className="h-2 w-2 rounded-full bg-blue-400 animate-bounce [animation-delay:0ms]" />
              <span className="h-2 w-2 rounded-full bg-blue-400 animate-bounce [animation-delay:150ms]" />
              <span className="h-2 w-2 rounded-full bg-blue-400 animate-bounce [animation-delay:300ms]" />
            </div>
            <span className="text-sm text-white/70">Thinking…</span>
          </div>
        )}

        {/* ── Fullscreen toggle ──────────────────────────────────── */}
        <button
          onClick={toggleFullscreen}
          className="absolute top-4 left-4 p-2 bg-black/40 hover:bg-black/60 backdrop-blur-sm rounded-lg text-white/50 hover:text-white/90 transition-all"
          title={isFullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}
        >
          {isFullscreen ? (
            <Minimize2 className="h-5 w-5" />
          ) : (
            <Maximize2 className="h-5 w-5" />
          )}
        </button>

        {/* ── Speech overlay (subtitles) ─────────────────────────── */}
        {visibleSpeech && (
          <div
            className={`absolute bottom-24 left-1/2 -translate-x-1/2 max-w-[80%] transition-opacity duration-1000 ${
              speechFading ? 'opacity-0' : 'opacity-100'
            }`}
          >
            <div className="bg-black/75 backdrop-blur-md rounded-2xl px-8 py-5 shadow-2xl border border-white/10">
              <p className="text-white text-lg md:text-xl lg:text-2xl leading-relaxed text-center font-light">
                {visibleSpeech}
              </p>
            </div>
          </div>
        )}

        {/* ── Image prompt caption (shown on hover) ──────────────── */}
        {featured && (
          <div className="absolute bottom-4 left-4 right-4 opacity-0 hover:opacity-100 transition-opacity duration-300 pointer-events-none">
            <p className="text-white/50 text-xs text-center truncate px-4">
              {featured.prompt}
            </p>
          </div>
        )}
      </div>

      {/* ── Thumbnail strip ─────────────────────────────────────── */}
      {images.length > 1 && (
        <div className="shrink-0 bg-black/80 border-t border-white/10 px-4 py-2">
          <div className="flex gap-2 overflow-x-auto [scrollbar-width:thin] [scrollbar-color:rgba(255,255,255,0.2)_transparent]">
            {images.map((img, i) => (
              <button
                key={`${img.ts}-${i}`}
                onClick={() => setPinnedIndex(i)}
                className={`shrink-0 rounded-lg overflow-hidden border-2 transition-all duration-200 ${
                  i === featuredIdx
                    ? 'border-white/60 ring-1 ring-white/30 scale-105'
                    : 'border-transparent opacity-60 hover:opacity-100 hover:border-white/30'
                }`}
              >
                <img
                  src={img.url}
                  alt={img.prompt}
                  className="h-16 w-16 md:h-20 md:w-20 object-cover"
                  loading="lazy"
                />
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

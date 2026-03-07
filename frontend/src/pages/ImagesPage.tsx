import { useAppContext } from '@/context/AppContext'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Badge } from '@/components/ui/badge'
import { ImageIcon } from 'lucide-react'
import { formatTime } from '@/lib/formatTime'

export function ImagesPage() {
  const { state } = useAppContext()

  return (
    <div className="h-full flex flex-col">
      <div className="border-b border-border px-6 py-4 flex items-center gap-2 shrink-0">
        <ImageIcon className="h-5 w-5 text-muted-foreground" />
        <h1 className="text-lg font-semibold">Images</h1>
        <Badge variant="secondary" className="ml-auto">
          {state.images.length}
        </Badge>
      </div>

      {state.images.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center gap-3 text-muted-foreground">
          <ImageIcon className="h-10 w-10 opacity-20" />
          <p className="text-sm">No images generated yet</p>
          <p className="text-xs opacity-70">The agent generates images during sessions</p>
        </div>
      ) : (
        <ScrollArea className="flex-1">
          <div className="p-6 grid gap-4 max-w-5xl mx-auto sm:grid-cols-2 lg:grid-cols-3">
            {state.images.map((img, i) => (
              <div
                key={`${img.ts}-${i}`}
                className="group relative rounded-lg overflow-hidden border border-border/70 bg-card aspect-square"
              >
                <img
                  src={img.url}
                  alt={img.prompt}
                  className="w-full h-full object-cover"
                  loading="lazy"
                />
                <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex flex-col justify-end p-3">
                  <p className="text-xs text-white/90 leading-relaxed line-clamp-3">{img.prompt}</p>
                  <p className="text-xs text-white/50 mt-1">{formatTime(img.ts)}</p>
                </div>
              </div>
            ))}
          </div>
        </ScrollArea>
      )}
    </div>
  )
}

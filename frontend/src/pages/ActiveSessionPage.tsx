import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { TranscriptTab } from '@/tabs/TranscriptTab'
import { AgentLogTab } from '@/tabs/AgentLogTab'
import { MemoryTab } from '@/tabs/MemoryTab'
import { useAppContext } from '@/context/AppContext'
import { FileText, Wrench, Brain } from 'lucide-react'

export function ActiveSessionPage() {
  const { state } = useAppContext()

  return (
    <Tabs defaultValue="transcript" className="flex flex-col h-full">
      <div className="border-b border-border px-4 shrink-0">
        <TabsList className="bg-transparent h-10 p-0 gap-1 rounded-none">
          <TabsTrigger
            value="transcript"
            className="gap-1.5 rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:shadow-none h-10"
          >
            <FileText className="h-3.5 w-3.5" />
            Transcript
            {state.transcript.length > 0 && (
              <span className="text-xs text-muted-foreground ml-1">({state.transcript.length})</span>
            )}
          </TabsTrigger>
          <TabsTrigger
            value="agent-log"
            className="gap-1.5 rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:shadow-none h-10"
          >
            <Wrench className="h-3.5 w-3.5" />
            Agent Log
            {state.toolLog.length > 0 && (
              <span className="text-xs text-muted-foreground ml-1">({state.toolLog.length})</span>
            )}
          </TabsTrigger>
          <TabsTrigger
            value="memory"
            className="gap-1.5 rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:shadow-none h-10"
          >
            <Brain className="h-3.5 w-3.5" />
            Memory
            {state.shortTermMemory.length > 0 && (
              <span className="text-xs text-muted-foreground ml-1">({state.shortTermMemory.length})</span>
            )}
          </TabsTrigger>
        </TabsList>
      </div>
      <TabsContent value="transcript" className="flex-1 mt-0 overflow-hidden data-[state=inactive]:hidden">
        <TranscriptTab />
      </TabsContent>
      <TabsContent value="agent-log" className="flex-1 mt-0 overflow-hidden data-[state=inactive]:hidden">
        <AgentLogTab />
      </TabsContent>
      <TabsContent value="memory" className="flex-1 mt-0 overflow-hidden data-[state=inactive]:hidden">
        <MemoryTab />
      </TabsContent>
    </Tabs>
  )
}

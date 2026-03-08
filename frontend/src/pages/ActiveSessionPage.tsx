import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { TranscriptTab } from '@/tabs/TranscriptTab'
import { AgentLogTab } from '@/tabs/AgentLogTab'
import { MemoryTab } from '@/tabs/MemoryTab'
import { LogsTab } from '@/tabs/LogsTab'
import { useAppContext } from '@/context/AppContext'
import { FileText, Wrench, Brain, ImageIcon, ArrowLeft, Terminal } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useNavigate } from 'react-router-dom'
import { SessionImagesTab } from '@/tabs/SessionImagesTab'

export function ActiveSessionPage() {
  const { state } = useAppContext()
  const navigate = useNavigate()

  return (
    <Tabs defaultValue="transcript" className="flex flex-col h-full">
      <div className="border-b border-border px-4 shrink-0 flex items-center gap-2">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => navigate('/sessions')}
          className="gap-1.5 h-10 px-2 text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
          <span className="hidden sm:inline text-xs">Sessions</span>
        </Button>
        <TabsList className="bg-transparent h-10 p-0 gap-1 rounded-none flex-1">
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
          <TabsTrigger
            value="images"
            className="gap-1.5 rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:shadow-none h-10"
          >
            <ImageIcon className="h-3.5 w-3.5" />
            Images
            {state.images.length > 0 && (
              <span className="text-xs text-muted-foreground ml-1">({state.images.length})</span>
            )}
          </TabsTrigger>
          <TabsTrigger
            value="logs"
            className="gap-1.5 rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:shadow-none h-10"
          >
            <Terminal className="h-3.5 w-3.5" />
            Logs
            {state.logs.length > 0 && (
              <span className="text-xs text-muted-foreground ml-1">({state.logs.length})</span>
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
      <TabsContent value="images" className="flex-1 mt-0 overflow-hidden data-[state=inactive]:hidden">
        <SessionImagesTab />
      </TabsContent>
      <TabsContent value="logs" className="flex-1 mt-0 overflow-hidden data-[state=inactive]:hidden">
        <LogsTab />
      </TabsContent>
    </Tabs>
  )
}

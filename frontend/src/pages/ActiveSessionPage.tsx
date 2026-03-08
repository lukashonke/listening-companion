import { useState } from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { TranscriptTab } from '@/tabs/TranscriptTab'
import { AgentLogTab } from '@/tabs/AgentLogTab'
import { MemoryTab } from '@/tabs/MemoryTab'
import { LogsTab } from '@/tabs/LogsTab'
import { useAppContext } from '@/context/AppContext'
import { FileText, Wrench, Brain, ImageIcon, ArrowLeft, Terminal, ChevronDown, ChevronRight, Monitor, PanelRightClose, PanelRightOpen } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useNavigate } from 'react-router-dom'
import { SessionImagesTab } from '@/tabs/SessionImagesTab'
import { MainTab } from '@/tabs/MainTab'
import { SessionMetadataPanel } from '@/components/SessionMetadataPanel'

export function ActiveSessionPage() {
  const { state, dispatchUI } = useAppContext()
  const navigate = useNavigate()
  const [showSessionSettings, setShowSessionSettings] = useState(false)
  const [showMetadataPanel, setShowMetadataPanel] = useState(true)

  return (
    <div className="flex h-full">
      {/* Main content area */}
      <div className="flex-1 min-w-0 flex flex-col">
        <Tabs defaultValue="main" className="flex flex-col h-full">
          {/* Session settings (collapsible) */}
          <div className="border-b border-border px-4 py-2 shrink-0">
            <button
              onClick={() => setShowSessionSettings(v => !v)}
              className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors w-full"
            >
              {showSessionSettings ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
              <span className="font-medium">Session Settings</span>
              {state.sessionName && state.sessionName !== 'New Session' && (
                <span className="text-foreground ml-1">— {state.sessionName}</span>
              )}
            </button>
            {showSessionSettings && (
              <div className="mt-2 space-y-2 max-w-lg">
                <div>
                  <label className="text-xs text-muted-foreground">Session Name</label>
                  <input
                    className="w-full px-2 py-1 rounded-md border bg-background text-sm mt-0.5"
                    value={state.sessionName}
                    onChange={e => dispatchUI({ type: 'SET_SESSION_NAME', payload: e.target.value })}
                    placeholder="Session name"
                  />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground">Theme / Context</label>
                  <input
                    className="w-full px-2 py-1 rounded-md border bg-background text-sm mt-0.5"
                    value={state.config.theme}
                    onChange={e => dispatchUI({ type: 'SET_CONFIG', payload: { theme: e.target.value } })}
                    placeholder="e.g. D&D session, meeting, lecture…"
                  />
                </div>
              </div>
            )}
          </div>

          <div className="border-b border-border px-4 shrink-0 flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigate('/sessions')}
              className="gap-1.5 h-10 px-2 text-muted-foreground hover:text-foreground shrink-0"
            >
              <ArrowLeft className="h-4 w-4" />
              <span className="hidden sm:inline text-xs">Sessions</span>
            </Button>
            <div className="flex-1 overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
              <TabsList className="bg-transparent h-10 p-0 gap-1 rounded-none min-w-max">
                <TabsTrigger
                  value="main"
                  className="gap-1.5 rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:shadow-none h-10 shrink-0"
                >
                  <Monitor className="h-3.5 w-3.5" />
                  Main
                </TabsTrigger>
                <TabsTrigger
                  value="transcript"
                  className="gap-1.5 rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:shadow-none h-10 shrink-0"
                >
                  <FileText className="h-3.5 w-3.5" />
                  Transcript
                  {state.transcript.length > 0 && (
                    <span className="text-xs text-muted-foreground ml-1">({state.transcript.length})</span>
                  )}
                </TabsTrigger>
                <TabsTrigger
                  value="agent-log"
                  className="gap-1.5 rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:shadow-none h-10 shrink-0"
                >
                  <Wrench className="h-3.5 w-3.5" />
                  Agent Log
                  {state.toolLog.length > 0 && (
                    <span className="text-xs text-muted-foreground ml-1">({state.toolLog.length})</span>
                  )}
                </TabsTrigger>
                <TabsTrigger
                  value="memory"
                  className="gap-1.5 rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:shadow-none h-10 shrink-0"
                >
                  <Brain className="h-3.5 w-3.5" />
                  Memory
                  {state.shortTermMemory.length > 0 && (
                    <span className="text-xs text-muted-foreground ml-1">({state.shortTermMemory.length})</span>
                  )}
                </TabsTrigger>
                <TabsTrigger
                  value="images"
                  className="gap-1.5 rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:shadow-none h-10 shrink-0"
                >
                  <ImageIcon className="h-3.5 w-3.5" />
                  Images
                  {state.images.length > 0 && (
                    <span className="text-xs text-muted-foreground ml-1">({state.images.length})</span>
                  )}
                </TabsTrigger>
                <TabsTrigger
                  value="logs"
                  className="gap-1.5 rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:shadow-none h-10 shrink-0"
                >
                  <Terminal className="h-3.5 w-3.5" />
                  Logs
                  {state.logs.length > 0 && (
                    <span className="text-xs text-muted-foreground ml-1">({state.logs.length})</span>
                  )}
                </TabsTrigger>
              </TabsList>
            </div>
            {/* Toggle button for metadata panel - hidden on mobile where panel is always hidden */}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowMetadataPanel(v => !v)}
              className="gap-1.5 h-10 px-2 text-muted-foreground hover:text-foreground shrink-0 hidden md:flex"
              aria-label={showMetadataPanel ? 'Hide metadata panel' : 'Show metadata panel'}
            >
              {showMetadataPanel ? (
                <PanelRightClose className="h-4 w-4" />
              ) : (
                <PanelRightOpen className="h-4 w-4" />
              )}
            </Button>
          </div>
          <TabsContent value="main" className="flex-1 mt-0 overflow-hidden data-[state=inactive]:hidden">
            <MainTab />
          </TabsContent>
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
      </div>

      {/* Right metadata panel - hidden on mobile, toggleable on desktop */}
      {showMetadataPanel && (
        <aside
          className="hidden md:flex w-72 lg:w-80 border-l border-border shrink-0 bg-card/50"
          data-testid="metadata-panel-aside"
        >
          <SessionMetadataPanel />
        </aside>
      )}
    </div>
  )
}

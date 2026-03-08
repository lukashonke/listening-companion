import { createContext, useContext, useReducer, useCallback, useRef, useEffect, type ReactNode } from 'react'
import { appReducer, uiReducer, initialState, DEFAULT_CONFIG } from '@/store/reducer'
import type { AppState, WSEvent } from '@/store/types'
import type { UIAction } from '@/store/reducer'

const LS_KEY = 'lc_config'

function loadInitialState(): AppState {
  try {
    const saved = localStorage.getItem(LS_KEY)
    if (saved) {
      const parsed = JSON.parse(saved)
      return { ...initialState, config: { ...DEFAULT_CONFIG, ...parsed } }
    }
  } catch {}
  return initialState
}

interface AppContextValue {
  state: AppState
  dispatchWS: (event: WSEvent) => void
  dispatchUI: (action: UIAction) => void
  sendJSON: (data: object) => void
  /** Called by AppLayout after useWebSocket initialises to register the real sender */
  registerSendJSON: (fn: (data: object) => void) => void
}

const AppContext = createContext<AppContextValue | null>(null)

type AnyAction = WSEvent | UIAction

const UI_ACTION_TYPES: ReadonlySet<string> = new Set<UIAction['type']>([
  'SET_RECORDING',
  'SET_SESSION_NAME',
  'CLEAR_ERROR',
  'CLEAR_LOGS',
  'RESET_SESSION',
  'SET_CONFIG',
  'SET_RESUME_SESSION_ID',
  'SET_IMAGES',
])

function combinedReducer(state: AppState, action: AnyAction): AppState {
  if (UI_ACTION_TYPES.has(action.type)) {
    return uiReducer(state, action as UIAction)
  }
  return appReducer(state, action as WSEvent)
}

export function AppProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(combinedReducer, undefined, loadInitialState)
  const sendJSONRef = useRef<(data: object) => void>(() => {
    console.warn('sendJSON called before WebSocket initialised')
  })

  const dispatchWS = useCallback((event: WSEvent) => dispatch(event), [])
  const dispatchUI = useCallback((action: UIAction) => dispatch(action), [])
  const sendJSON = useCallback((data: object) => sendJSONRef.current(data), [])
  const registerSendJSON = useCallback((fn: (data: object) => void) => {
    sendJSONRef.current = fn
  }, [])

  useEffect(() => {
    try {
      localStorage.setItem(LS_KEY, JSON.stringify(state.config))
    } catch {}
  }, [state.config])

  return (
    <AppContext.Provider value={{ state, dispatchWS, dispatchUI, sendJSON, registerSendJSON }}>
      {children}
    </AppContext.Provider>
  )
}

export function useAppContext() {
  const ctx = useContext(AppContext)
  if (!ctx) throw new Error('useAppContext must be used within AppProvider')
  return ctx
}

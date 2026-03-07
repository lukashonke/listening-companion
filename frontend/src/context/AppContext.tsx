import { createContext, useContext, useReducer, useCallback, type ReactNode } from 'react'
import { appReducer, uiReducer, initialState } from '@/store/reducer'
import type { AppState, WSEvent } from '@/store/types'
import type { UIAction } from '@/store/reducer'

interface AppContextValue {
  state: AppState
  dispatchWS: (event: WSEvent) => void
  dispatchUI: (action: UIAction) => void
}

const AppContext = createContext<AppContextValue | null>(null)

type AnyAction = WSEvent | UIAction

const UI_ACTION_TYPES: ReadonlySet<string> = new Set<UIAction['type']>([
  'SET_RECORDING',
  'SET_SESSION_NAME',
  'CLEAR_ERROR',
  'RESET_SESSION',
  'SET_CONFIG',
])

function combinedReducer(state: AppState, action: AnyAction): AppState {
  if (UI_ACTION_TYPES.has(action.type)) {
    return uiReducer(state, action as UIAction)
  }
  return appReducer(state, action as WSEvent)
}

export function AppProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(combinedReducer, initialState)

  const dispatchWS = useCallback((event: WSEvent) => dispatch(event), [])
  const dispatchUI = useCallback((action: UIAction) => dispatch(action), [])

  return (
    <AppContext.Provider value={{ state, dispatchWS, dispatchUI }}>
      {children}
    </AppContext.Provider>
  )
}

export function useAppContext() {
  const ctx = useContext(AppContext)
  if (!ctx) throw new Error('useAppContext must be used within AppProvider')
  return ctx
}

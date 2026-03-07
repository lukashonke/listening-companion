const STORAGE_KEY = 'app_password'

export function getPassword(): string {
  return localStorage.getItem(STORAGE_KEY) ?? ''
}

export function setPassword(password: string): void {
  if (password) {
    localStorage.setItem(STORAGE_KEY, password)
  } else {
    localStorage.removeItem(STORAGE_KEY)
  }
}

export function getAuthHeaders(): HeadersInit {
  const pw = getPassword()
  return pw ? { Authorization: `Bearer ${pw}` } : {}
}

export function apiFetch(input: string, init: RequestInit = {}): Promise<Response> {
  return fetch(input, {
    ...init,
    headers: { ...getAuthHeaders(), ...(init.headers ?? {}) },
  })
}

export function getWsUrl(base: string): string {
  const pw = getPassword()
  return pw ? `${base}?token=${encodeURIComponent(pw)}` : base
}

export class ApiError extends Error {
  code: string
  status: number
  details: unknown

  constructor(code: string, message: string, status: number, details?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.status = status
    this.details = details
  }
}

export interface ApiClient {
  get<T = unknown>(path: string): Promise<T>
  post<T = unknown>(path: string, payload?: unknown): Promise<T>
  patch<T = unknown>(path: string, payload?: unknown): Promise<T>
}

export const API_PATH_PREFIX = '/api/'

type Fetcher = (input: string, init?: RequestInit) => Promise<Response>

export function createApiClient(options: {
  baseUrl?: string
  tokenProvider?: () => string | null | undefined
  fetcher?: Fetcher
  onUnauthorized?: (error: ApiError) => void
} = {}): ApiClient {
  const baseUrl = options.baseUrl ?? import.meta.env.VITE_API_BASE_URL ?? ''
  const fetcher = options.fetcher ?? fetch
  const tokenProvider = options.tokenProvider ?? readStoredToken
  const onUnauthorized = options.onUnauthorized ?? notifyUnauthorized

  async function request<T>(method: string, path: string, payload?: unknown): Promise<T> {
    const headers: Record<string, string> = { Accept: 'application/json' }
    const token = tokenProvider()
    if (token) headers.Authorization = `Bearer ${token}`
    let body: string | undefined
    if (payload !== undefined) {
      headers['Content-Type'] = 'application/json'
      body = JSON.stringify(payload)
    }
    const response = await fetcher(`${baseUrl}${path}`, { method, headers, body })
    const contentType = response.headers.get('content-type') ?? ''
    const data = contentType.includes('application/json') ? await response.json() : await readResponseBody(response)
    if (!response.ok) {
      const error = typeof data === 'object' && data !== null && 'error' in data ? (data as any).error : {}
      const apiError = new ApiError(error.code ?? 'api_error', error.message ?? response.statusText, response.status, error.details)
      if (response.status === 401) onUnauthorized(apiError)
      throw apiError
    }
    return data as T
  }

  return {
    get: (path) => request('GET', path),
    post: (path, payload) => request('POST', path, payload),
    patch: (path, payload) => request('PATCH', path, payload)
  }
}

export const apiClient = createApiClient()

function readStoredToken() {
  if (typeof localStorage === 'undefined') return null
  return localStorage.getItem('opportunity_crawler_token')
}

async function readResponseBody(response: Response) {
  const text = await response.text()
  if (!text) return null
  try {
    return JSON.parse(text)
  } catch {
    return text
  }
}

function notifyUnauthorized(error: ApiError) {
  if (typeof window === 'undefined') return
  window.dispatchEvent(new CustomEvent('opportunity-crawler:auth-expired', { detail: error }))
}

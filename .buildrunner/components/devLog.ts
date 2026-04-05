/**
 * BR3 Edge Function Debug Logger
 * Captures console output during function execution and injects it
 * into the JSON response as `_debug` array. Client-side supabaseLogger
 * extracts these and writes them to .buildrunner/supabase.log.
 *
 * Controlled by DEBUG=true env var. Zero overhead when off.
 *
 * Usage:
 *   import { withDevLogs } from '../_shared/devLog.ts'
 *   serve(withDevLogs(async (req) => { ... }))
 */

let _logs: string[] = []

/** Log to console AND capture for _debug response. Drop-in console.log replacement. */
export function devLog(...args: unknown[]): void {
  const msg = args.map(a =>
    typeof a === 'string' ? a : JSON.stringify(a, null, 0)
  ).join(' ')
  const line = `[${new Date().toISOString()}] ${msg}`
  console.log(line)
  _logs.push(line)
}

/**
 * Wraps a serve handler to inject _debug logs into JSON responses.
 * Only active when DEBUG=true env var is set.
 */
export function withDevLogs(
  handler: (req: Request) => Promise<Response> | Response
): (req: Request) => Promise<Response> {
  return async (req: Request) => {
    const debug = Deno.env.get('DEBUG') === 'true'
    if (!debug) return await handler(req)

    _logs = []
    const response = await handler(req)

    // Only inject into JSON responses (skip OPTIONS preflight, streams, etc.)
    const ct = response.headers.get('content-type') || ''
    if (!ct.includes('application/json')) return response

    try {
      const text = await response.text()
      const body = JSON.parse(text)
      body._debug = _logs
      const headers = new Headers(response.headers)
      return new Response(JSON.stringify(body), {
        status: response.status,
        headers,
      })
    } catch {
      // If body isn't parseable JSON, return as-is
      return response
    }
  }
}

export type DevLogEntry = {
  at: string;
  event: string;
  detail?: unknown;
};

type DebugContext = {
  _debug: DevLogEntry[];
  devLog: (event: string, detail?: unknown) => void;
};

type EdgeHandler<TContext extends object> = (
  request: Request,
  context: TContext & DebugContext,
) => Promise<Response>;

export function withDevLogs<TContext extends object>(
  handler: EdgeHandler<TContext>,
) {
  return async (request: Request, context: TContext): Promise<Response> => {
    const _debug: DevLogEntry[] = [];
    const devLog = (event: string, detail?: unknown) => {
      _debug.push({
        at: new Date().toISOString(),
        event,
        detail,
      });
    };

    try {
      const response = await handler(request, {
        ...context,
        _debug,
        devLog,
      });
      return await appendDebugPayload(request, response, _debug);
    } catch (error) {
      devLog("handler_error", {
        message: error instanceof Error ? error.message : String(error),
      });
      return Response.json({ error: "Function failed", _debug }, { status: 500 });
    }
  };
}

async function appendDebugPayload(
  request: Request,
  response: Response,
  _debug: DevLogEntry[],
): Promise<Response> {
  const url = new URL(request.url);
  const wantsDebug =
    request.headers.get("x-br-debug") === "1" || url.searchParams.has("debug");
  if (!wantsDebug || _debug.length == 0) {
    return response;
  }

  try {
    const payload = await response.clone().json();
    if (payload && typeof payload === "object" && !Array.isArray(payload)) {
      return Response.json(
        {
          ...payload,
          _debug,
        },
        {
          status: response.status,
          headers: response.headers,
        },
      );
    }
  } catch {
    // Non-JSON response; fall through to a lightweight header hint.
  }

  const headers = new Headers(response.headers);
  headers.set("x-br-debug-count", String(_debug.length));

  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers,
  });
}

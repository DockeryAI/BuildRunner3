export interface LogPayload {
  logs: Array<Record<string, unknown>>;
}

export async function postLogBatch(
  payload: LogPayload,
  endpoint = '/api/br-log'
): Promise<void> {
  await fetch(endpoint, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
    keepalive: true,
  });
}

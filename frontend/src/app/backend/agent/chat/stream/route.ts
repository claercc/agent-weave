export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const BACKEND_BASE_URL = (
  process.env.BACKEND_BASE_URL ?? "http://127.0.0.1:8000"
).replace(/\/$/, "");
const AGENT_STREAM_URL = `${BACKEND_BASE_URL}/api/agent/chat/stream`;

export async function POST(request: Request): Promise<Response> {
  const requestBody = await request.text();

  try {
    const upstreamResponse = await fetch(AGENT_STREAM_URL, {
      method: "POST",
      headers: {
        Accept: "text/event-stream",
        "Content-Type": "application/json",
      },
      body: requestBody,
      cache: "no-store",
      signal: request.signal,
    });

    if (!upstreamResponse.body) {
      return Response.json(
        {
          detail: "FastAPI 没有返回可读取的 SSE 响应流。",
        },
        {
          status: 502,
        },
      );
    }

    return new Response(upstreamResponse.body, {
      status: upstreamResponse.status,
      headers: {
        "Content-Type": "text/event-stream; charset=utf-8",
        "Cache-Control": "no-cache, no-store, no-transform",
        "Content-Encoding": "identity",
        "X-Accel-Buffering": "no",
      },
    });
  } catch (error) {
    const message =
      error instanceof Error
        ? error.message
        : "无法连接 FastAPI Agent 服务。";

    return Response.json(
      {
        detail: message,
      },
      {
        status: 502,
      },
    );
  }
}

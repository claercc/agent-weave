export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const AGENT_RESUME_STREAM_URL =
  "http://127.0.0.1:8000/api/agent/chat/resume/stream";

/**
 * 将浏览器提交的审批结果转发给 FastAPI，
 * 并把恢复后的 SSE 响应体直接返回给浏览器。
 */
export async function POST(request: Request): Promise<Response> {
  const requestBody = await request.text();

  const upstreamResponse = await fetch(AGENT_RESUME_STREAM_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body: requestBody,
    cache: "no-store",
    signal: request.signal,
  });

  if (!upstreamResponse.ok) {
    const errorBody = await upstreamResponse.text();

    return new Response(errorBody, {
      status: upstreamResponse.status,
      headers: {
        "Content-Type":
          upstreamResponse.headers.get("Content-Type") ??
          "application/json; charset=utf-8",
      },
    });
  }

  if (!upstreamResponse.body) {
    return Response.json(
      {
        detail: "FastAPI 没有返回恢复执行的流式响应体",
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
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
      "Content-Encoding": "identity",
      "X-Accel-Buffering": "no",
    },
  });
}
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";

function unauthorized(message = "Authentication required"): Response {
  return new Response(message, {
    status: 401,
    headers: {
      "Cache-Control": "no-store",
      "WWW-Authenticate": 'Basic realm="AgentWeave Demo", charset="UTF-8"',
    },
  });
}

export function proxy(request: NextRequest): Response {
  const expectedUsername = process.env.DEMO_USERNAME;
  const expectedPassword = process.env.DEMO_PASSWORD;

  if (!expectedUsername || !expectedPassword) {
    return new Response("Demo access credentials are not configured", {
      status: 503,
      headers: {
        "Cache-Control": "no-store",
      },
    });
  }

  const authorization = request.headers.get("authorization");

  if (!authorization?.startsWith("Basic ")) {
    return unauthorized();
  }

  try {
    const credentials = atob(authorization.slice("Basic ".length));
    const separatorIndex = credentials.indexOf(":");

    if (separatorIndex < 0) {
      return unauthorized();
    }

    const username = credentials.slice(0, separatorIndex);
    const password = credentials.slice(separatorIndex + 1);

    if (
      username !== expectedUsername ||
      password !== expectedPassword
    ) {
      return unauthorized("Invalid username or password");
    }
  } catch {
    return unauthorized();
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|robots.txt|sitemap.xml).*)",
  ],
};

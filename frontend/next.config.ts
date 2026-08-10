import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    const backendBaseUrl = (
      process.env.BACKEND_BASE_URL ?? "http://127.0.0.1:8000"
    ).replace(/\/$/, "");

    return [
      {
        // 前端请求 /backend/agent/chat/stream
        // Next.js 转发到 http://127.0.0.1:8000/api/agent/chat/stream
        source: "/backend/:path*",
        destination: `${backendBaseUrl}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;

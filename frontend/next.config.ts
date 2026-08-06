import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        // 前端请求 /backend/agent/chat/stream
        // Next.js 转发到 http://127.0.0.1:8000/api/agent/chat/stream
        source: "/backend/:path*",
        destination: "http://127.0.0.1:8000/api/:path*",
      },
    ];
  },
};

export default nextConfig;
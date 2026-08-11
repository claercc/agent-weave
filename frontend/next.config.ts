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
  // standalone 会让 Next.js 构建出一个适合放进 Docker 的精简服务，不需要把完整的 node_modules 搬进最终镜像
  output: "standalone",
};

export default nextConfig;

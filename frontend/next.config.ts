import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  experimental: {
    // PDF 首次导入可能需要初始化 OCR 和 Embedding 模型。
    // Next.js rewrite 代理默认 30 秒会先于后端处理完成而返回 500。
    proxyTimeout: 5 * 60 * 1000,
  },
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

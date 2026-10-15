import type { NextConfig } from "next";

const rawBackend = process.env.BACKEND_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
const backendUrl =
  rawBackend && rawBackend.startsWith("http")
    ? rawBackend.replace(/\/api\/v1\/?$/, "")
    : "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  allowedDevOrigins: ['192.168.0.163'],
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${backendUrl}/api/v1/:path*`,
      },
    ];
  },
};

export default nextConfig;


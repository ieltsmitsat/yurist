import type { NextConfig } from "next";

const backendUrl = process.env.NEXT_PUBLIC_API_URL
  ? process.env.NEXT_PUBLIC_API_URL.replace(/\/api\/v1\/?$/, "")
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


/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // API base is provided at runtime via NEXT_PUBLIC_API_URL; images are
  // served by the FastAPI backend's /media static mount (real filesystem
  // paths, not next/image's remote-loader), so unoptimized is simplest here.
  images: { unoptimized: true },
};
module.exports = nextConfig;

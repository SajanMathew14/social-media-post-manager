/** @type {import('next').NextConfig} */
const nextConfig = {
  transpilePackages: ['@social-media-manager/shared'],
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  },
  // Production optimizations
  output: 'standalone',
  poweredByHeader: false,
  compress: true,
}

module.exports = nextConfig

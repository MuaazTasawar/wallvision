/** @type {import('next').NextConfig} */
const nextConfig = {
  webpack: (config, { isServer }) => {
    if (isServer) {
      // Plotly is client-side only — exclude from SSR bundle
      config.externals = [...(config.externals || []), 'plotly.js'];
    }
    return config;
  },
};

export default nextConfig;
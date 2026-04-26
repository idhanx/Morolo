/** @type {import('next').NextConfig} */
const nextConfig = {
    output: "standalone",
    env: {
        NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
        NEXT_PUBLIC_OM_UI_URL: process.env.NEXT_PUBLIC_OM_UI_URL || "http://localhost:8585",
    },
};

module.exports = nextConfig;

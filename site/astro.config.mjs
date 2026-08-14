// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import tailwindcss from '@tailwindcss/vite';

// https://astro.build/config
export default defineConfig({
  site: 'https://mcp-tool-shop-org.github.io',
  base: '/comfy-preflight',
  integrations: [
    starlight({
      title: 'comfy-preflight',
      logo: {
        // A LOCAL file — external HTTPS URLs fail Vite's ESM loader. The square gate icon
        // rather than the wide wordmark: a 2.96:1 wordmark in a Starlight header shrinks to
        // an unreadable smear, and the icon is a purpose-drawn second drawing, not a crop.
        src: './src/assets/icon.png',
        alt: 'comfy-preflight',
        href: '/comfy-preflight/',
        replacesTitle: false,
      },
      description: 'A gate that runs on a ComfyUI workflow graph in the seconds before submission and halts a submission that would spend credits producing a known-wrong result. Zero-prerequisite npx launcher — no Python needed.',
      disable404Route: true,
      social: [
        { icon: 'github', label: 'GitHub', href: 'https://github.com/mcp-tool-shop-org/comfy-preflight' },
      ],
      sidebar: [
        {
          label: 'Handbook',
          autogenerate: { directory: 'handbook' },
        },
      ],
      customCss: ['./src/styles/starlight-custom.css'],
    }),
  ],
  vite: {
    plugins: [tailwindcss()],
  },
});

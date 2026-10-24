import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'vitest/config';

const backend = 'http://localhost:8888';

export default defineConfig({
	plugins: [tailwindcss(), sveltekit()],
	server: {
		port: 5173,
		proxy: {
			'/api': backend,
			'/client': backend,
			'/ws': { target: backend, ws: true }
		}
	},
	test: {
		include: ['src/**/*.test.ts'],
		environment: 'node'
	}
});

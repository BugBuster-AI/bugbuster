import react from '@vitejs/plugin-react';
import {defineConfig} from 'vite';
import path from 'path';
import svgr from "vite-plugin-svgr";
import {viteStaticCopy} from "vite-plugin-static-copy";
import {viteCommonjs} from '@originjs/vite-plugin-commonjs'
import {nodePolyfills} from 'vite-plugin-node-polyfills'

// https://vite.dev/config/
export default defineConfig({
    plugins: [
        react({
            jsxImportSource: '@emotion/react',
            babel: {
                plugins: ['@emotion/babel-plugin'],
            },
        }),
        nodePolyfills({
            include: ['util'], // Полифиллы для модуля 'util'
        }),
        svgr(),
        viteStaticCopy({
            targets: [
                {
                    src: 'node_modules/web-tree-sitter/tree-sitter.wasm',
                    dest: 'public/tree-sitter.wasm',
                },
                {
                    src: 'node_modules/curlconverter/dist/tree-sitter-bash.wasm',
                    dest: 'public/tree-sitter-bash.wasm',
                },
            ],
        }),
    ],
    server: {
        proxy: {
            '/api': {
                target: 'http://localhost:7665',
                changeOrigin: true,
                secure: false,
            }
        }
    },
    preview: {
        allowedHosts: true,
    },
    esbuild: {
        supported: {
            'top-level-await': true
        },
    },
    optimizeDeps: {
        esbuildOptions: {
            target: "esnext",
            supported: {
                "top-level-await": true
            },
        },
    },
    resolve: {
        alias: {
            '@Common': path.resolve(__dirname, './src/common'),
            '@Components': path.resolve(__dirname, './src/common/components'),
            '@Pages': path.resolve(__dirname, './src/pages'),
            '@Assets': path.resolve(__dirname, './src/assets'),
            "@Entities": path.resolve(__dirname, './src/entities'),
            "@Features": path.resolve(__dirname, './src/features')
        },
    }
})

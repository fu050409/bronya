import { defineConfig } from '@farmfe/core';
import vue from 'unplugin-vue/vite';

export default defineConfig({
    vitePlugins: [vue()],
});

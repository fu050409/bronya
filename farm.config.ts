import { defineConfig } from '@farmfe/core';

import postcss from '@farmfe/js-plugin-postcss';
import vue from 'unplugin-vue/vite';

export default defineConfig({
    plugins: [postcss()],
    vitePlugins: [vue()],
});

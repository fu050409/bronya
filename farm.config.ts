import { defineConfig } from '@farmfe/core';

import postcss from '@farmfe/js-plugin-postcss';
import vue from 'unplugin-vue/rollup';

export default defineConfig({
    plugins: [postcss()],
    vitePlugins: [vue()],
});

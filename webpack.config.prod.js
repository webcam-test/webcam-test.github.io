const { merge } = require('webpack-merge');
const common = require('./webpack.common.js');
const HtmlWebpackPlugin = require('html-webpack-plugin');
const CopyPlugin = require('copy-webpack-plugin');

module.exports = merge(common, {
  mode: 'production',
  plugins: [
    new HtmlWebpackPlugin({
      template: './index.html',
    }),
    new CopyPlugin({
      patterns: [
        { from: 'img', to: 'img' },
        { from: 'css', to: 'css' },
        { from: 'js/vendor', to: 'js/vendor' },
        { from: 'icon.svg', to: 'icon.svg' },
        { from: 'favicon.ico', to: 'favicon.ico' },
        { from: 'robots.txt', to: 'robots.txt' },
        { from: 'icon.png', to: 'icon.png' },
        { from: '404.html', to: '404.html' },
        { from: 'site.webmanifest', to: 'site.webmanifest' },
        { from: 'webcam-recorder.html', to: 'webcam-recorder.html' },
        { from: 'webcam-effects.html', to: 'webcam-effects.html' },
        { from: 'webcam-gif.html', to: 'webcam-gif.html' },
        { from: 'webcam-timelapse.html', to: 'webcam-timelapse.html' },
        { from: 'webcam-quality-test.html', to: 'webcam-quality-test.html' },
        { from: 'webcam-zoom-test.html', to: 'webcam-zoom-test.html' },
        { from: 'webcam-brightness-test.html', to: 'webcam-brightness-test.html' },
        { from: 'webcam-color-test.html', to: 'webcam-color-test.html' },
        { from: 'camera-comparison.html', to: 'camera-comparison.html' },
        { from: 'webcam-lighting-test.html', to: 'webcam-lighting-test.html' },
        { from: 'webcam-framing-guide.html', to: 'webcam-framing-guide.html' },
      ],
    }),
  ],
});

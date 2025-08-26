const { defineConfig } = require('cypress');

module.exports = defineConfig({
  video: false,
  e2e: {
    baseUrl: 'http://localhost:8080',
    supportFile: false,
    viewportWidth: 1280,
    viewportHeight: 900,
    defaultCommandTimeout: 15000,
  },
});



import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './tests',
  workers: 1,
  timeout: 30000,
  use: {
    baseURL: 'http://127.0.0.1:5173',
    headless: true,
    launchOptions: {
      executablePath:
        process.env.PLAYWRIGHT_CHROME_PATH ||
        'C:/Program Files/Google/Chrome/Application/chrome.exe',
    },
    screenshot: 'only-on-failure',
  },
  reporter: 'list',
});

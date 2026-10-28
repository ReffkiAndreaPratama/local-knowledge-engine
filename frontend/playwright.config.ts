import { defineConfig, devices } from '@playwright/test'
import { existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const here = path.dirname(fileURLToPath(import.meta.url))
const backendDir = path.resolve(here, '../backend')

// Prefer an explicit interpreter (CI installs into the system Python), then the
// local virtualenv, then plain `python` so the config is cross-platform.
function resolvePython(): string {
  const explicit = process.env.LKE_PYTHON
  if (explicit) return explicit
  const candidates =
    process.platform === 'win32'
      ? [path.join(backendDir, '.venv', 'Scripts', 'python.exe')]
      : [path.join(backendDir, '.venv', 'bin', 'python')]
  return candidates.find((candidate) => existsSync(candidate)) ?? 'python'
}

const pythonExe = resolvePython()

const API_PORT = 8011
const WEB_PORT = 5174

export default defineConfig({
  testDir: './e2e',
  timeout: 90_000,
  expect: { timeout: 20_000 },
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: `http://127.0.0.1:${WEB_PORT}`,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    {
      // Isolated database so the e2e run never touches the user's real index.
      command: `"${pythonExe}" -m uvicorn app.main:app --host 127.0.0.1 --port ${API_PORT}`,
      cwd: backendDir,
      url: `http://127.0.0.1:${API_PORT}/api/health/`,
      env: {
        ...process.env,
        DATABASE_URL: 'sqlite:///./data/e2e.db',
        ENABLE_SEMANTIC_SEARCH: 'false',
        ENABLE_AI_ASSISTANT: 'false',
        STORE_SEARCH_HISTORY: 'false',
      },
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command: `node node_modules/vite/bin/vite.js --host 127.0.0.1 --port ${WEB_PORT} --strictPort`,
      cwd: here,
      url: `http://127.0.0.1:${WEB_PORT}`,
      env: {
        ...process.env,
        VITE_API_TARGET: `http://127.0.0.1:${API_PORT}`,
      },
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
})

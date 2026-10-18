/**
 * Activ-Ate frontend configuration.
 *
 * USE_MOCK_API = true  → every API call is answered by the in-browser mock backend
 *                        (assets/js/mock/), data lives in localStorage. No server needed.
 * USE_MOCK_API = false → calls go to API_BASE_URL over HTTPS (see docs/API.md).
 *
 * You can also override per browser for testing:
 *   localStorage.setItem('activate.useMock', 'false')   // use real backend
 *   localStorage.removeItem('activate.useMock')         // back to the value below
 */
const stored = (() => {
  try { return localStorage.getItem('activate.useMock'); } catch { return null; }
})();

export const CONFIG = {
  /** Base URL of the REST API. Same-origin path is recommended (nginx proxies /api/ to the backend). */
  API_BASE_URL: '/api/v1',

  /** Switch between mock backend and real backend. */
  USE_MOCK_API: stored === null ? true : stored === 'true',

  /** Simulated network latency of the mock backend in ms [min, max]. */
  MOCK_LATENCY_MS: [150, 450],

  /** Request timeout for the real backend (AI endpoints can take a few seconds). */
  REQUEST_TIMEOUT_MS: 30000,

  APP_NAME: 'Activ-Ate',
};

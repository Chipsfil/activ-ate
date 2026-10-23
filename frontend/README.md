# Activ-Ate frontend

Static web app built with HTML, CSS, and JavaScript modules. It has no build
step. The app can use the Flask API or an in-browser mock whose data is stored
in `localStorage`.

## Run locally

Serve this directory over HTTP (ES modules do not run from `file://`):

```bash
cd frontend
python3 -m http.server 8080
```

Open <http://localhost:8080>. The frontend uses the real API by default at
`http://127.0.0.1:8000/api/v1`. Start the backend using
[`../backend/README.md`](../backend/README.md).

To use the mock instead, open the browser console and run:

```javascript
localStorage.setItem('activate.useMock', 'true');
location.reload();
```

Mock mode includes a demo account (`demo` / `demo1234`). To return to the real
API, set `activate.useMock` to `'false'` or remove the setting. To change the
API address, set `activate.apiBaseUrl` to the full API base URL, for example
`http://localhost:8000/api/v1`.

## Structure

- Root HTML files are the app pages.
- `assets/css/` contains styles; `assets/js/pages/` contains page behavior.
- `assets/js/api.js` handles API requests; `assets/js/mock/` implements mock
  mode.
- `assets/data/sports.json` provides the sports catalog.

The API contract is in [`docs/API.md`](docs/API.md).

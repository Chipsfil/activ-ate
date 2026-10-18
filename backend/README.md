# Activ-Ate backend (Flask + PostgreSQL)

Il backend implementa l'API REST usata da `frontend/assets/js/api.js`.
Le route sono separate per dominio:

```text
backend/
├── app.py                 # crea Flask e registra i blueprint
├── api/
│   ├── common.py          # DB, autenticazione e serializzatori condivisi
│   ├── auth.py            # registrazione, login, refresh, logout
│   ├── profile.py         # profilo, obiettivi e onboarding
│   ├── activity.py        # sport, dashboard, check-in e workout
│   ├── nutrition.py       # pasti e riepiloghi nutrizionali
│   ├── recommendations.py # raccomandazioni giornaliere
│   ├── community.py       # rete, leaderboard e feed
│   └── coach.py           # conversazioni e messaggi coach
```

Non esiste un file per ogni singola API: le API dello stesso dominio condividono
validazione e logica.

La configurazione è in `config.py`, senza file `.env`. Prima dell'avvio modifica
`DATABASE_URL`, `JWT_SECRET`, `FRONTEND_ORIGIN` e `COOKIE_SECURE`.

## Avvio locale

Richiede Python 3.11+ e PostgreSQL 14+.

### Backend

```bash
cd backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
# modifica config.py con l'URL del tuo PostgreSQL
psql "$(python3 -c 'from config import DATABASE_URL; print(DATABASE_URL)')" -f schema.sql
python app.py
```

Per verificare il collegamento:

```bash
curl http://127.0.0.1:8000/api/v1/health
```

Il comando legge `DATABASE_URL` direttamente da `config.py`, quindi non serve
una variabile d'ambiente.

### Frontend e collegamento locale

In un secondo terminale:

```bash
cd frontend
python3 -m http.server 8080
```

Il frontend usa normalmente `/api/v1`. In locale apri la console del browser su
`http://localhost:8080` ed esegui:

```javascript
localStorage.setItem("activate.useMock", "false");
localStorage.setItem("activate.apiBaseUrl", "http://127.0.0.1:8000/api/v1");
location.reload();
```

Per tornare al mock:

```javascript
localStorage.removeItem("activate.useMock");
localStorage.removeItem("activate.apiBaseUrl");
location.reload();
```

Il backend deve avere `COOKIE_SECURE = False` quando si usa HTTP locale. Il
browser invierà il cookie di refresh solo se frontend e backend usano origini
consentite da `FRONTEND_ORIGIN`.

## Due VM Google Cloud: versione didattica semplice

Per una demo basica il browser comunica direttamente con Flask:

```text
Frontend VM: http://FRONTEND_IP:8080
      │
      └── HTTP/fetch + CORS
              │
Backend VM: http://BACKEND_IP:8000
      │
      └── PostgreSQL sulla rete privata
```

Nel frontend imposta in `assets/js/config.js`:

```javascript
API_BASE_URL: 'http://BACKEND_VM_PUBLIC_IP:8000/api/v1',
USE_MOCK_API: false
```

Nel backend imposta in `config.py` l'origine reale della VM frontend:

```python
HOST = "0.0.0.0"
PORT = 8000
FRONTEND_ORIGIN = ["http://FRONTEND_VM_PUBLIC_IP:8080"]
COOKIE_SECURE = False
COOKIE_SAMESITE = "Lax"
```

Apri nel firewall Google Cloud `tcp:8000` solo per il traffico necessario alla
demo e non aprire mai `tcp:5432` a Internet. Il backend viene avviato con il server Flask integrato:

```bash
python app.py
```

Questa configurazione è adatta a una demo didattica. Usa HTTP e quindi non
deve trattare password o dati reali. `debug=False` è impostato nel codice.

## PostgreSQL su un altro server

Sul server PostgreSQL:

```sql
CREATE USER activate WITH PASSWORD 'una-password-lunga';
CREATE DATABASE activate OWNER activate;
```

Consentire la rete del server Flask in `postgresql.conf`:

```conf
listen_addresses = '*'
```

In `pg_hba.conf` autorizzare solo l'IP privato del server Flask:

```conf
hostssl activate activate 10.0.2.15/32 scram-sha-256
```

Riavviare PostgreSQL e aprire la porta 5432 solo sulla rete privata.

Sul server Flask modifica `backend/config.py`:

```python
DATABASE_URL = "postgresql://activate:PASSWORD@10.0.0.20:5432/activate?sslmode=require"
JWT_SECRET = "una-chiave-casuale-lunga"
FRONTEND_ORIGIN = "https://your-domain.example"
COOKIE_SECURE = True
```

Genera il segreto con:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

Poi inizializza lo schema:

```bash
psql "postgresql://activate:PASSWORD@10.0.0.20:5432/activate?sslmode=require" -f schema.sql
python scripts/import_sports.py
```

L'app apre una connessione PostgreSQL per richiesta usando Psycopg. PostgreSQL
non viene montato come cartella: Python legge righe e colonne via protocollo
TCP e usa query parametrizzate con placeholder `%s`.

Per importare gli sport, `scripts/import_sports.py` legge
`frontend/assets/data/sports.json` e aggiorna la tabella `sports`.

## Collegamento frontend

Impostare `CONFIG.USE_MOCK_API = false` in
`frontend/assets/js/config.js`. Nginx inoltra `/api/` a
`http://127.0.0.1:8000`; frontend e backend restano sullo stesso dominio e il
cookie HttpOnly di refresh funziona senza CORS aggiuntivo.

Le risposte AI e il reset password hanno fallback locali. Prima del go-live
aggiungere un provider email e, se necessario, un provider LLM.

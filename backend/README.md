# Activ-Ate backend

For deployment on the existing Linux VMs with Google Cloud SQL, follow
[GCP_DEPLOYMENT.md](../GCP_DEPLOYMENT.md).

Backend REST di Activ-Ate, realizzato con Flask e PostgreSQL remoto
(Supabase o PostgreSQL installato su un altro server).

Il backend è organizzato per dominio:

```text
backend/
├── app.py                  # avvio Flask e registrazione dei Blueprint
├── config.py               # carica la configurazione da .env
├── api/
│   ├── common.py           # connessione DB, JWT e helper condivisi
│   ├── auth.py             # registrazione, login e sessioni
│   ├── profile.py          # profilo, obiettivi e onboarding
│   ├── activity.py         # sport, dashboard, check-in e workout
│   ├── nutrition.py        # pasti e riepiloghi nutrizionali
│   ├── recommendations.py  # raccomandazioni
│   ├── community.py        # community e leaderboard
│   ├── coach.py            # coach e conversazioni
│   └── system.py           # health check
├── schema.sql              # schema PostgreSQL
└── scripts/import_sports.py
```

Le API dello stesso dominio condividono validazione e logica: non esiste un
file separato per ogni singola route. Il prefisso comune è
`/api/v1`. L'elenco aggiornato delle route è in
[frontend/docs/API.md](../frontend/docs/API.md).

## Configurazione

La configurazione runtime è nel file locale `backend/.env`, escluso da Git.
Partire da [.env.example](.env.example):

```bash
cd backend
cp .env.example .env
```

Modificare almeno:

```dotenv
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DATABASE?sslmode=require
JWT_SECRET=una-stringa-casuale-lunga
FRONTEND_ORIGIN=http://localhost:8080
COOKIE_SECURE=false
COOKIE_SAMESITE=Lax
HOST=0.0.0.0
PORT=8000
```

`config.py` legge `.env` con `python-dotenv`; non contiene credenziali
hardcoded. Non committare e non condividere `backend/.env`.

Per generare un segreto JWT:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

## Supabase e PostgreSQL remoto

In Supabase usare la connection string **Session Pooler** quando la direct
connection IPv6 non è raggiungibile dalla VM. Copiare la stringa in
`DATABASE_URL`, mantenendo `sslmode=require`.

Per un PostgreSQL gestito autonomamente:

1. creare database e utente applicativo;
2. consentire nel firewall solo l'IP privato della VM Flask;
3. configurare `listen_addresses` e `pg_hba.conf`;
4. usare TLS e una password URL-encoded nella connection string.

Esempio SQL eseguito sul server PostgreSQL:

```sql
CREATE USER activate WITH PASSWORD 'una-password-lunga';
CREATE DATABASE activate OWNER activate;
```

Poi applicare lo schema dal backend:

```bash
cd backend
psql "$(python3 -c 'from config import DATABASE_URL; print(DATABASE_URL)')" -f schema.sql
python scripts/import_sports.py
```

Lo script di import legge [sports.json](../frontend/assets/data/sports.json) e
inserisce o aggiorna gli sport nella tabella `sports`.

Python non legge file dal server PostgreSQL: apre una connessione TCP tramite
Psycopg, invia query SQL parametrizzate e riceve righe e colonne. Il database
può quindi stare su un server diverso dalla VM Flask; deve essere raggiungibile
in rete e autorizzare l'IP del backend.

## Avvio locale

Richiede Python 3.11+.

```bash
cd backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# modificare .env con la connection string reale
psql "$(python3 -c 'from config import DATABASE_URL; print(DATABASE_URL)')" -f schema.sql
python app.py
```

Il server Flask ascolta su `0.0.0.0:8000` con `debug=False`.
Per verificare applicazione e database:

```bash
curl http://127.0.0.1:8000/api/v1/health
```

Risposta attesa:

```json
{"database":"ok","status":"ok"}
```

## Avvio del frontend e collegamento

In un secondo terminale:

```bash
cd frontend
python3 -m http.server 8080
```

Per collegare il frontend al backend reale:

```javascript
localStorage.setItem("activate.useMock", "false");
localStorage.setItem("activate.apiBaseUrl", "http://127.0.0.1:8000/api/v1");
location.reload();
```

Su due VM sostituire l'URL con l'indirizzo del backend:

```javascript
localStorage.setItem(
  "activate.apiBaseUrl",
  "http://BACKEND_VM_PUBLIC_IP:8000/api/v1"
);
```

Impostare `FRONTEND_ORIGIN` sull'origine esatta del frontend, per esempio
`http://FRONTEND_VM_PUBLIC_IP:8080`. Il backend usa CORS con credenziali per
permettere il cookie HttpOnly di refresh.

Per tornare al mock:

```javascript
localStorage.removeItem("activate.useMock");
localStorage.removeItem("activate.apiBaseUrl");
location.reload();
```

## Architettura demo a due VM

```text
Browser
   │ HTTP/fetch + CORS
Frontend VM: python3 -m http.server 8080
   │
Backend VM: python app.py, porta 8000
   │
Supabase/PostgreSQL remoto
```

Per questa demo non servono Nginx o Gunicorn. Aprire la porta TCP `8000` solo
al traffico necessario e non esporre mai la porta PostgreSQL a Internet.
L'uso di HTTP e `COOKIE_SECURE=false` è adatto solo a dati dimostrativi:
per dati reali servono HTTPS, cookie Secure e un deployment WSGI/reverse
proxy adeguato.

## Verifica registrazione e login

```bash
curl -i -c /tmp/activate-cookies.txt \
  -X POST http://127.0.0.1:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Test",
    "last_name": "User",
    "username": "test.user.unique",
    "email": "test.user.unique@example.invalid",
    "password": "password123",
    "gender": "unspecified",
    "date_of_birth": "1995-01-10",
    "weight_kg": 70,
    "height_cm": 175
  }'
```

La risposta corretta è `201` e contiene `access_token` e `user`; il cookie
`refresh_token` viene impostato nella risposta. Per verificare il database,
controllare la riga corrispondente in `users` senza stampare password o
connection string nei log.

Le funzioni AI, l'invio email per il reset password e alcune funzioni avanzate
di community/coach sono predisposte come fallback o placeholder. Non
considerare l'attuale configurazione una installazione production-ready.

## Leggere e modificare il codice

Ogni modulo in `api/` contiene le route di un dominio. I decorator `@bp.get`,
`@bp.post`, `@bp.put`, `@bp.patch` e `@bp.delete` indicano metodo e URL;
la funzione subito sotto gestisce la richiesta e restituisce la risposta.
`@auth_required` controlla il token e salva l'ID dell'utente in `g.user_id`.

Le query usano parametri `%s`: i valori della richiesta vengono passati
separatamente dalla stringa SQL. `with conn() as connection` apre una
connessione e la chiude alla fine del blocco; Psycopg esegue il commit in caso
di successo e il rollback in caso di errore. Alcune route mantengono commit
espliciti prima di leggere la risposta o creare una nuova sessione.

`common.py` contiene solo helper condivisi. `replace_preferences` in
`profile.py` salva le preferenze per entrambe le route del profilo.
`week_start` e `weekly_target` mantengono gli stessi calcoli per dashboard,
statistiche, community e coach. I commenti spiegano le regole meno immediate,
come il mantenimento di una serie di allenamenti fino al giorno successivo.

## Test di regressione

Dalla root del repository, con l'ambiente virtuale del backend attivo:

```bash
python -m unittest discover -s backend/tests -v
```

I test standard usano un database simulato e non leggono le credenziali di
`.env`. Verificano autenticazione, cookie, validazione, serializzazione,
profilo, workout, community e placeholder. Il test PostgreSQL viene saltato
se non è configurato un database di test.

Per verificare anche un flusso completo con PostgreSQL, indicare un database
locale dedicato ai test:

```bash
ACTIVATE_TEST_DATABASE_URL='postgresql://USER:PASSWORD@localhost/activate_test' \
  python -m unittest discover -s backend/tests -v
```

Il test crea uno schema con nome casuale e lo elimina alla fine. Richiede
permessi per creare lo schema e le estensioni `pgcrypto` e `citext` previste
da `schema.sql`. Usare un database separato da quello dell'applicazione.

# FastAPI stack quickstart

1. Start the services:

   ```bash
   docker compose -f docker-compose.fastapi.yml up --build
   ```

   This launches:

   - `service-front` on http://localhost:8000
   - `service-api` on http://localhost:8001 (interactive docs at `/docs`)
   - `db` Postgres instance on port 54320 (`lpa` / `lpa`)

2. Create an account via the UI:

   - Visit http://localhost:8000
   - Select **Create an account**
   - Submit your email address and password
   - The front end will call the API to create and activate the account automatically, then redirect you to the dashboard

3. Sign out/in:

   - Use **Sign out** on the dashboard to clear the session cookie
   - Return to http://localhost:8000/login and sign in with the same credentials

4. API-only verification (optional):

   ```bash
   # Create a user
   curl -X POST http://localhost:8001/v2/users/ \
     -H 'content-type: application/json' \
     -d '{"username": "demo@example.com", "password": "Passw0rd!"}'

   # Activate the user
   curl -X POST http://localhost:8001/v2/users/ \
     -H 'content-type: application/json' \
     -d '{"activationToken": "<token-from-previous-response>"}'

   # Authenticate
   curl -X POST http://localhost:8001/v2/authenticate \
     -H 'content-type: application/json' \
     -d '{"username": "demo@example.com", "password": "Passw0rd!", "Update": true}'
   ```

   The final call returns the session token that the front end persists in a signed cookie.

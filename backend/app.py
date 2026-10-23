"""Start the Activ-Ate Flask API."""

import psycopg
from flask import Flask
from flask_cors import CORS

from api import (
    auth,
    profile,
    activity,
    nutrition,
    community,
    recommendations,
    coach,
    system,
)
from config import FRONTEND_ORIGIN, HOST, PORT
from api.common import err

app = Flask(__name__)
# Accept both spellings of the configured local frontend address.
frontend_origins = {
    FRONTEND_ORIGIN,
    FRONTEND_ORIGIN.replace("localhost", "127.0.0.1"),
    FRONTEND_ORIGIN.replace("127.0.0.1", "localhost"),
}
# Allow the configured frontend origins to make requests with cookies.
CORS(app, origins=list(frontend_origins), supports_credentials=True)
# Attach each domain's routes to the same Flask application.
for module in (
    auth,
    profile,
    activity,
    nutrition,
    community,
    recommendations,
    coach,
    system,
):
    app.register_blueprint(module.bp)


@app.errorhandler(404)
def not_found(_):
    return err("Endpoint not found.", "not_found", 404)


@app.errorhandler(Exception)
def unhandled(error):
    # Return the standard API error for database failures; re-raise other errors.
    if isinstance(error, psycopg.Error):
        return err("Database error.", "server_error", 503)
    raise error


if __name__ == "__main__":
    # Start the local development server using the environment settings.
    app.run(host=HOST, port=PORT, debug=False)

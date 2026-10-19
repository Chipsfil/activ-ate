"""Start the Activ-Ate Flask API."""

from flask import Flask
from flask_cors import CORS

from api import auth, profile, activity, nutrition, community, recommendations, coach, system
from config import FRONTEND_ORIGIN, HOST, PORT
from api.common import err

app = Flask(__name__)
frontend_origins = {
    FRONTEND_ORIGIN,
    FRONTEND_ORIGIN.replace("localhost", "127.0.0.1"),
    FRONTEND_ORIGIN.replace("127.0.0.1", "localhost"),
}
CORS(app, origins=list(frontend_origins), supports_credentials=True)
for module in (auth, profile, activity, nutrition, community, recommendations, coach, system):
    app.register_blueprint(module.bp)


@app.errorhandler(404)
def not_found(_):
    return err("Endpoint not found.", "not_found", 404)


@app.errorhandler(Exception)
def unhandled(error):
    import psycopg

    if isinstance(error, psycopg.Error):
        return err("Database error.", "server_error", 503)
    raise error

if __name__ == "__main__":
    app.run(host=HOST, port=PORT, debug=False)

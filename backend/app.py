"""Activ-Ate Flask API application factory and blueprint registry."""
from flask import Flask
from flask_cors import CORS
from config import FRONTEND_ORIGIN, PORT, HOST
from api import auth, profile, activity, nutrition, community, recommendations, coach, system

app = Flask(__name__)
CORS(app, origins=FRONTEND_ORIGIN, supports_credentials=True)
for module in (auth, profile, activity, nutrition, community, recommendations, coach, system):
    app.register_blueprint(module.bp)

@app.errorhandler(404)
def not_found(_):
    from api.common import err
    return err("Endpoint not found.", "not_found", 404)

@app.errorhandler(Exception)
def unhandled(error):
    # Database errors are returned in the repository's standard JSON shape.
    import psycopg
    from api.common import err
    if isinstance(error, psycopg.Error):
        return err("Database error.", "server_error", 503)
    raise error

if __name__ == "__main__":
    app.run(host=HOST, port=PORT, debug=False)

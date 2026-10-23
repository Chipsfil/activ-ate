from flask import Blueprint

from .common import auth_required

bp = Blueprint("nutrition", __name__)


def not_implemented():
    @auth_required
    def view():
        return {"message": "Nutrition is not implemented in the backend."}, 501
    return view


for path, name, methods in [
    ("/nutrition/summary", "nutrition_summary", ["GET"]),
    ("/meals", "meals", ["GET", "POST"]),
    ("/meals/estimate", "estimate", ["POST"]),
]:
    bp.add_url_rule("/api/v1" + path, name, not_implemented(), methods=methods)


@bp.delete("/api/v1/meals/<mid>")
@auth_required
def delete_meal(mid):
    return {"message": "Nutrition is not implemented in the backend."}, 501

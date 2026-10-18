from flask import Blueprint
from .common import *

bp = Blueprint("nutrition", __name__)

@bp.get("/api/v1/nutrition/summary")
@auth_required
def nutrition_summary():
    d=parse_date(request.args.get("date"),date.today())
    with conn() as c:return {"date":iso(d),"totals":totals(c,g.user_id,d),"targets":{"kcal":2350,"protein_g":140,"carbs_g":250,"fat_g":80}}

@bp.get("/api/v1/meals")
@auth_required
def meals():
    d=parse_date(request.args.get("date"),date.today())
    with conn() as c:return {"items":[{**{k:r[k] for k in ("meal_type","description","source","kcal","protein_g","carbs_g","fat_g")},"id":str(r["id"]),"eaten_on":iso(r["eaten_on"])} for r in c.execute("SELECT * FROM meals WHERE user_id=%s AND eaten_on=%s ORDER BY created_at",(g.user_id,d))]}
@bp.post("/api/v1/meals/estimate")
@auth_required
def estimate(): return {"estimate_id":str(uuid.uuid4()),"items":[],"totals":{"kcal":0,"protein_g":0,"carbs_g":0,"fat_g":0}}
@bp.post("/api/v1/meals")
@auth_required
def create_meal():
    b=body(); d=parse_date(b.get("eaten_on"),date.today())
    with conn() as c:
        r=c.execute("INSERT INTO meals(user_id,eaten_on,meal_type,description,source,kcal,protein_g,carbs_g,fat_g) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *",(g.user_id,d,b.get("meal_type","snack"),b.get("description",""),b.get("source","manual"),b.get("kcal",0),b.get("protein_g",0),b.get("carbs_g",0),b.get("fat_g",0))).fetchone();c.commit()
        return {"meal":{**{k:r[k] for k in ("meal_type","description","source","kcal","protein_g","carbs_g","fat_g")},"id":str(r["id"]),"eaten_on":iso(r["eaten_on"])}, "totals":totals(c,g.user_id,d)},201
@bp.delete("/api/v1/meals/<mid>")
@auth_required
def delete_meal(mid):
    with conn() as c:
        r=c.execute("DELETE FROM meals WHERE id=%s AND user_id=%s RETURNING eaten_on",(mid,g.user_id)).fetchone()
        if not r:return err("Meal not found.","not_found",404)
        c.commit();return {"totals":totals(c,g.user_id,r["eaten_on"])}

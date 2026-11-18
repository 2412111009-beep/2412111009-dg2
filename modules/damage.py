"""Báo hỏng kèm ảnh, xử lý báo hỏng, phục vụ file ảnh tải lên."""
import os, uuid
from flask import (
    render_template,
    request,
    redirect,
    url_for,
    flash,
    g,
    abort,
    send_from_directory)
from werkzeug.utils import secure_filename
from core import app, db, q, one, login_required, roles, UPLOAD_DIR


def save_photo(file):
    if not file or not file.filename:
        return None
    ext = os.path.splitext(secure_filename(file.filename))[1].lower()
    if ext not in (".png", ".jpg", ".jpeg", ".gif", ".webp"):
        raise ValueError("Chỉ nhận ảnh PNG, JPG, GIF hoặc WEBP.")
    name = uuid.uuid4().hex + ext
    file.save(os.path.join(UPLOAD_DIR, name))
    return name


@app.route("/damage/new", methods=["GET", "POST"])
@login_required
def damage_new():
    rooms = q("SELECT * FROM rooms ORDER BY name")
    equips = q("SELECT * FROM equipment ORDER BY name")
    if request.method == "POST":
        f = request.form
        if not f.get("description", "").strip():
            flash("Hãy mô tả tình trạng hỏng.", "err")
        elif not f.get("equipment_id") and not f.get("room_id"):
            flash("Hãy chọn thiết bị hoặc phòng bị hỏng.", "err")
        else:
            try:
                photo = save_photo(request.files.get("photo"))
            except ValueError as e:
                flash(str(e), "err")
                return render_template("damage_new.html", rooms=rooms, equips=equips)
            db().execute("INSERT INTO damage_reports(reporter_id,equipment_id,room_id,description,photo) VALUES (?,?,?,?,?)",
                         (g.user["id"], f.get("equipment_id") or None, f.get("room_id") or None,
                          f["description"].strip(), photo))
            db().commit()
            flash("Đã gửi báo hỏng.", "ok")
            return redirect(url_for("damage_list"))
    return render_template("damage_new.html", rooms=rooms, equips=equips)


@app.route("/damage")
@login_required
def damage_list():
    sql = """SELECT d.*, u.full_name, e.name ename, r.name rname FROM damage_reports d
             JOIN users u ON u.id=d.reporter_id LEFT JOIN equipment e ON e.id=d.equipment_id
             LEFT JOIN rooms r ON r.id=d.room_id"""
    if g.user["role"] == "admin":
        rows = q(sql + " ORDER BY (d.status='open') DESC, d.created_at DESC")
    else:
        rows = q(sql + " WHERE d.reporter_id=? ORDER BY d.created_at DESC", (g.user["id"],))
    return render_template("damage_list.html", rows=rows)


@app.route("/admin/damage/<int:did>/resolve", methods=["POST"])
@roles("admin")
def damage_resolve(did):
    d = one("SELECT * FROM damage_reports WHERE id=?", (did,))
    if not d:
        abort(404)
    db().execute("UPDATE damage_reports SET status='resolved' WHERE id=?", (did,))
    if d["equipment_id"] and request.form.get("restock"):   # thiết bị đã sửa xong -> trả về kho dùng được
        db().execute("UPDATE equipment SET broken_qty=MAX(0, broken_qty-1) WHERE id=?", (d["equipment_id"],))
    db().commit()
    flash("Đã đánh dấu xử lý xong.", "ok")
    return redirect(url_for("damage_list"))


@app.route("/uploads/<path:name>")
@login_required
def uploads(name):
    return send_from_directory(UPLOAD_DIR, name)

"""Quản lý danh mục phòng lab và thiết bị."""
import sqlite3
from flask import render_template, request, redirect, url_for, flash
from core import app, db, q, roles


@app.route("/admin/rooms", methods=["GET", "POST"])
@roles("admin")
def admin_rooms():
    if request.method == "POST":
        f = request.form
        try:
            if f["op"] == "add":
                db().execute("INSERT INTO rooms(name,location,capacity,description) VALUES (?,?,?,?)",
                             (f["name"].strip(), f["location"].strip(), int(f.get("capacity") or 0) or None, f.get("description")))
            elif f["op"] == "toggle":
                db().execute("UPDATE rooms SET is_active=1-is_active WHERE id=?", (int(f["id"]),))
            db().commit()
            flash("Đã lưu.", "ok")
        except (sqlite3.IntegrityError, ValueError):
            flash("Không lưu được (tên phòng đã tồn tại hoặc dữ liệu sai).", "err")
        return redirect(url_for("admin_rooms"))
    return render_template("admin_rooms.html", rows=q("SELECT * FROM rooms ORDER BY name"))


@app.route("/admin/equipment", methods=["GET", "POST"])
@roles("admin")
def admin_equipment():
    if request.method == "POST":
        f = request.form
        try:
            if f["op"] == "add":
                db().execute("INSERT INTO equipment(name,category,quantity,description) VALUES (?,?,?,?)",
                             (f["name"].strip(), f["category"].strip(), int(f["quantity"]), f.get("description")))
            elif f["op"] == "toggle":
                db().execute("UPDATE equipment SET is_active=1-is_active WHERE id=?", (int(f["id"]),))
            elif f["op"] == "qty":
                db().execute("UPDATE equipment SET quantity=?, broken_qty=MIN(broken_qty, ?) WHERE id=?",
                             (int(f["quantity"]), int(f["quantity"]), int(f["id"])))
            db().commit()
            flash("Đã lưu.", "ok")
        except (sqlite3.IntegrityError, ValueError):
            flash("Không lưu được (tên đã tồn tại hoặc số lượng sai).", "err")
        return redirect(url_for("admin_equipment"))
    return render_template("admin_equipment.html", rows=q("SELECT * FROM equipment ORDER BY name"))

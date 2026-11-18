"""Trang tổng quan theo vai trò (quản trị/giảng viên/sinh viên) và quản lý tài khoản."""
from flask import (
    render_template,
    request,
    redirect,
    url_for,
    flash,
    g)
from core import app, db, q, one, login_required, roles, ROLE_LABEL


@app.route("/dashboard")
@login_required
def dashboard():
    role = g.user["role"]
    if role == "admin":
        stats = dict(
            pending=one("SELECT COUNT(*) c FROM bookings WHERE status='pending'")["c"],
            today=one("SELECT COUNT(*) c FROM bookings WHERE status='approved' AND date(start_time)=date('now','localtime')")["c"],
            out=one("SELECT COUNT(*) c FROM loans WHERE returned_at IS NULL")["c"],
            dmg=one("SELECT COUNT(*) c FROM damage_reports WHERE status='open'")["c"],
            inactive=one("SELECT COUNT(*) c FROM users WHERE is_active=0")["c"])
        pend = q("""SELECT b.*, u.full_name, u.role, r.name room FROM bookings b
                    JOIN users u ON u.id=b.user_id LEFT JOIN rooms r ON r.id=b.room_id
                    WHERE b.status='pending' ORDER BY (u.role='lecturer') DESC, b.start_time LIMIT 8""")
        return render_template("dash_admin.html", s=stats, pend=pend)
    mine = q("""SELECT b.*, r.name room FROM bookings b LEFT JOIN rooms r ON r.id=b.room_id
                WHERE b.user_id=? AND b.end_time>=datetime('now','localtime') AND b.status IN ('pending','approved','bumped')
                ORDER BY b.start_time LIMIT 6""", (g.user["id"],))
    bumped = q("SELECT COUNT(*) c FROM bookings WHERE user_id=? AND status='bumped'", (g.user["id"],))[0]["c"]
    return render_template("dash_lecturer.html" if role == "lecturer" else "dash_student.html",
                           mine=mine, bumped=bumped)


@app.route("/admin/users", methods=["GET", "POST"])
@roles("admin")
def admin_users():
    if request.method == "POST":
        uid = int(request.form["id"])
        if uid == g.user["id"]:
            flash("Không thể tự thay đổi tài khoản của chính mình tại đây.", "err")
        else:
            op = request.form["op"]
            if op == "toggle":
                db().execute("UPDATE users SET is_active=1-is_active WHERE id=?", (uid,))
            elif op == "role" and request.form["role"] in ROLE_LABEL:
                db().execute("UPDATE users SET role=? WHERE id=?", (request.form["role"], uid))
            db().commit()
            flash("Đã cập nhật tài khoản.", "ok")
        return redirect(url_for("admin_users"))
    return render_template("admin_users.html", rows=q("SELECT * FROM users ORDER BY is_active, role, full_name"))

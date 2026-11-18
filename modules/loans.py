"""Giao – nhận thiết bị, ghi nhận tình trạng khi trả."""
from flask import (
    render_template,
    request,
    redirect,
    url_for,
    flash,
    g,
    abort)
from core import app, db, q, one, roles, COND_LABEL


@app.route("/admin/loans")
@roles("admin")
def admin_loans():
    to_issue = q("""SELECT b.id bid, b.start_time, b.end_time, u.full_name, be.equipment_id, be.quantity, e.name ename,
                    be.quantity - COALESCE((SELECT SUM(l.quantity) FROM loans l WHERE l.booking_id=b.id AND l.equipment_id=be.equipment_id),0) AS remain
                    FROM bookings b JOIN users u ON u.id=b.user_id
                    JOIN booking_equipment be ON be.booking_id=b.id JOIN equipment e ON e.id=be.equipment_id
                    WHERE b.status='approved' AND b.end_time>=datetime('now','localtime','-1 day')
                    ORDER BY b.start_time""")
    to_issue = [r for r in to_issue if r["remain"] > 0]
    out = q("""SELECT l.*, e.name ename, u.full_name FROM loans l JOIN equipment e ON e.id=l.equipment_id
               JOIN bookings b ON b.id=l.booking_id JOIN users u ON u.id=b.user_id
               WHERE l.returned_at IS NULL ORDER BY l.borrowed_at""")
    history = q("""SELECT l.*, e.name ename, u.full_name FROM loans l JOIN equipment e ON e.id=l.equipment_id
               JOIN bookings b ON b.id=l.booking_id JOIN users u ON u.id=b.user_id
               WHERE l.returned_at IS NOT NULL ORDER BY l.returned_at DESC LIMIT 30""")
    return render_template("admin_loans.html", to_issue=to_issue, out=out, history=history)


@app.route("/admin/loan/issue", methods=["POST"])
@roles("admin")
def loan_issue():
    bid, eid = int(request.form["booking_id"]), int(request.form["equipment_id"])
    be = one("SELECT * FROM booking_equipment WHERE booking_id=? AND equipment_id=?", (bid, eid))
    if not be:
        abort(404)
    db().execute("INSERT INTO loans(booking_id,equipment_id,quantity,handled_by) VALUES (?,?,?,?)",
                 (bid, eid, be["quantity"], g.user["id"]))
    db().commit()
    flash("Đã ghi nhận giao thiết bị.", "ok")
    return redirect(url_for("admin_loans"))


@app.route("/admin/loan/<int:lid>/return", methods=["POST"])
@roles("admin")
def loan_return(lid):
    l = one("SELECT * FROM loans WHERE id=? AND returned_at IS NULL", (lid,))
    if not l:
        abort(404)
    cond = request.form.get("condition", "good")
    if cond not in COND_LABEL:
        abort(400)
    note = request.form.get("note", "").strip()
    d = db()
    d.execute("UPDATE loans SET returned_at=datetime('now','localtime'), return_condition=?, return_note=? WHERE id=?",
              (cond, note, lid))
    if cond in ("damaged", "lost"):
        d.execute("UPDATE equipment SET broken_qty=MIN(quantity, broken_qty+?) WHERE id=?", (l["quantity"], l["equipment_id"]))
        d.execute("INSERT INTO damage_reports(reporter_id,equipment_id,loan_id,description) VALUES (?,?,?,?)",
                  (g.user["id"], l["equipment_id"], lid, f"[Phát hiện khi trả – {COND_LABEL[cond]}] {note}"))
    d.commit()
    flash("Đã ghi nhận trả thiết bị.", "ok")
    return redirect(url_for("admin_loans"))

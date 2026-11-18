"""Lịch tuần, đặt phòng/thiết bị, ưu tiên giảng viên, duyệt yêu cầu."""
import sqlite3
from datetime import datetime, timedelta, date
from flask import (
    render_template,
    request,
    redirect,
    url_for,
    flash,
    g,
    abort)
from core import app, db, q, one, login_required, roles, parse_dt, monday_of, STATUS_LABEL, OPEN_H, CLOSE_H


def build_week(kind, obj_id, monday):
    start = monday.strftime("%Y-%m-%d 00:00")
    end = (monday + timedelta(days=7)).strftime("%Y-%m-%d 00:00")
    if kind == "room":
        rows = q("""SELECT b.*, u.full_name, u.role, NULL qty FROM bookings b JOIN users u ON u.id=b.user_id
                    WHERE b.room_id=? AND b.status IN ('pending','approved') AND b.start_time<? AND b.end_time>?""",
                 (obj_id, end, start))
    else:
        rows = q("""SELECT b.*, u.full_name, u.role, be.quantity qty FROM bookings b
                    JOIN booking_equipment be ON be.booking_id=b.id JOIN users u ON u.id=b.user_id
                    WHERE be.equipment_id=? AND b.status IN ('pending','approved') AND b.start_time<? AND b.end_time>?""",
                 (obj_id, end, start))
    grid = {}
    for d in range(7):
        day = monday + timedelta(days=d)
        for h in range(OPEN_H, CLOSE_H):
            s = datetime(day.year, day.month, day.day, h)
            e = s + timedelta(hours=1)
            cell = [b for b in rows
                    if datetime.strptime(b["start_time"], "%Y-%m-%d %H:%M") < e
                    and datetime.strptime(b["end_time"], "%Y-%m-%d %H:%M") > s]
            grid[(d, h)] = cell
    return grid


@app.route("/schedule")
@login_required
def schedule():
    kind = "equip" if request.args.get("kind") == "equip" else "room"
    rooms = q("SELECT * FROM rooms WHERE is_active=1 ORDER BY name")
    equips = q("SELECT * FROM equipment WHERE is_active=1 ORDER BY name")
    items = rooms if kind == "room" else equips
    try:
        obj_id = int(request.args.get("id", items[0]["id"] if items else 0))
    except ValueError:
        obj_id = 0
    try:
        monday = monday_of(datetime.strptime(request.args.get("week", ""), "%Y-%m-%d").date())
    except ValueError:
        monday = monday_of(date.today())
    obj = next((i for i in items if i["id"] == obj_id), None)
    grid = build_week(kind, obj_id, monday) if obj else {}
    return render_template("schedule.html", kind=kind, items=items, obj=obj, grid=grid,
                           monday=monday, prev=monday - timedelta(days=7), nxt=monday + timedelta(days=7),
                           hours=range(OPEN_H, CLOSE_H), days=[monday + timedelta(days=i) for i in range(7)],
                           today=date.today(), now_str=datetime.now().strftime("%Y-%m-%d %H:%M"))


def create_booking(user, room_id, start, end, purpose, equip):
    """Tạo yêu cầu. Việc chặn trùng do trigger CSDL đảm nhiệm;
    nếu người đặt là giảng viên, thử thay thế các yêu cầu CHƯA DUYỆT của sinh viên rồi chèn lại."""
    d = db()
    bumped = []
    is_lect = user["role"] == "lecturer"

    def bump(where_sql, args):
        victims = d.execute(f"""SELECT b.id FROM bookings b JOIN users u ON u.id=b.user_id
            WHERE b.status='pending' AND u.role='student' AND b.start_time<? AND b.end_time>? AND {where_sql}
            ORDER BY b.created_at DESC""", (end, start, *args)).fetchall()
        for v in victims:
            d.execute("UPDATE bookings SET status='bumped', admin_note=? WHERE id=?",
                      ("Bị thay thế bởi yêu cầu ưu tiên của giảng viên " + user["full_name"], v["id"]))
            bumped.append(v["id"])
        return len(victims)

    try:
        for attempt in range(2):
            try:
                cur = d.execute("INSERT INTO bookings(user_id,room_id,start_time,end_time,purpose) VALUES (?,?,?,?,?)",
                                (user["id"], room_id, start, end, purpose))
                break
            except sqlite3.IntegrityError as e:
                if "ROOM_CONFLICT" in str(e) and is_lect and attempt == 0 and bump("b.room_id=?", (room_id,)):
                    continue
                raise
        bid = cur.lastrowid
        for eid, qty in equip:
            while True:
                try:
                    d.execute("INSERT INTO booking_equipment(booking_id,equipment_id,quantity) VALUES (?,?,?)",
                              (bid, eid, qty))
                    break
                except sqlite3.IntegrityError as e:
                    if "EQUIP_CONFLICT" in str(e) and is_lect:
                        one_victim = d.execute("""SELECT b.id FROM bookings b JOIN users u ON u.id=b.user_id
                            JOIN booking_equipment be ON be.booking_id=b.id
                            WHERE b.status='pending' AND u.role='student' AND be.equipment_id=?
                              AND b.start_time<? AND b.end_time>? ORDER BY b.created_at DESC LIMIT 1""",
                                               (eid, end, start)).fetchone()
                        if one_victim:
                            d.execute("UPDATE bookings SET status='bumped', admin_note=? WHERE id=?",
                                      ("Bị thay thế bởi yêu cầu ưu tiên của giảng viên " + user["full_name"], one_victim["id"]))
                            bumped.append(one_victim["id"])
                            continue
                    raise
        d.commit()
        return bid, bumped
    except Exception:
        d.rollback()
        raise


@app.route("/booking/new", methods=["GET", "POST"])
@roles("student", "lecturer")
def booking_new():
    rooms = q("SELECT * FROM rooms WHERE is_active=1 ORDER BY name")
    equips = q("SELECT *, quantity-broken_qty AS avail FROM equipment WHERE is_active=1 ORDER BY name")
    if request.method == "POST":
        f = request.form
        try:
            room_id = int(f["room_id"]) if f.get("room_id") else None
            start, end = parse_dt(f["date"], f["start"]), parse_dt(f["date"], f["end"])
            equip = []
            for e in equips:
                n = int(f.get(f"eq_{e['id']}") or 0)
                if n > 0:
                    equip.append((e["id"], n))
        except (ValueError, KeyError):
            flash("Dữ liệu chưa hợp lệ, hãy kiểm tra lại ngày giờ và số lượng.", "err")
            return render_template("booking_new.html", rooms=rooms, equips=equips, f=f)
        err = None
        if not room_id and not equip:
            err = "Hãy chọn ít nhất một phòng hoặc một thiết bị."
        elif start >= end:
            err = "Giờ kết thúc phải sau giờ bắt đầu."
        elif start < datetime.now():
            err = "Không thể đặt vào thời điểm đã qua."
        elif start.hour < OPEN_H or end > end.replace(hour=CLOSE_H, minute=0) or end.hour < OPEN_H:
            err = f"Phòng lab mở từ {OPEN_H}:00 đến {CLOSE_H}:00."
        if err:
            flash(err, "err")
            return render_template("booking_new.html", rooms=rooms, equips=equips, f=f)
        try:
            bid, bumped = create_booking(g.user, room_id, start.strftime("%Y-%m-%d %H:%M"),
                                         end.strftime("%Y-%m-%d %H:%M"), f.get("purpose", "").strip(), equip)
        except sqlite3.IntegrityError as e:
            msg = str(e)
            if "ROOM_CONFLICT" in msg:
                flash("Phòng đã có yêu cầu khác trong khung giờ này. Xem lịch tuần để chọn giờ trống.", "err")
            elif "EQUIP_CONFLICT" in msg:
                flash("Một thiết bị không đủ số lượng trong khung giờ này.", "err")
            else:
                flash("Không thể lưu yêu cầu: " + msg, "err")
            return render_template("booking_new.html", rooms=rooms, equips=equips, f=f)
        flash("Đã gửi yêu cầu, đang chờ cán bộ duyệt." +
              (f" Đã thay thế {len(bumped)} yêu cầu chưa duyệt của sinh viên." if bumped else ""), "ok")
        return redirect(url_for("my_bookings"))
    return render_template("booking_new.html", rooms=rooms, equips=equips, f=request.args)


@app.route("/my/bookings")
@roles("student", "lecturer")
def my_bookings():
    rows = q("""SELECT b.*, r.name room,
                (SELECT group_concat(e.name||' ×'||be.quantity, ', ') FROM booking_equipment be
                   JOIN equipment e ON e.id=be.equipment_id WHERE be.booking_id=b.id) equip
                FROM bookings b LEFT JOIN rooms r ON r.id=b.room_id
                WHERE b.user_id=? ORDER BY b.start_time DESC""", (g.user["id"],))
    return render_template("my_bookings.html", rows=rows)


@app.route("/booking/<int:bid>/cancel", methods=["POST"])
@roles("student", "lecturer")
def booking_cancel(bid):
    b = one("SELECT * FROM bookings WHERE id=? AND user_id=?", (bid, g.user["id"]))
    if not b or b["status"] not in ("pending", "approved"):
        abort(404)
    if one("SELECT 1 FROM loans WHERE booking_id=? AND returned_at IS NULL", (bid,)):
        flash("Thiết bị của yêu cầu này đang được mượn, hãy trả trước khi hủy.", "err")
    else:
        db().execute("UPDATE bookings SET status='cancelled' WHERE id=?", (bid,))
        db().commit()
        flash("Đã hủy yêu cầu.", "ok")
    return redirect(url_for("my_bookings"))


@app.route("/admin/bookings")
@roles("admin")
def admin_bookings():
    status = request.args.get("status", "pending")
    sql = """SELECT b.*, u.full_name, u.role, u.group_name, r.name room,
             (SELECT group_concat(e.name||' ×'||be.quantity, ', ') FROM booking_equipment be
                JOIN equipment e ON e.id=be.equipment_id WHERE be.booking_id=b.id) equip
             FROM bookings b JOIN users u ON u.id=b.user_id LEFT JOIN rooms r ON r.id=b.room_id"""
    if status in STATUS_LABEL:
        rows = q(sql + " WHERE b.status=? ORDER BY (u.role='lecturer') DESC, b.start_time", (status,))
    else:
        rows = q(sql + " ORDER BY b.start_time DESC LIMIT 200")
    return render_template("admin_bookings.html", rows=rows, status=status)


@app.route("/admin/booking/<int:bid>/<action>", methods=["POST"])
@roles("admin")
def admin_booking_action(bid, action):
    b = one("SELECT * FROM bookings WHERE id=?", (bid,))
    if not b:
        abort(404)
    new = {"approve": "approved", "reject": "rejected", "done": "done"}.get(action)
    allowed = {"approved": ("pending",), "rejected": ("pending", "approved"), "done": ("approved",)}
    if not new or b["status"] not in allowed[new]:
        flash("Thao tác không áp dụng được với trạng thái hiện tại.", "err")
    else:
        if new == "done" and one("SELECT 1 FROM loans WHERE booking_id=? AND returned_at IS NULL", (bid,)):
            flash("Còn thiết bị chưa trả, chưa thể hoàn tất.", "err")
            return redirect(request.referrer or url_for("admin_bookings"))
        db().execute("UPDATE bookings SET status=?, admin_note=? WHERE id=?",
                     (new, request.form.get("note") or b["admin_note"], bid))
        db().commit()
        flash(f"Đã chuyển yêu cầu #{bid} sang “{STATUS_LABEL[new]}”.", "ok")
    return redirect(request.referrer or url_for("admin_bookings"))

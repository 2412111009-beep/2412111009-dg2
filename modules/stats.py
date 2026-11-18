"""Thống kê tần suất sử dụng phòng và thiết bị."""
from datetime import datetime, timedelta, date
from flask import render_template, request
from core import app, q, roles, WEEKDAYS


@app.route("/admin/stats")
@roles("admin")
def admin_stats():
    try:
        d_to = datetime.strptime(request.args["to"], "%Y-%m-%d").date()
        d_from = datetime.strptime(request.args["from"], "%Y-%m-%d").date()
    except (KeyError, ValueError):
        d_to, d_from = date.today(), date.today() - timedelta(days=29)
    a, b = d_from.strftime("%Y-%m-%d 00:00"), (d_to + timedelta(days=1)).strftime("%Y-%m-%d 00:00")
    rooms = q("""SELECT r.name, COUNT(b.id) cnt,
                 ROUND(COALESCE(SUM((julianday(b.end_time)-julianday(b.start_time))*24),0),1) hours
                 FROM rooms r LEFT JOIN bookings b ON b.room_id=r.id AND b.status IN ('approved','done')
                   AND b.start_time>=? AND b.start_time<? GROUP BY r.id ORDER BY cnt DESC, r.name""", (a, b))
    equips = q("""SELECT e.name, COUNT(b.id) cnt, COALESCE(SUM(be.quantity),0) qty
                  FROM equipment e LEFT JOIN booking_equipment be ON be.equipment_id=e.id
                  LEFT JOIN bookings b ON b.id=be.booking_id AND b.status IN ('approved','done')
                    AND b.start_time>=? AND b.start_time<?
                  GROUP BY e.id ORDER BY cnt DESC, e.name""", (a, b))
    wd = {int(r["w"]): r["c"] for r in q("""SELECT strftime('%w',start_time) w, COUNT(*) c FROM bookings
                 WHERE status IN ('approved','done') AND start_time>=? AND start_time<? GROUP BY w""", (a, b))}
    by_day = [(WEEKDAYS[(i - 1) % 7], wd.get(i % 7, 0)) for i in range(1, 8)]   # Thứ 2 .. CN
    return render_template("admin_stats.html", rooms=rooms, equips=equips, by_day=by_day,
                           d_from=d_from, d_to=d_to,
                           max_room=max([r["cnt"] for r in rooms] + [1]),
                           max_eq=max([e["cnt"] for e in equips] + [1]),
                           max_day=max([c for _, c in by_day] + [1]))

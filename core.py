"""Phần lõi dùng chung: tạo app, tiện ích CSDL, đăng nhập/phân quyền, CSRF, xử lý lỗi.
Chỉ sửa file này khi thật cần và báo cả nhóm (đây là file chung)."""
import os, secrets, hashlib, smtplib, sqlite3, uuid
from datetime import datetime, timedelta, date
from email.message import EmailMessage
from functools import wraps

from flask import (Flask, render_template, request, redirect, url_for, session,
                   flash, g, abort, send_from_directory)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from db import get_db, init_db, DATA_DIR

BASE = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _secret():
    if os.environ.get("SECRET_KEY"):
        return os.environ["SECRET_KEY"]
    p = os.path.join(DATA_DIR, ".secret_key")
    if not os.path.exists(p):
        with open(p, "w") as f:
            f.write(secrets.token_hex(32))
    return open(p).read()


app = Flask(__name__)
app.secret_key = _secret()
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("COOKIE_SECURE") == "1"   # bật khi chạy sau HTTPS

ROLE_LABEL = {"admin": "Quản trị", "lecturer": "Giảng viên", "student": "Sinh viên"}
STATUS_LABEL = {"pending": "Chờ duyệt", "approved": "Đã duyệt", "rejected": "Từ chối",
                "cancelled": "Đã hủy", "bumped": "Bị thay thế", "done": "Hoàn tất"}
COND_LABEL = {"good": "Tốt", "damaged": "Hỏng", "lost": "Mất"}
OPEN_H, CLOSE_H = 7, 21          # giờ mở cửa phòng lab
WEEKDAYS = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "CN"]


def db():
    if "db" not in g:
        g.db = get_db()
    return g.db


@app.teardown_appcontext
def close_db(_):
    d = g.pop("db", None)
    if d:
        d.close()


def q(sql, args=()):
    return db().execute(sql, args).fetchall()


def one(sql, args=()):
    return db().execute(sql, args).fetchone()


@app.before_request
def load_user():
    g.user = None
    uid = session.get("uid")
    if uid:
        u = one("SELECT * FROM users WHERE id=? AND is_active=1", (uid,))
        if u:
            g.user = u
        else:
            session.clear()


@app.before_request
def csrf_protect():
    if request.method == "POST":
        sent, real = request.form.get("csrf", ""), session.get("csrf", "")
        if not real or not secrets.compare_digest(real, sent):
            abort(400, "CSRF token không hợp lệ. Hãy tải lại trang và thử lại.")


@app.context_processor
def inject():
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(16)
    return dict(csrf=session["csrf"], ROLE_LABEL=ROLE_LABEL, STATUS_LABEL=STATUS_LABEL,
                COND_LABEL=COND_LABEL, me=g.get("user"), WEEKDAYS=WEEKDAYS)


def login_required(f):
    @wraps(f)
    def w(*a, **k):
        if not g.user:
            flash("Vui lòng đăng nhập.", "warn")
            return redirect(url_for("login", next=request.path))
        return f(*a, **k)
    return w


def roles(*allowed):
    def deco(f):
        @wraps(f)
        @login_required
        def w(*a, **k):
            if g.user["role"] not in allowed:
                abort(403)
            return f(*a, **k)
        return w
    return deco


def parse_dt(d, t):
    return datetime.strptime(f"{d} {t}", "%Y-%m-%d %H:%M")


def monday_of(d):
    return d - timedelta(days=d.weekday())


@app.errorhandler(403)
def e403(_):
    return render_template("error.html", code=403, msg="Bạn không có quyền vào trang này."), 403


@app.errorhandler(404)
def e404(_):
    return render_template("error.html", code=404, msg="Không tìm thấy trang hoặc dữ liệu."), 404


@app.errorhandler(400)
def e400(e):
    return render_template("error.html", code=400, msg=getattr(e, "description", "Yêu cầu không hợp lệ.")), 400

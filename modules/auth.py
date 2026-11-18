"""Đăng nhập, đăng xuất, đăng ký, quên/đặt lại mật khẩu, hồ sơ cá nhân."""
import os, secrets, hashlib, smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage
from flask import (
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    g)
from werkzeug.security import generate_password_hash, check_password_hash
from core import app, db, one, login_required


@app.route("/")
def index():
    return redirect(url_for("dashboard") if g.user else url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if g.user:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        u = one("SELECT * FROM users WHERE email=?", (email,))
        if not u or not check_password_hash(u["password_hash"], request.form["password"]):
            flash("Email hoặc mật khẩu không đúng.", "err")
        elif not u["is_active"]:
            flash("Tài khoản đang chờ quản trị viên kích hoạt.", "warn")
        else:
            session.clear()
            session["uid"] = u["id"]
            nxt = request.args.get("next", "")
            return redirect(nxt if nxt.startswith("/") and not nxt.startswith("//") else url_for("dashboard"))
    return render_template("login.html")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if g.user:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        f = request.form
        email, name = f["email"].strip().lower(), f["full_name"].strip()
        role = f.get("role", "student")
        if role not in ("student", "lecturer"):
            role = "student"
        if not email or not name:
            flash("Hãy nhập đủ họ tên và email.", "err")
        elif len(f["password"]) < 6:
            flash("Mật khẩu cần tối thiểu 6 ký tự.", "err")
        elif f["password"] != f["password2"]:
            flash("Hai mật khẩu chưa khớp.", "err")
        elif one("SELECT 1 FROM users WHERE email=?", (email,)):
            flash("Email này đã được đăng ký.", "err")
        else:
            active = 1 if role == "student" else 0   # giảng viên phải được admin duyệt
            db().execute(
                "INSERT INTO users(email,password_hash,full_name,phone,role,group_name,is_active) VALUES (?,?,?,?,?,?,?)",
                (email, generate_password_hash(f["password"]), name, f.get("phone", "").strip(),
                 role, f.get("group_name", "").strip() or None, active))
            db().commit()
            flash("Đăng ký thành công. " + ("Bạn có thể đăng nhập ngay." if active else
                  "Tài khoản giảng viên sẽ dùng được sau khi quản trị viên kích hoạt."), "ok")
            return redirect(url_for("login"))
    return render_template("register.html")


def send_reset_mail(to, link):
    host = os.environ.get("SMTP_HOST")
    if not host:
        return False
    msg = EmailMessage()
    msg["Subject"], msg["From"], msg["To"] = "Đặt lại mật khẩu LabBook", os.environ.get("SMTP_FROM", "noreply@lab.local"), to
    msg.set_content(f"Mở liên kết sau trong 30 phút để đặt lại mật khẩu:\n{link}")
    with smtplib.SMTP(host, int(os.environ.get("SMTP_PORT", 587))) as s:
        s.starttls()
        if os.environ.get("SMTP_USER"):
            s.login(os.environ["SMTP_USER"], os.environ.get("SMTP_PASS", ""))
        s.send_message(msg)
    return True


@app.route("/forgot", methods=["GET", "POST"])
def forgot():
    dev_link = None
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        u = one("SELECT * FROM users WHERE email=? AND is_active=1", (email,))
        if u:
            token = secrets.token_urlsafe(32)
            exp = (datetime.now() + timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S")
            db().execute("INSERT INTO password_resets(user_id,token_hash,expires_at) VALUES (?,?,?)",
                         (u["id"], hashlib.sha256(token.encode()).hexdigest(), exp))
            db().commit()
            link = url_for("reset", token=token, _external=True)
            try:
                sent = send_reset_mail(email, link)
            except Exception as e:      # lỗi SMTP không được lộ việc email có tồn tại hay không
                app.logger.error("SMTP lỗi: %s", e)
                sent = False
            if not sent:                # chưa cấu hình SMTP -> chế độ phát triển
                print(f"[DEV] Link đặt lại mật khẩu cho {email}: {link}")
                dev_link = link
        flash("Nếu email tồn tại trong hệ thống, liên kết đặt lại mật khẩu đã được gửi.", "ok")
    return render_template("forgot.html", dev_link=dev_link)


@app.route("/reset/<token>", methods=["GET", "POST"])
def reset(token):
    h = hashlib.sha256(token.encode()).hexdigest()
    r = one("SELECT * FROM password_resets WHERE token_hash=? AND used=0 AND expires_at>?",
            (h, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    if not r:
        flash("Liên kết không hợp lệ hoặc đã hết hạn.", "err")
        return redirect(url_for("forgot"))
    if request.method == "POST":
        if len(request.form["password"]) < 6:
            flash("Mật khẩu cần tối thiểu 6 ký tự.", "err")
        elif request.form["password"] != request.form["password2"]:
            flash("Hai mật khẩu chưa khớp.", "err")
        else:
            db().execute("UPDATE users SET password_hash=? WHERE id=?",
                         (generate_password_hash(request.form["password"]), r["user_id"]))
            db().execute("UPDATE password_resets SET used=1 WHERE user_id=?", (r["user_id"],))
            db().commit()
            flash("Đã đổi mật khẩu. Hãy đăng nhập lại.", "ok")
            return redirect(url_for("login"))
    return render_template("reset.html")


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    if request.method == "POST":
        f = request.form
        if f.get("new_password"):
            if not check_password_hash(g.user["password_hash"], f["old_password"]):
                flash("Mật khẩu hiện tại chưa đúng.", "err")
                return redirect(url_for("profile"))
            if len(f["new_password"]) < 6:
                flash("Mật khẩu mới cần tối thiểu 6 ký tự.", "err")
                return redirect(url_for("profile"))
            db().execute("UPDATE users SET password_hash=? WHERE id=?",
                         (generate_password_hash(f["new_password"]), g.user["id"]))
        db().execute("UPDATE users SET full_name=?, phone=?, group_name=? WHERE id=?",
                     (f["full_name"].strip() or g.user["full_name"], f.get("phone", ""),
                      f.get("group_name") or None, g.user["id"]))
        db().commit()
        flash("Đã lưu hồ sơ.", "ok")
        return redirect(url_for("profile"))
    return render_template("profile.html")

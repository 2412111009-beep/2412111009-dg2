"""Điểm vào của ứng dụng: nạp lần lượt mọi module trong thư mục modules/.
Mỗi thành viên chỉ thêm file trong modules/ của mình, không phải sửa file này.

Khi chạy RIÊNG một phần (chưa có module của người khác), các đường dẫn còn thiếu
được thay bằng trang thông báo "chưa ghép" để menu và liên kết không bị lỗi."""
import importlib, os, pkgutil

import modules
from core import app
from db import get_db, init_db
from flask import render_template

for _m in sorted(pkgutil.iter_modules(modules.__path__), key=lambda x: x.name):
    importlib.import_module(f"modules.{_m.name}")

# endpoint: (đường dẫn, phương thức, thành viên sở hữu) – dùng để dựng trang "chưa ghép" khi chạy riêng từng phần
EXPECTED = {
    'admin_users': ('/admin/users', ['GET', 'POST'], 1),
    'dashboard': ('/dashboard', ['GET'], 1),
    'forgot': ('/forgot', ['GET', 'POST'], 1),
    'index': ('/', ['GET'], 1),
    'login': ('/login', ['GET', 'POST'], 1),
    'logout': ('/logout', ['POST'], 1),
    'profile': ('/profile', ['GET', 'POST'], 1),
    'register': ('/register', ['GET', 'POST'], 1),
    'reset': ('/reset/<token>', ['GET', 'POST'], 1),
    'admin_booking_action': ('/admin/booking/<int:bid>/<action>', ['POST'], 2),
    'admin_bookings': ('/admin/bookings', ['GET'], 2),
    'booking_cancel': ('/booking/<int:bid>/cancel', ['POST'], 2),
    'booking_new': ('/booking/new', ['GET', 'POST'], 2),
    'my_bookings': ('/my/bookings', ['GET'], 2),
    'schedule': ('/schedule', ['GET'], 2),
    'admin_equipment': ('/admin/equipment', ['GET', 'POST'], 3),
    'admin_loans': ('/admin/loans', ['GET'], 3),
    'admin_rooms': ('/admin/rooms', ['GET', 'POST'], 3),
    'admin_stats': ('/admin/stats', ['GET'], 3),
    'damage_list': ('/damage', ['GET'], 3),
    'damage_new': ('/damage/new', ['GET', 'POST'], 3),
    'damage_resolve': ('/admin/damage/<int:did>/resolve', ['POST'], 3),
    'loan_issue': ('/admin/loan/issue', ['POST'], 3),
    'loan_return': ('/admin/loan/<int:lid>/return', ['POST'], 3),
    'uploads': ('/uploads/<path:name>', ['GET'], 3),
}


def _stub(owner):
    def view(**_):
        return render_template("error.html", code=501,
                               msg=f"Chức năng này thuộc phần của Thành viên {owner}, "
                                   "chưa được ghép vào bản đang chạy."), 501
    return view


for _name, (_rule, _methods, _owner) in EXPECTED.items():
    if _name not in app.view_functions:
        app.add_url_rule(_rule, endpoint=_name, view_func=_stub(_owner), methods=_methods)

init_db()

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1", host=os.environ.get("HOST", "127.0.0.1"), port=5000)

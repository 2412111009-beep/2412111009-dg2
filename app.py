"""Điểm vào của bản phần 3: nạp app chính (chỉ đọc) rồi gắn thêm API phần 3."""
from app import app  # app của web chính, không bị sửa
from phan3_api import bp, init_db

init_db()
app.register_blueprint(bp)

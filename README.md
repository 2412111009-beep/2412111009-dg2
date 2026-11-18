# LabBook – Đặt phòng lab & mượn thiết bị (Flask + SQLite)

## Chạy
    pip install -r requirements.txt
    python app.py          # mở http://127.0.0.1:5000

Lần chạy đầu tự tạo `labbook.db` kèm dữ liệu mẫu.

| Vai trò   | Email          | Mật khẩu |
|-----------|----------------|----------|
| Quản trị  | admin@lab.local | admin123 |
| Giảng viên| gv@lab.local    | gv123456 |
| Sinh viên | sv@lab.local    | sv123456 |

Đổi mật khẩu các tài khoản mẫu trước khi dùng thật.

## Quên mật khẩu
Chưa cấu hình SMTP: liên kết đặt lại hiện ngay trên trang và in ra console (chế độ phát triển).
Muốn gửi email thật, đặt biến môi trường: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, SMTP_FROM.

## Cấu trúc
- `core.py` tạo app, CSRF, phân quyền; `app.py` nạp các module
- `db.py` schema 8 bảng + trigger chống trùng lịch (ROOM_CONFLICT, EQUIP_CONFLICT)
- `modules/` auth, dashboard, booking, loans, damage, catalog, stats (mỗi file tự đăng ký route)
- `templates/` giao diện (mỗi vai trò có dashboard và menu riêng), `static/style.css`
- `docs/PHAN_CONG.md` phân công 3 thành viên và quy trình Git

## Docker
    docker compose up -d --build     # mở http://localhost:5000
    docker compose logs -f           # xem log (liên kết quên mật khẩu in ở đây nếu chưa có SMTP)
    docker compose down              # dừng, DỮ LIỆU VẪN GIỮ trong volume labbook_data
    docker compose down -v           # dừng và XÓA dữ liệu

CSDL, ảnh báo hỏng và khóa bí mật nằm trong volume `labbook_data` (thư mục /data).
Sao lưu: `docker run --rm -v labbook_data:/data -v $PWD:/b alpine tar czf /b/labbook-backup.tgz -C /data .`
Đặt `SECRET_KEY` và `COOKIE_SECURE=1` trong file `.env` khi triển khai sau HTTPS.

### Ba lớp Docker (mỗi thành viên một lớp)
| Lớp | File | Chạy |
|---|---|---|
| TV1 – ứng dụng | `Dockerfile`, `docker-compose.yml` | `docker compose up -d --build` |
| TV2 – xem CSDL | `docker-compose.db.yml`, `docker/dbviewer/` | thêm `-f docker-compose.db.yml` (mở http://localhost:8080, chỉ đọc) |
| TV3 – sao lưu | `docker-compose.backup.yml`, `docker/backup/` | thêm `-f docker-compose.backup.yml` (ghi vào `./backups`) |

Chạy đủ cả ba:

    docker compose -f docker-compose.yml -f docker-compose.db.yml -f docker-compose.backup.yml up -d --build

Hai file bổ sung không chạy riêng được, luôn đi kèm `docker-compose.yml`.
Khôi phục CSDL: dừng ứng dụng, chép `backups/labbook-<thời gian>.db` thành `labbook.db` trong volume `labbook_data`.

## Chạy riêng từng phần
Thiếu module của người khác vẫn chạy được: các đường dẫn còn thiếu hiện trang "chưa ghép" (mã 501). Xem `docs/PHAN_CONG.md`.

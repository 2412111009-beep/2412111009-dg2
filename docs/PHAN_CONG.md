# Phân công 3 thành viên – LabBook

Mỗi người sở hữu một nhóm file riêng nên **không bao giờ sửa trùng file của nhau** (hạn chế conflict khi push).
`app.py` tự nạp mọi file trong `modules/`, nên thêm chức năng chỉ cần thêm file của mình.

| | Thành viên 1 | Thành viên 2 | Thành viên 3 |
|---|---|---|---|
| **Vai trò** | Nền tảng, tài khoản, giao diện chung, Docker | CSDL và đặt lịch | Mượn – trả, báo hỏng, danh mục, thống kê |
| **Nhánh git** | `feature/core-auth-docker` | `feature/database-booking` | `feature/loans-damage-stats` |

## Thành viên 1 – Nền tảng, tài khoản, Docker
- `core.py` (tạo app, CSRF, phân quyền, xử lý lỗi), `app.py`, `modules/__init__.py`
- `modules/auth.py`: đăng nhập, đăng xuất, đăng ký, quên và đặt lại mật khẩu, hồ sơ
- `modules/dashboard.py`: tổng quan 3 vai trò, quản lý tài khoản (kích hoạt giảng viên, đổi vai trò)
- Giao diện chung: `static/style.css`, `templates/` gồm `base, _flash, _m, _auth, login, register, forgot, reset, error, profile, dash_admin, dash_lecturer, dash_student, admin_users`
- Docker lớp 1 (ứng dụng): `Dockerfile`, `docker-compose.yml` (gunicorn, volume `labbook_data`, healthcheck), `.dockerignore`, `.env.example`
- File chung: `requirements.txt`, `README.md`, `.gitignore`, `docs/`
- Ý chính khi trình bày: băm mật khẩu, token đặt lại mật khẩu (lưu hash, hết hạn 30 phút, dùng 1 lần), chống CSRF, phân quyền theo vai trò, đóng gói Docker với volume giữ dữ liệu.

## Thành viên 2 – CSDL và đặt lịch
- `db.py`: schema 8 bảng, **trigger chống trùng lịch ở mức CSDL** (phòng, số lượng thiết bị), dữ liệu mẫu
- `modules/booking.py`: lịch tuần, đặt phòng/thiết bị, **ưu tiên giảng viên thay yêu cầu chưa duyệt của sinh viên**, hủy yêu cầu, quản trị duyệt/từ chối/hoàn tất
- `templates/`: `schedule, booking_new, my_bookings, admin_bookings`
- Docker lớp 2 (xem CSDL): `docker-compose.db.yml`, `docker/dbviewer/Dockerfile` – trình xem SQLite chỉ đọc ở http://localhost:8080 để cho thấy bảng và trigger
- Ý chính khi trình bày: vì sao chặn ở CSDL chứ không chỉ ở code, cách trigger kiểm tra chồng giờ (`start < end2 AND end > start2`), luồng giảng viên thay thế sinh viên trong một giao dịch, dựng bảng tuần.

## Thành viên 3 – Mượn trả, báo hỏng, danh mục, thống kê
- `modules/loans.py`: giao thiết bị, nhận trả và ghi nhận tình trạng (Tốt/Hỏng/Mất, tự trừ số lượng khả dụng)
- `modules/damage.py`: báo hỏng kèm ảnh (kiểm tra đuôi file, tên file ngẫu nhiên), xử lý báo hỏng
- `modules/catalog.py`: quản lý phòng và thiết bị
- `modules/stats.py`: thống kê tần suất sử dụng phòng, thiết bị, theo thứ trong tuần
- `templates/`: `admin_loans, damage_new, damage_list, admin_rooms, admin_equipment, admin_stats`
- Docker lớp 3 (sao lưu): `docker-compose.backup.yml`, `docker/backup/` (`Dockerfile`, `backup.py`) – tự sao lưu CSDL bằng API backup của SQLite và ảnh báo hỏng vào `./backups`, giữ N bản mới nhất; thư mục `backups/.gitkeep`
- Ý chính khi trình bày: vòng đời mượn trả, liên kết báo hỏng với lượt mượn, truy vấn thống kê (`GROUP BY`, `julianday`).

## Chạy Docker (ba lớp xếp chồng)
```bash
docker compose up -d --build                                   # TV1: ứng dụng
docker compose -f docker-compose.yml -f docker-compose.db.yml up -d --build      # + TV2: xem CSDL
docker compose -f docker-compose.yml -f docker-compose.backup.yml up -d --build  # + TV3: sao lưu
# đủ cả ba:
docker compose -f docker-compose.yml -f docker-compose.db.yml -f docker-compose.backup.yml up -d --build
```

## Chạy riêng từng phần
Mỗi người dùng gói `chay-rieng-phan-N.zip` (đã gồm phần nền tảng cần để đăng nhập, cộng phần của mình):
```bash
python -m venv .venv && .venv\\Scripts\\activate     # Windows (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
python app.py                                  # http://127.0.0.1:5000
# hoặc: docker compose up -d --build           # http://localhost:5000
```
Khi chạy riêng, đường dẫn của phần khác hiện thông báo "chưa ghép" (mã 501). Gói chạy riêng chỉ để chạy thử,
**khi commit chỉ thêm file thuộc phần của mình** (danh sách ở trên); các file nền tảng đã có sẵn trong repo từ thành viên 1.

## Quy trình Git gợi ý
```bash
# Thành viên 1 tạo repo trên GitHub (trống), rồi:
git init && git add . && git commit -m "feat: nền tảng, tài khoản, docker"
git branch -M main && git remote add origin <URL> && git push -u origin main

# Thành viên 2 và 3 (sau khi clone):
git checkout -b feature/database-booking        # hoặc feature/loans-damage-stats
# chép file phần của mình vào đúng đường dẫn rồi:
git add <các file của mình>
git commit -m "feat(booking): lịch tuần và ưu tiên giảng viên"
git push -u origin feature/database-booking
# mở Pull Request vào main, một người khác trong nhóm review rồi merge
```
- Commit nhỏ, đặt tên dạng `feat(phạm-vi): mô tả`, `fix(...)`, `docs(...)` để lịch sử có thể nhìn ra đóng góp từng người.
- Thứ tự merge: phần 1, rồi phần 2, rồi phần 3.
- Mỗi người có thể **chạy riêng phần của mình** (xem mục dưới). Trang thuộc phần người khác sẽ hiện thông báo "chưa ghép" thay vì báo lỗi.
- Phần nào cần sửa file của người khác thì nhắn họ sửa, hoặc mở Issue.

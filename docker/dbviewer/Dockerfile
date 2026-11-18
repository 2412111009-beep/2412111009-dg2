# Dịch vụ xem CSDL SQLite trên trình duyệt (chỉ đọc) – dùng khi phát triển/bảo vệ đồ án
FROM python:3.12-slim
RUN pip install --no-cache-dir sqlite-web
EXPOSE 8080
CMD ["sqlite_web", "/data/labbook.db", "--host", "0.0.0.0", "--port", "8080", "--read-only", "--no-browser"]

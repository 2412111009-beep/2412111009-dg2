"""Sao lưu định kỳ CSDL (an toàn khi ứng dụng đang ghi) và ảnh báo hỏng. Giữ N bản mới nhất."""
import glob, os, sqlite3, tarfile, time
from datetime import datetime

DATA = os.environ.get("DATA_DIR", "/data")
OUT = os.environ.get("BACKUP_DIR", "/backups")
INTERVAL = int(os.environ.get("BACKUP_INTERVAL", "3600"))   # giây
KEEP = int(os.environ.get("BACKUP_KEEP", "24"))
ONCE = os.environ.get("BACKUP_ONCE") == "1"


def backup_once():
    os.makedirs(OUT, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    src_path = os.path.join(DATA, "labbook.db")
    if not os.path.exists(src_path):
        print("Chưa có labbook.db, bỏ qua lượt này", flush=True)
        return
    db_out = os.path.join(OUT, f"labbook-{stamp}.db")
    src = sqlite3.connect(f"file:{src_path}?mode=ro", uri=True)
    dst = sqlite3.connect(db_out)
    with dst:
        src.backup(dst)           # API sao lưu của SQLite: bản chụp nhất quán
    dst.close(); src.close()
    up = os.path.join(DATA, "uploads")
    if os.path.isdir(up) and os.listdir(up):
        with tarfile.open(os.path.join(OUT, f"uploads-{stamp}.tgz"), "w:gz") as t:
            t.add(up, arcname="uploads")
    for pattern in ("labbook-*.db", "uploads-*.tgz"):
        for old in sorted(glob.glob(os.path.join(OUT, pattern)))[:-KEEP]:
            os.remove(old)
    print(f"[{stamp}] đã sao lưu", flush=True)


if __name__ == "__main__":
    while True:
        try:
            backup_once()
        except Exception as e:     # lỗi tạm thời không làm dừng dịch vụ
            print("Lỗi sao lưu:", e, flush=True)
        if ONCE:
            break
        time.sleep(INTERVAL)

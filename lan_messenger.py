#!/usr/bin/env python3
"""
LAN Messenger v3
Kurulum: pip install pystray pillow
Her bilgisayarda aynı dosyayı çalıştır. Sunucu gerekmez.
Geçmiş : %USERPROFILE%\.lan_messenger\<kullanici>.db
Dosyalar: %USERPROFILE%\Downloads\LAN_Messenger\
"""

import tkinter as tk
from tkinter import messagebox, filedialog
import socket, threading, json, sqlite3, datetime
import os, struct, time, mimetypes, sys, winreg

try:
    import pystray
    from PIL import Image as PILImage, ImageDraw, ImageTk
    HAS_EXTRAS = True
except ImportError:
    HAS_EXTRAS = False

DISCOVERY_PORT = 55100
MESSAGE_PORT   = 55101
BROADCAST_INT  = 5
MAX_FILE_BYTES = 100 * 1024 * 1024
SAVE_DIR       = os.path.join(os.path.expanduser("~"), "Downloads", "LAN_Messenger")
IMAGE_EXTS     = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff"}

STATUS_ONLINE = "online"
STATUS_BUSY   = "busy"
STATUS_AWAY   = "away"

STATUS_DOT   = {STATUS_ONLINE: "🟢", STATUS_BUSY: "🟡", STATUS_AWAY: "🟠"}
STATUS_LABEL = {STATUS_ONLINE: "Çevrimiçi", STATUS_BUSY: "Meşgul", STATUS_AWAY: "Uzakta"}
STATUS_COLOR = {STATUS_ONLINE: "#003399",   STATUS_BUSY: "#CC6600",  STATUS_AWAY: "#666666"}


# ---------------------------------------------------------------------------
# Windows başlangıç kaydı
# ---------------------------------------------------------------------------

def _startup_value():
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    pythonw = sys.executable.replace("python.exe", "pythonw.exe")
    script  = os.path.abspath(__file__)
    return f'"{pythonw}" "{script}"'

def add_to_startup():
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_READ | winreg.KEY_WRITE
        )
        winreg.SetValueEx(key, "LAN Messenger", 0, winreg.REG_SZ, _startup_value())
        winreg.CloseKey(key)
    except Exception:
        pass

def is_in_startup():
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_READ
        )
        winreg.QueryValueEx(key, "LAN Messenger")
        winreg.CloseKey(key)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Ağ servisi
# ---------------------------------------------------------------------------

class NetworkService:
    def __init__(self, username, local_ip, on_peer_found, on_peer_lost, on_message, get_status):
        self.username      = username
        self.local_ip      = local_ip
        self.on_peer_found = on_peer_found
        self.on_peer_lost  = on_peer_lost
        self.on_message    = on_message
        self.get_status    = get_status   # callable → kendi anlık durumu döner
        self.running       = False

    def start(self):
        self.running = True
        for fn in (self._broadcaster, self._discovery_listener, self._message_server):
            threading.Thread(target=fn, daemon=True).start()

    def stop(self):
        self.running = False
        self._udp_broadcast({"type": "bye", "username": self.username, "ip": self.local_ip})

    def broadcast_status(self):
        """Durum değişince anında broadcast gönder."""
        self._udp_broadcast({
            "type": "hello",
            "username": self.username,
            "ip": self.local_ip,
            "status": self.get_status(),
        })

    # UDP -----------------------------------------------------------------

    def _udp_broadcast(self, data):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s.sendto(json.dumps(data).encode(), ("255.255.255.255", DISCOVERY_PORT))
            s.close()
        except Exception:
            pass

    def _broadcaster(self):
        while self.running:
            self._udp_broadcast({
                "type": "hello",
                "username": self.username,
                "ip": self.local_ip,
                "status": self.get_status(),
            })
            time.sleep(BROADCAST_INT)

    def _discovery_listener(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("", DISCOVERY_PORT))
        except OSError:
            return
        s.settimeout(1.0)
        while self.running:
            try:
                data, addr = s.recvfrom(1024)
                msg    = json.loads(data.decode())
                ip     = msg.get("ip", addr[0])
                name   = msg.get("username", ip)
                status = msg.get("status", STATUS_ONLINE)
                if ip == self.local_ip:
                    continue
                if msg["type"] == "hello":
                    self.on_peer_found(ip, name, status)
                elif msg["type"] == "bye":
                    self.on_peer_lost(ip)
            except socket.timeout:
                pass
            except Exception:
                pass
        s.close()

    # TCP -----------------------------------------------------------------

    def _message_server(self):
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            srv.bind(("", MESSAGE_PORT))
        except OSError:
            return
        srv.listen(5)
        srv.settimeout(1.0)
        while self.running:
            try:
                conn, addr = srv.accept()
                threading.Thread(
                    target=self._handle_conn, args=(conn, addr[0]), daemon=True
                ).start()
            except socket.timeout:
                pass
        srv.close()

    def _handle_conn(self, conn, sender_ip):
        try:
            raw = self._recv_n(conn, 4)
            if not raw:
                return
            hlen = struct.unpack(">I", raw)[0]
            hdr  = json.loads(self._recv_n(conn, hlen).decode())
            if hdr["type"] == "file":
                hdr["raw_data"] = self._recv_n(conn, hdr["file_size"]) or b""
            self.on_message(sender_ip, hdr)
        except Exception:
            pass
        finally:
            conn.close()

    @staticmethod
    def _recv_n(conn, n):
        if n == 0:
            return b""
        buf = b""
        while len(buf) < n:
            chunk = conn.recv(min(65536, n - len(buf)))
            if not chunk:
                return buf if buf else None
            buf += chunk
        return buf

    def _tcp_send(self, ip, header: dict, body: bytes = b""):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(30)
            s.connect((ip, MESSAGE_PORT))
            h = json.dumps(header).encode()
            s.sendall(struct.pack(">I", len(h)) + h + body)
            s.close()
            return True
        except Exception:
            return False

    def send_text(self, ip, content):
        return self._tcp_send(ip, {"type": "text", "content": content})

    def send_file(self, ip, filepath):
        size = os.path.getsize(filepath)
        if size > MAX_FILE_BYTES:
            return False, "Dosya 100 MB üzerinde."
        filename = os.path.basename(filepath)
        mime, _  = mimetypes.guess_type(filepath)
        header   = {"type": "file", "filename": filename,
                    "file_size": size, "mime": mime or "application/octet-stream"}
        with open(filepath, "rb") as f:
            data = f.read()
        return self._tcp_send(ip, header, data), None


# ---------------------------------------------------------------------------
# Yerel geçmiş
# ---------------------------------------------------------------------------

class MessageDB:
    def __init__(self, username):
        db_dir = os.path.join(os.path.expanduser("~"), ".lan_messenger")
        os.makedirs(db_dir, exist_ok=True)
        safe = "".join(c for c in username if c.isalnum() or c in "_-")
        self.path = os.path.join(db_dir, f"{safe}.db")
        self._init()

    def _init(self):
        with sqlite3.connect(self.path) as c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    peer_ip    TEXT NOT NULL,
                    peer_name  TEXT NOT NULL,
                    direction  TEXT NOT NULL,
                    msg_type   TEXT NOT NULL DEFAULT 'text',
                    content    TEXT,
                    filename   TEXT,
                    saved_path TEXT,
                    ts         TEXT NOT NULL
                )
            """)

    def _now(self):
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def save_text(self, peer_ip, peer_name, direction, content):
        ts = self._now()
        with sqlite3.connect(self.path) as c:
            c.execute(
                "INSERT INTO messages (peer_ip,peer_name,direction,msg_type,content,ts)"
                " VALUES (?,?,?,?,?,?)",
                (peer_ip, peer_name, direction, "text", content, ts)
            )
        return ts

    def save_file(self, peer_ip, peer_name, direction, filename, saved_path):
        ts = self._now()
        with sqlite3.connect(self.path) as c:
            c.execute(
                "INSERT INTO messages (peer_ip,peer_name,direction,msg_type,filename,saved_path,ts)"
                " VALUES (?,?,?,?,?,?,?)",
                (peer_ip, peer_name, direction, "file", filename, saved_path, ts)
            )
        return ts

    def load(self, peer_ip, limit=200):
        with sqlite3.connect(self.path) as c:
            cur = c.execute(
                "SELECT direction,peer_name,msg_type,content,filename,saved_path,ts"
                " FROM messages WHERE peer_ip=? ORDER BY id DESC LIMIT ?",
                (peer_ip, limit)
            )
            return list(reversed(cur.fetchall()))


# ---------------------------------------------------------------------------
# Sohbet penceresi
# ---------------------------------------------------------------------------

class ChatWindow:
    def __init__(self, parent, username, peer_ip, peer_name, db, network, on_close):
        self.username  = username
        self.peer_ip   = peer_ip
        self.peer_name = peer_name
        self.db        = db
        self.network   = network
        self._images   = []

        self.win = tk.Toplevel(parent)
        self.win.title(f"Sohbet — {peer_name}")
        self.win.geometry("520x580")
        self.win.configure(bg="#DDE8FF")
        self.win.protocol("WM_DELETE_WINDOW", lambda: on_close(peer_ip))
        self._build()
        self._load_history()

    def _build(self):
        bar = tk.Frame(self.win, bg="#003399", height=46)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        tk.Label(bar, text=f"💬  {self.peer_name}", bg="#003399", fg="white",
                 font=("Tahoma", 12, "bold")).pack(side="left", padx=12, pady=8)
        tk.Label(bar, text=self.peer_ip, bg="#003399", fg="#8899DD",
                 font=("Tahoma", 8)).pack(side="right", padx=10)

        chat_frame = tk.Frame(self.win)
        chat_frame.pack(fill="both", expand=True, padx=6, pady=6)
        sb = tk.Scrollbar(chat_frame, orient="vertical")
        sb.pack(side="right", fill="y")
        self.chat = tk.Text(
            chat_frame, wrap="word", bg="#FFFFFF", fg="#000033",
            font=("Tahoma", 10), state="disabled", relief="flat",
            yscrollcommand=sb.set, cursor="arrow",
            borderwidth=1, highlightthickness=1, highlightbackground="#AABBFF"
        )
        self.chat.pack(side="left", fill="both", expand=True)
        sb.config(command=self.chat.yview)
        self.chat.tag_config("my_name",   foreground="#CC0000", font=("Tahoma", 10, "bold"))
        self.chat.tag_config("my_msg",    foreground="#000033", font=("Tahoma", 10))
        self.chat.tag_config("peer_name", foreground="#0044CC", font=("Tahoma", 10, "bold"))
        self.chat.tag_config("peer_msg",  foreground="#000033", font=("Tahoma", 10))

        bottom = tk.Frame(self.win, bg="#DDE8FF")
        bottom.pack(fill="x", padx=6, pady=(0, 6))
        tk.Button(bottom, text="📎", command=self._pick_file,
                  bg="#DDE8FF", fg="#003399", font=("Arial", 15),
                  relief="flat", cursor="hand2", bd=0, padx=4).pack(side="left")
        self.input_box = tk.Text(
            bottom, height=3, font=("Tahoma", 10), relief="flat",
            bd=1, bg="white", wrap="word",
            highlightthickness=1, highlightbackground="#AABBFF"
        )
        self.input_box.pack(side="left", fill="x", expand=True, padx=(3, 5))
        self.input_box.bind("<Return>", self._on_enter)
        self.input_box.focus()
        tk.Button(bottom, text="Gönder", command=self._send_text,
                  bg="#003399", fg="white", font=("Tahoma", 10),
                  relief="flat", padx=14, cursor="hand2",
                  activebackground="#0044CC").pack(side="right", fill="y")

    def _on_enter(self, e):
        if e.state & 0x1:
            return
        self._send_text()
        return "break"

    def _load_history(self):
        for row in self.db.load(self.peer_ip):
            direction, name, msg_type, content, filename, saved_path, ts = row
            is_me       = (direction == "sent")
            actual_name = self.username if is_me else name
            if msg_type == "text":
                self._append_text(actual_name, content or "", ts, is_me)
            else:
                self._append_file(actual_name, filename or "", saved_path, ts, is_me)

    def _ts_str(self, ts):
        try:
            return datetime.datetime.strptime(ts, "%Y-%m-%d %H:%M:%S").strftime("%H:%M")
        except Exception:
            return ts[-5:] if len(ts) >= 5 else ts

    def _append_text(self, name, content, ts, is_me):
        self.chat.configure(state="normal")
        nt = "my_name"  if is_me else "peer_name"
        mt = "my_msg"   if is_me else "peer_msg"
        self.chat.insert("end", f"{name} ({self._ts_str(ts)}):\n", nt)
        self.chat.insert("end", f"{content}\n\n", mt)
        self.chat.configure(state="disabled")
        self.chat.see("end")

    def _append_file(self, name, filename, saved_path, ts, is_me):
        self.chat.configure(state="normal")
        nt = "my_name" if is_me else "peer_name"
        self.chat.insert("end", f"{name} ({self._ts_str(ts)}):\n", nt)
        ext = os.path.splitext(filename)[1].lower()
        if HAS_EXTRAS and ext in IMAGE_EXTS and saved_path and os.path.exists(saved_path):
            try:
                img = PILImage.open(saved_path)
                img.thumbnail((260, 200))
                photo = ImageTk.PhotoImage(img)
                self._images.append(photo)
                lbl = tk.Label(self.chat, image=photo, bg="white", cursor="hand2")
                lbl.bind("<Button-1>", lambda e, p=saved_path: self._open_file(p))
                self.chat.window_create("end", window=lbl, padx=2, pady=2)
                self.chat.insert("end", "\n")
            except Exception:
                pass
        card = tk.Frame(self.chat, bg="#E8F0FF", bd=1, relief="solid")
        icon = ("🖼️" if ext in IMAGE_EXTS else
                "🎵" if ext in {".mp3", ".wav", ".ogg"} else
                "🎬" if ext in {".mp4", ".mkv", ".avi"} else "📄")
        tk.Label(card, text=f"  {icon}  {filename}", bg="#E8F0FF",
                 fg="#000033", font=("Tahoma", 9), anchor="w"
                 ).pack(side="left", padx=6, pady=5, fill="x", expand=True)
        if saved_path and os.path.exists(saved_path):
            tk.Button(card, text="Aç", command=lambda p=saved_path: self._open_file(p),
                      bg="#003399", fg="white", font=("Tahoma", 8),
                      relief="flat", padx=8, cursor="hand2").pack(side="right", padx=5, pady=3)
        self.chat.window_create("end", window=card, padx=2, pady=2)
        self.chat.insert("end", "\n\n")
        self.chat.configure(state="disabled")
        self.chat.see("end")

    def _open_file(self, path):
        try:
            os.startfile(path)
        except Exception:
            messagebox.showerror("Hata", f"Dosya açılamadı:\n{path}", parent=self.win)

    def _send_text(self):
        content = self.input_box.get("1.0", "end-1c").strip()
        if not content:
            return
        if self.network.send_text(self.peer_ip, content):
            ts = self.db.save_text(self.peer_ip, self.peer_name, "sent", content)
            self._append_text(self.username, content, ts, is_me=True)
            self.input_box.delete("1.0", "end")
        else:
            messagebox.showerror("Hata", f"{self.peer_name} adresine ulaşılamadı.", parent=self.win)

    def _pick_file(self):
        path = filedialog.askopenfilename(parent=self.win, title="Dosya seç",
                                          filetypes=[("Tüm dosyalar", "*.*")])
        if not path:
            return
        if os.path.getsize(path) > MAX_FILE_BYTES:
            messagebox.showwarning("Uyarı", "Dosya 100 MB üzerinde.", parent=self.win)
            return
        self.win.config(cursor="wait")
        threading.Thread(target=self._do_send_file, args=(path,), daemon=True).start()

    def _do_send_file(self, path):
        ok, err = self.network.send_file(self.peer_ip, path)
        self.win.after(0, lambda: self._on_file_sent(path, ok, err))

    def _on_file_sent(self, path, ok, err):
        self.win.config(cursor="")
        if ok:
            filename = os.path.basename(path)
            ts = self.db.save_file(self.peer_ip, self.peer_name, "sent", filename, path)
            self._append_file(self.username, filename, path, ts, is_me=True)
        else:
            messagebox.showerror("Hata", err or "Dosya gönderilemedi.", parent=self.win)

    def receive_text(self, content):
        ts = self.db.save_text(self.peer_ip, self.peer_name, "received", content)
        self._append_text(self.peer_name, content, ts, is_me=False)
        self.win.bell()
        self.win.lift()

    def receive_file(self, filename, raw_data):
        os.makedirs(SAVE_DIR, exist_ok=True)
        dest = os.path.join(SAVE_DIR, filename)
        base, ext = os.path.splitext(filename)
        counter = 1
        while os.path.exists(dest):
            dest = os.path.join(SAVE_DIR, f"{base}_{counter}{ext}")
            counter += 1
        with open(dest, "wb") as f:
            f.write(raw_data)
        ts = self.db.save_file(self.peer_ip, self.peer_name, "received", filename, dest)
        self._append_file(self.peer_name, filename, dest, ts, is_me=False)
        self.win.bell()
        self.win.lift()

    def focus(self):
        self.win.lift()
        self.win.focus_force()

    def exists(self):
        try:
            return bool(self.win.winfo_exists())
        except Exception:
            return False


# ---------------------------------------------------------------------------
# Sistem tepsisi
# ---------------------------------------------------------------------------

class TrayManager:
    def __init__(self, app):
        self.app  = app
        self.icon = None
        if not HAS_EXTRAS:
            return
        self._setup()

    def _make_icon(self, status=STATUS_ONLINE):
        color = STATUS_COLOR.get(status, "#003399")
        img   = PILImage.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw  = ImageDraw.Draw(img)
        draw.rounded_rectangle([3, 3, 61, 46], radius=10, fill=color)
        draw.polygon([(14, 42), (5, 58), (27, 42)], fill=color)
        for cx in (19, 32, 45):
            draw.ellipse([cx - 5, 18, cx + 5, 28], fill="white")
        return img

    def _setup(self):
        menu = pystray.Menu(
            pystray.MenuItem(
                "Durum",
                pystray.Menu(
                    pystray.MenuItem("🟢 Çevrimiçi", lambda i, it: self.app.root.after(0, lambda: self.app.set_status(STATUS_ONLINE))),
                    pystray.MenuItem("🟡 Meşgul",    lambda i, it: self.app.root.after(0, lambda: self.app.set_status(STATUS_BUSY))),
                    pystray.MenuItem("🟠 Uzakta",    lambda i, it: self.app.root.after(0, lambda: self.app.set_status(STATUS_AWAY))),
                )
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Göster / Gizle", lambda i, it: self.app.root.after(0, self.app.toggle_window), default=True),
        )
        self.icon = pystray.Icon("lan_messenger", self._make_icon(), "LAN Messenger", menu)
        threading.Thread(target=self.icon.run, daemon=True).start()

    def update_icon(self, status):
        if self.icon:
            try:
                self.icon.icon = self._make_icon(status)
            except Exception:
                pass

    def stop(self):
        if self.icon:
            try:
                self.icon.stop()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Ana uygulama
# ---------------------------------------------------------------------------

class LANMessengerApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()

        self.peers          = {}              # {ip: name}
        self.peer_statuses  = {}              # {ip: status}
        self.chat_windows   = {}
        self.username       = None
        self.own_status     = STATUS_ONLINE
        self.db             = None
        self.network        = None
        self.tray           = None
        self._win_visible   = True

        self._show_login()
        if self.username:
            self._start_main()
        self.root.mainloop()

    @staticmethod
    def _local_ip():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    # -- giriş ---------------------------------------------------------------

    def _show_login(self):
        win = tk.Toplevel(self.root)
        win.title("LAN Messenger")
        win.geometry("320x215")
        win.configure(bg="#003399")
        win.resizable(False, False)
        win.protocol("WM_DELETE_WINDOW", self.root.destroy)
        win.update_idletasks()
        sx, sy = win.winfo_screenwidth(), win.winfo_screenheight()
        win.geometry(f"320x215+{(sx-320)//2}+{(sy-215)//2}")

        tk.Label(win, text="💬 LAN Messenger", bg="#003399", fg="white",
                 font=("Tahoma", 16, "bold")).pack(pady=(28, 4))
        tk.Label(win, text="Yerel ağ  •  sunucu yok  •  dosya paylaşımı",
                 bg="#003399", fg="#8899DD", font=("Tahoma", 8)).pack()

        row = tk.Frame(win, bg="#003399")
        row.pack(pady=18)
        tk.Label(row, text="Adınız:", bg="#003399", fg="white",
                 font=("Tahoma", 10)).grid(row=0, column=0, sticky="e", padx=6)
        name_var = tk.StringVar()
        entry = tk.Entry(row, textvariable=name_var, font=("Tahoma", 11), width=16)
        entry.grid(row=0, column=1, padx=6)
        entry.focus()

        def do_login():
            name = name_var.get().strip()
            if not name:
                messagebox.showwarning("Uyarı", "Ad girin.", parent=win)
                return
            self.username = name
            win.destroy()

        entry.bind("<Return>", lambda e: do_login())
        tk.Button(win, text="Giriş Yap", command=do_login,
                  bg="#6699FF", fg="white", font=("Tahoma", 10, "bold"),
                  relief="flat", padx=22, pady=6, cursor="hand2",
                  activebackground="#0044CC").pack(pady=2)

        win.grab_set()
        win.wait_window()

    # -- başlatma ------------------------------------------------------------

    def _start_main(self):
        self.local_ip = self._local_ip()
        self.db       = MessageDB(self.username)
        self.network  = NetworkService(
            username      = self.username,
            local_ip      = self.local_ip,
            on_peer_found = self._on_peer_found,
            on_peer_lost  = self._on_peer_lost,
            on_message    = self._on_message,
            get_status    = lambda: self.own_status,
        )
        self.network.start()
        self.tray = TrayManager(self)

        # Windows başlangıcına ekle (bir kez)
        if not is_in_startup():
            add_to_startup()

        self._build_main()
        self.root.deiconify()

    # -- ana pencere ---------------------------------------------------------

    def _build_main(self):
        self.root.title(f"LAN Messenger — {self.username}")
        self.root.geometry("255x460")
        self.root.configure(bg="#003399")
        self.root.resizable(False, True)
        # X → kapanmaz, meşgule geçer
        self.root.protocol("WM_DELETE_WINDOW", self._on_close_button)

        # Profil başlığı
        header = tk.Frame(self.root, bg="#002277")
        header.pack(fill="x")

        self._status_btn = tk.Button(
            header, text=STATUS_DOT[self.own_status],
            bg="#002277", relief="flat", cursor="hand2",
            font=("Arial", 15), bd=0,
            command=self._show_status_menu
        )
        self._status_btn.pack(side="left", padx=(8, 2), pady=8)
        tk.Label(header, text=self.username, bg="#002277", fg="white",
                 font=("Tahoma", 12, "bold")).pack(side="left", pady=10)
        tk.Label(header, text=f"({self.local_ip})", bg="#002277", fg="#6677AA",
                 font=("Tahoma", 8)).pack(side="right", padx=8)

        tk.Frame(self.root, bg="#0055CC", height=2).pack(fill="x")

        bar = tk.Frame(self.root, bg="#003399")
        bar.pack(fill="x", padx=8, pady=(8, 3))
        tk.Label(bar, text="KİŞİLER", bg="#003399", fg="#AABBFF",
                 font=("Tahoma", 8, "bold")).pack(side="left")
        self._count_lbl = tk.Label(bar, text="(bekleniyor...)",
                                    bg="#003399", fg="#6677AA", font=("Tahoma", 8))
        self._count_lbl.pack(side="right")

        lf = tk.Frame(self.root, bg="#0033AA", relief="flat", bd=1)
        lf.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self._listbox = tk.Listbox(
            lf, bg="#0033AA", fg="white",
            selectbackground="#0055FF", selectforeground="white",
            font=("Tahoma", 11), relief="flat", bd=0,
            cursor="hand2", activestyle="none"
        )
        self._listbox.pack(fill="both", expand=True, padx=2, pady=2)
        self._listbox.bind("<Double-Button-1>", self._open_from_list)

        self._status_lbl = tk.Label(
            self.root, text="Ağ taranıyor...", bg="#002277",
            fg="#AABBFF", font=("Tahoma", 8), anchor="w"
        )
        self._status_lbl.pack(fill="x", side="bottom")

    # -- X butonu davranışı --------------------------------------------------

    def _on_close_button(self):
        """X'e basınca kapanmaz — durumu Meşgul yapar ve gizlenir."""
        self.set_status(STATUS_BUSY)
        self.root.withdraw()
        self._win_visible = False

    # -- durum yönetimi ------------------------------------------------------

    def set_status(self, status):
        self.own_status = status
        if hasattr(self, "_status_btn"):
            self._status_btn.config(text=STATUS_DOT[status])
        if self.tray:
            self.tray.update_icon(status)
        if self.network:
            threading.Thread(target=self.network.broadcast_status, daemon=True).start()

    def _show_status_menu(self):
        menu = tk.Menu(self.root, tearoff=0, bg="#003399", fg="white",
                       activebackground="#0055CC", activeforeground="white",
                       font=("Tahoma", 10))
        for st in (STATUS_ONLINE, STATUS_BUSY, STATUS_AWAY):
            label = f"{STATUS_DOT[st]}  {STATUS_LABEL[st]}"
            menu.add_command(label=label, command=lambda s=st: self.set_status(s))
        try:
            x = self._status_btn.winfo_rootx()
            y = self._status_btn.winfo_rooty() + self._status_btn.winfo_height()
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    # -- tray ----------------------------------------------------------------

    def toggle_window(self):
        if self._win_visible:
            self.root.withdraw()
        else:
            self.root.deiconify()
            self.root.lift()
        self._win_visible = not self._win_visible

    # -- ağ olayları ---------------------------------------------------------

    def _on_peer_found(self, ip, name, status):
        self.root.after(0, lambda: self._add_peer(ip, name, status))

    def _on_peer_lost(self, ip):
        self.root.after(0, lambda: self._remove_peer(ip))

    def _on_message(self, sender_ip, msg):
        sender_name = self.peers.get(sender_ip, sender_ip)
        if msg["type"] == "text":
            content = msg["content"]
            self.root.after(0, lambda: self._recv_text(sender_ip, sender_name, content))
        elif msg["type"] == "file":
            filename = msg["filename"]
            raw      = msg.get("raw_data", b"")
            self.root.after(0, lambda: self._recv_file(sender_ip, sender_name, filename, raw))

    # -- kişi listesi --------------------------------------------------------

    def _add_peer(self, ip, name, status):
        self.peers[ip]         = name
        self.peer_statuses[ip] = status
        self._refresh_list()

    def _remove_peer(self, ip):
        self.peers.pop(ip, None)
        self.peer_statuses.pop(ip, None)
        self._refresh_list()

    def _refresh_list(self):
        self._listbox.delete(0, "end")
        for ip, name in self.peers.items():
            dot = STATUS_DOT.get(self.peer_statuses.get(ip, STATUS_ONLINE), "🟢")
            self._listbox.insert("end", f"  {dot}  {name}")
        count = len(self.peers)
        self._count_lbl.config(text=f"({count} çevrimiçi)" if count else "(kimse yok)")
        self._status_lbl.config(
            text=f"{count} kişi  •  {self.local_ip}" if count
            else f"Ağ taranıyor...  •  {self.local_ip}"
        )

    # -- sohbet --------------------------------------------------------------

    def _open_from_list(self, _=None):
        sel = self._listbox.curselection()
        if not sel:
            return
        ips = list(self.peers.keys())
        idx = sel[0]
        if idx < len(ips):
            ip = ips[idx]
            self._open_chat(ip, self.peers[ip])

    def _open_chat(self, ip, name):
        if ip in self.chat_windows and self.chat_windows[ip].exists():
            self.chat_windows[ip].focus()
            return
        self.chat_windows[ip] = ChatWindow(
            parent=self.root, username=self.username,
            peer_ip=ip, peer_name=name,
            db=self.db, network=self.network,
            on_close=self._close_chat,
        )

    def _close_chat(self, ip):
        cw = self.chat_windows.pop(ip, None)
        if cw:
            try:
                cw.win.destroy()
            except Exception:
                pass

    # -- mesaj alma ----------------------------------------------------------

    def _recv_text(self, ip, name, content):
        # Meşgulse sessiz bildirim (zil yok), ama pencere açılır
        if ip in self.chat_windows and self.chat_windows[ip].exists():
            self.chat_windows[ip].receive_text(content)
        else:
            self._open_chat(ip, name)
            self.root.after(200, lambda: self._deliver_text(ip, content))
        # Pencereyi göster
        if not self._win_visible:
            self.root.deiconify()
            self._win_visible = True

    def _recv_file(self, ip, name, filename, raw):
        if ip in self.chat_windows and self.chat_windows[ip].exists():
            self.chat_windows[ip].receive_file(filename, raw)
        else:
            self._open_chat(ip, name)
            self.root.after(200, lambda: self._deliver_file(ip, filename, raw))
        if not self._win_visible:
            self.root.deiconify()
            self._win_visible = True

    def _deliver_text(self, ip, content):
        if ip in self.chat_windows and self.chat_windows[ip].exists():
            self.chat_windows[ip].receive_text(content)

    def _deliver_file(self, ip, filename, raw):
        if ip in self.chat_windows and self.chat_windows[ip].exists():
            self.chat_windows[ip].receive_file(filename, raw)

    # -- çıkış ---------------------------------------------------------------

    def _on_quit(self):
        if self.network:
            self.network.stop()
        if self.tray:
            self.tray.stop()
        self.root.destroy()


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    LANMessengerApp()

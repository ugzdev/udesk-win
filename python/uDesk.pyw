from concurrent.futures import ThreadPoolExecutor
import sys
import os
import json
import socket
import threading
import winreg
import subprocess
import ctypes
import base64
import atexit
import secrets
import hashlib
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from PyQt5.QtCore import QFileInfo, QByteArray, QBuffer, QIODevice
from PyQt5.QtWidgets import QFileIconProvider
from winrt.windows.storage.streams import DataReader
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume, ISimpleAudioVolume
import asyncio
import concurrent.futures
from winrt.windows.media.control import (
    GlobalSystemMediaTransportControlsSessionManager,
    GlobalSystemMediaTransportControlsSessionPlaybackStatus as PlaybackStatus,
)
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLineEdit,
                             QFileDialog, QLabel, QMessageBox, QGridLayout,
                             QScrollArea, QFrame, QDialog, QSystemTrayIcon, QMenu, QAction,QRubberBand,QCheckBox)
from PyQt5.QtCore import QThread, Qt, QTimer, QEvent, QRect, QPoint, QSize,QObject,pyqtSignal
from PyQt5.QtGui import QPixmap, QMovie, QFontDatabase, QIcon
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest
from PyQt5.QtCore import QUrl

from http.server import BaseHTTPRequestHandler, HTTPServer

import keyboard
import comtypes
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

import psutil
import pyautogui
pyautogui.PAUSE = 0
import time

import pyperclip

SERVER_ACTIVE = False

client_port = 12896
udp_port=12897

LAST_PC_CLIPBOARD = ""
PENDING_ANDROID_CLIPBOARD = ""

import queue
import pynput.mouse as pmouse

MOUSE_MODE_ACTIVE = False
MOUSE_EVENT_QUEUE = queue.Queue(maxsize=100)
POWER_SAVING_ACTIVE = False
HOOKED_HOTKEYS = []
mouse_listener = None
last_mouse_pos = None

SHARED_COOKIES = []


# Sesi yönetecek C# programını hafızada tutacağımız değişken
AUDIO_HELPER_PROCESS = None

ACTION_LOCK = threading.Lock()
NET_LOCK = threading.Lock()

# Gelen ekran görüntüsünü Android'e iletilene kadar hafızada tutacak değişken
PENDING_SCREENSHOT = ""

pyautogui.FAILSAFE = False # Ekran köşelerine gidince çökmesini engeller

# İnternet hızı hesaplamak için global değişkenler
last_net_bytes = psutil.net_io_counters().bytes_recv + psutil.net_io_counters().bytes_sent
last_net_time = time.time()

APP_STARTUP_NAME = "uDeskAutoStart"

def get_executable_path():
    """Çalışma ortamına göre doğru dosya yolunu döndürür (.py veya .exe)"""
    if getattr(sys, 'frozen', False):
        # PyInstaller vb. ile .exe yapılmışsa
        return f'"{sys.executable}"'
    else:
        # Geliştirme ortamında .py olarak çalışıyorsa
        return f'"{sys.executable}" "{os.path.abspath(__file__)}"'

def check_startup_status():
    """Uygulamanın başlangıçta açılmaya ayarlı olup olmadığını kontrol eder."""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ)
        value, _ = winreg.QueryValueEx(key, APP_STARTUP_NAME)
        winreg.CloseKey(key)
        return value == get_executable_path()
    except (FileNotFoundError, OSError):
        return False

def set_startup_status(state):
    """Başlangıçta çalışma durumunu Kayıt Defterine yazar veya siler."""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
        if state:
            winreg.SetValueEx(key, APP_STARTUP_NAME, 0, winreg.REG_SZ, get_executable_path())
            print("[uDesk] Başlangıca eklendi.")
        else:
            winreg.DeleteValue(key, APP_STARTUP_NAME)
            print("[uDesk] Başlangıçtan kaldırıldı.")
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"[uDesk] Başlangıç ayarı değiştirilemedi: {e}")
        return False
    
def toggle_usb_adb_mode(active):
    """ADB kullanarak USB üzerinden TCP portlarını yönlendirir (Reverse Proxy)"""
    try:
        if active:
            print("[uDesk] USB Modu Başlatılıyor (ADB Reverse)...")
            # Ana TCP Sunucusu
            subprocess.run(["adb", "reverse", f"tcp:{client_port}", f"tcp:{client_port}"], creationflags=subprocess.CREATE_NO_WINDOW)
            # Eklenti (HTTP) Sunucusu
            subprocess.run(["adb", "reverse", "tcp:51481", "tcp:51481"], creationflags=subprocess.CREATE_NO_WINDOW)
            return True
        else:
            print("[uDesk] USB Modu Kapatılıyor...")
            subprocess.run(["adb", "reverse", "--remove-all"], creationflags=subprocess.CREATE_NO_WINDOW)
            return True
    except FileNotFoundError:
        print("[uDesk] HATA: ADB (Android Debug Bridge) sistemde bulunamadı.")
        return False

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "127.0.0.1"
    
"""
def encrypt_cookies(cookies_list, token):
    if not cookies_list:
        return ""
    try:
        cookies_json = json.dumps(cookies_list).encode('utf-8')
        key = hashlib.sha256(token.encode('utf-8')).digest()
        iv = os.urandom(16)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        encrypted_bytes = cipher.encrypt(pad(cookies_json, AES.block_size))
        return base64.b64encode(iv + encrypted_bytes).decode('utf-8')
    except Exception as e:
        print(f"[Şifreleme Hatası]: {e}")
        return ""
"""


REFRESH_APPS_REQUESTED = False
REFRESH_MODS_REQUESTED = False
CACHED_IMAGE_URL = ""

def trigger_android_sync():
    global REFRESH_APPS_REQUESTED, REFRESH_MODS_REQUESTED, CACHED_APPS_LIST, CACHED_MODS_LIST, CACHED_IMAGE_URL
    with CACHE_LOCK:
        CACHED_APPS_LIST = None
        CACHED_MODS_LIST = None
        CACHED_IMAGE_URL = load_settings().get("image_url", "")
        REFRESH_APPS_REQUESTED = True
        REFRESH_MODS_REQUESTED = True
    print("[uDesk] Android için senkronizasyon tetiklendi.")

# --- PYINSTALLER ONEDIR UYUMLU KÖK DİZİN TESPİTİ ---
if getattr(sys, 'frozen', False):
    # PyInstaller ile derlendiğinde (.exe), ana dizin exe'nin bulunduğu klasördür.
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # Geliştirme ortamında (.pyw) çalışırken
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    
    

import traceback
import faulthandler

# ── 1. C++ SEVİYESİ ÇÖKMELER İÇİN KARA KUTU (SEGFAULT YAKALAYICI) ──
# Uygulama aniden yok olursa, bu dosyaya çökme anındaki satırı yazar.
crash_log_path = os.path.join(BASE_DIR, "udesk_crash_log.txt")
crash_log_file = open(crash_log_path, "w")
faulthandler.enable(file=crash_log_file)

# ── 2. PYTHON SEVİYESİ BEKLENMEYEN HATALARI EKRANA BASMA ──
def global_exception_handler(exc_type, exc_value, exc_traceback):
    # Eğer program klavyeden (Ctrl+C) kapatıldıysa görmezden gel
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    # Hata mesajını metne çevir
    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    
    # Hata penceresi göster (Uygulamanın sessizce yok olmasını engeller)
    from PyQt5.QtWidgets import QMessageBox
    msg_box = QMessageBox()
    msg_box.setIcon(QMessageBox.Critical)
    msg_box.setWindowTitle("uDesk Kritik Hata!")
    msg_box.setText("Uygulama beklenmeyen bir hata ile karşılaştı.")
    msg_box.setInformativeText("Lütfen detayları kontrol edin. Uygulama çalışmaya devam etmeye çalışacak.")
    msg_box.setDetailedText(error_msg)
    msg_box.exec_()

# Sistemin varsayılan hata yakalayıcısını bizimkiyle değiştir
sys.excepthook = global_exception_handler



# Tüm dosya yollarını artık BASE_DIR üzerinden güvenli bir şekilde bağlıyoruz
APPS_FILE = os.path.join(BASE_DIR, "udesk_apps.json")
SETTINGS_FILE = os.path.join(BASE_DIR, "udesk_settings.json")

def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        return {}
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content: return {}
            return json.loads(content)
    except:
        return {}

def save_settings(settings_data):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings_data, f, ensure_ascii=False, indent=4)
        return True
    except:
        return False
APP_ICONS_CACHE = {} # İkonları RAM'de tutmak için

settings_data = load_settings()
if "security_token" not in settings_data:
    settings_data["security_token"] = secrets.token_hex(3) # 6 haneli rastgele bir şifre (örn: a1b2c3)
    save_settings(settings_data)

SECURITY_TOKEN = settings_data["security_token"]

CACHED_MODS_LIST = None
CACHED_APPS_LIST = None
LAST_MEDIA_TITLE = ""

# Aynı dosyaya hem arayüz hem de sunucu thread'leri erişiyor.
# Kilitsiz erişim, eşzamanlı okuma/yazma sırasında dosyayı bozup
# "uygulama eklerken çöküyor" hatasına sebep oluyordu.
APPS_LOCK = threading.Lock()
SCREENSHOT_LOCK = threading.Lock()
CACHE_LOCK = threading.Lock()

async def get_media_info_async(last_title=""):
    manager = await GlobalSystemMediaTransportControlsSessionManager.request_async()

    sessions = manager.get_sessions()
    target = None
    for s in sessions:
        try:
            playback_info = s.get_playback_info()
            if playback_info and playback_info.playback_status == PlaybackStatus.PLAYING:
                target = s
                break
        except Exception:
            continue

    if target is None:
        target = manager.get_current_session()

    if target is None:
        return {"title": "No Media Playing", "artist": "", "thumbnail": "", "changed": True}

    info = await target.try_get_media_properties_async()
    title = (info.title or "").strip()
    artist = (info.artist or "").strip()
    
    if not title:
        return {"title": "No Media Playing", "artist": "", "thumbnail": "", "changed": True}

    # STATE CHECK: Başlık değişmediyse ağır fotoğraf işleme adımlarını direkt atla!
    if title == last_title:
        return {"title": title, "artist": artist, "thumbnail": "", "changed": False}

    # Başlık değişmiş, kapak fotoğrafını Base64 formatına çevir
    thumbnail_b64 = ""
    try:
        if info.thumbnail:
            stream = await info.thumbnail.open_read_async()
            reader = DataReader(stream)
            await reader.load_async(stream.size)
            buffer = bytearray(stream.size)
            reader.read_bytes(buffer)
            thumbnail_b64 = base64.b64encode(buffer).decode('utf-8')
    except Exception as e:
        pass
        
    return {"title": title, "artist": artist, "thumbnail": thumbnail_b64, "changed": True}

def _get_media_info_sync(last_title):
    return asyncio.run(get_media_info_async(last_title))

_media_executor = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix="udesk-media")

def get_media_info(last_title=""):
    try:
        future = _media_executor.submit(_get_media_info_sync, last_title)
        return future.result(timeout=5)
    except Exception as e:
        return {"title": "No Media Playing", "artist": "", "thumbnail": "", "changed": True}
    
    
def hide_system_cursor():
    """Windows sistem imleçlerini geçici olarak boş (görünmez) bir imleçle değiştirir."""
    and_mask = bytearray([0xFF] * 128)
    xor_mask = bytearray([0x00] * 128)
    
    # Gizlenecek yaygın imleç ID'leri: Normal ok(32512), Metin seçme(32513), Bekleme(32514), Link eli(32649)
    cursors_to_hide = [32512, 32513, 32514, 32649]
    
    for cursor_id in cursors_to_hide:
        # Her değiştirme işlemi için yeni bir imleç objesi oluşturulmalı
        hcursor = ctypes.windll.user32.CreateCursor(0, 0, 0, 32, 32, bytes(and_mask), bytes(xor_mask))
        ctypes.windll.user32.SetSystemCursor(hcursor, cursor_id)

def show_system_cursor():
    """Kayıt defterindeki standart Windows imleçlerini sisteme geri yükler."""
    # 0x0057 = SPI_SETCURSORS (Sistem imleçlerini sıfırla)
    ctypes.windll.user32.SystemParametersInfoW(0x0057, 0, None, 0)

def center_mouse():
    """Fareyi ekranın tam merkezine taşır."""
    # 0 = SM_CXSCREEN (Genişlik), 1 = SM_CYSCREEN (Yükseklik)
    screen_width = ctypes.windll.user32.GetSystemMetrics(0)
    screen_height = ctypes.windll.user32.GetSystemMetrics(1)
    ctypes.windll.user32.SetCursorPos(screen_width // 2, screen_height // 2)

# Uygulama aniden kapatılırsa fareyi tekrar görünür yapmak için güvenlik kancası
atexit.register(show_system_cursor)


def load_apps():
    """Kayıtlı uygulama listesini güvenli şekilde okur."""
    with APPS_LOCK:
        if not os.path.exists(APPS_FILE):
            return {}
        try:
            with open(APPS_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    return {}
                return json.loads(content)
        except (json.JSONDecodeError, OSError) as e:
            print(f"[Uygulama Listesi] Okuma hatası (dosya bozuk olabilir): {e}")
            return {}


def save_apps(apps):
    with APPS_LOCK:
        tmp_path = APPS_FILE + ".tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(apps, f, ensure_ascii=False, indent=4)
            os.replace(tmp_path, APPS_FILE)
            return True
        except OSError as e:
            print(f"[Uygulama Listesi] Yazma hatası: {e}")
            return False
        
def get_mods_list():
    global CACHED_MODS_LIST
    if CACHED_MODS_LIST is not None:
        return CACHED_MODS_LIST

    import modstarter
    
    mods_dir = os.path.join(BASE_DIR, "mods")
    mods_list = []
    
    if os.path.exists(mods_dir):
        for filename in os.listdir(mods_dir):
            if filename.endswith(".json"): # ARTIK PYTHON DEĞİL JSON OKUYORUZ
                file_path = os.path.join(mods_dir, filename)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        mod_info = json.load(f)
                        
                    mod_info["mod_file"] = filename[:-5] # .json uzantısını at
                    
                    # Butonların (Varsa) LED ışığı başlangıç durumunu kontrol et
                    updated_buttons = []
                    for btn in mod_info.get("buttons", []):
                        btn_copy = btn.copy()
                        if btn_copy.get("has_indicator"):
                            # modstarter'dan o anki mikrofon/ses durumunu al
                            btn_copy["initial_light"] = modstarter.get_initial_state(btn_copy.get("action"))
                        updated_buttons.append(btn_copy)
                        
                    mod_info["buttons"] = updated_buttons
                    mods_list.append(mod_info)
                except Exception as e:
                    print(f"[Mod Okuma Hatası] {filename}: {e}")
                    
    CACHED_MODS_LIST = mods_list
    return CACHED_MODS_LIST

def get_mods_html():
    """Kullanıcının PC'deki mods klasöründeki index.html dosyasını okur."""
    html_path = os.path.join(BASE_DIR, "mods", "index.html")
    if os.path.exists(html_path):
        try:
            with open(html_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            print(f"[HTML Okuma Hatası]: {e}")
            
    # Eğer dosya yoksa siyah, uDesk temasına uygun varsayılan bir uyarı ekranı yolla
    return """
    <html>
        <body style='margin:0; padding:20px; background-color:transparent; color:rgba(255,255,255,0.5); font-family:sans-serif; text-align:center; display:flex; flex-direction:column; justify-content:center; height:100vh;'>
            <h2 style='color:rgba(255,255,255,0.8);'>Mod Yüklü Değil</h2>
            <p style='font-size: 12px;'>PC'deki <b>mods</b> klasörüne bir <b>index.html</b> eklerseniz, kendi widget'larınızı burada görebilirsiniz.</p>
        </body>
    </html>
    """

def get_apps_list():
    global CACHED_APPS_LIST
    with CACHE_LOCK:
        if CACHED_APPS_LIST is not None:
            return CACHED_APPS_LIST

        apps = load_apps()
        app_list = []
        for name in apps.keys():
            app_list.append({
                "name": name,
                "icon": APP_ICONS_CACHE.get(name, "")
            })
        
        CACHED_APPS_LIST = app_list
        return CACHED_APPS_LIST

def get_wallpaper_b64():
    """Kayıtlı arka plan görselini okuyup base64 olarak döndürür."""
    settings = load_settings()
    wp_path = settings.get("wallpaper_path", "")
    if wp_path and os.path.exists(wp_path):
        try:
            with open(wp_path, "rb") as f:
                return base64.b64encode(f.read()).decode('utf-8')
        except Exception as e:
            print(f"[Wallpaper Hatası]: {e}")
    return ""


def get_master_volume():
    """0-100 arası mevcut sistem sesini döndürür, hata olursa None."""
    try:
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        return round(volume.GetMasterVolumeLevelScalar() * 100)
    except Exception as e:
        print(f"[Ses] Okuma hatası: {e}")
        return None


def set_master_volume(val_percent):
    try:
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        volume.SetMasterVolumeLevelScalar(max(0.0, min(1.0, val_percent / 100.0)), None)
        return True
    except Exception as e:
        print(f"[Ses] Yazma hatası: {e}")
        return False
    
# --- EKLENTİ URL DİNLEYİCİ BÖLÜMÜ ---
SHARED_URL = ""
SHARED_MINI_URL = ""

def win32_event_filter(msg, data):
    global mouse_listener
    if not MOUSE_MODE_ACTIVE:
        return True
        
    # 512 = WM_MOUSEMOVE (Fare Hareketi - Buna izin ver, pynput on_move'a göndersin)
    # 512 = WM_MOUSEMOVE (Fare Hareketi)
    if msg == 512:
        return True
    
    # 522 = WM_MOUSEWHEEL (Tekerlek Kaydırma)
    if msg == 522:
        try:
            # MSLLHOOKSTRUCT'ta tekerlek verisi 'mouseData' özelliğinin üst 16 bitindedir.
            mouse_data = getattr(data, 'mouseData', 0)
            
            # Üst 16 biti işaretli (signed) değere çeviriyoruz
            delta = (mouse_data >> 16) & 0xFFFF
            if delta >= 32768:
                delta -= 65536
            
            # Yönü netleştirip string olarak gönderiyoruz
            direction = "up" if delta > 0 else "down"
            
            if MOUSE_EVENT_QUEUE.full():
                try: MOUSE_EVENT_QUEUE.get_nowait()
                except: pass
                
            MOUSE_EVENT_QUEUE.put_nowait({"type": "scroll", "direction": direction}) 
        except Exception as e:
            print(f"[Scroll Hatası]: {e}")
            
        # Olayı Windows'tan (PC'den) engelle
        if mouse_listener is not None:
            mouse_listener.suppress_event()
        return True
        
    # 513 = Sol Bas, 514 = Sol Bırak | 516 = Sağ Bas, 517 = Sağ Bırak
    if msg in (513, 514, 516, 517):
        btn = "left" if msg in (513, 514) else "right"
        pressed = True if msg in (513, 516) else False
        
        # Olayı çöpe atmadan hemen önce kendimiz kuyruğa ekliyoruz!
        try: MOUSE_EVENT_QUEUE.put_nowait({"type": "click", "button": btn, "pressed": pressed})
        except queue.Full: pass
            
        # ŞİMDİ Windows'tan gizleyebiliriz
        if mouse_listener is not None:
            mouse_listener.suppress_event()
        return True
        
    # Kaydırma (Scroll) gibi diğer olayları da engelle
    if mouse_listener is not None:
        mouse_listener.suppress_event()
    return True

last_mouse_time = 0

def on_mouse_move(x, y):
    global MOUSE_MODE_ACTIVE, last_mouse_pos, last_mouse_time
    if not MOUSE_MODE_ACTIVE: 
        return
    if last_mouse_pos is None:
        last_mouse_pos = (x, y)
        return
    current_time = time.time()
    if current_time - last_mouse_time < 0.0010:
        return
    dx = x - last_mouse_pos[0]
    dy = y - last_mouse_pos[1]

    if dx != 0 or dy != 0:
        try: 
            MOUSE_EVENT_QUEUE.put_nowait({"type": "move", "dx": dx, "dy": dy})
            last_mouse_time = current_time
            last_mouse_pos = (x, y) 
        except queue.Full: 
            pass
        
def on_scroll(x, y, dx, dy):
    # pynput dinleyicisinin hata vermemesi için boş bir callback tanımı yapıyoruz.
    # Event engelleme ve kuyruğa ekleme işini zaten win32_event_filter içinde tıkır tıkır yapıyoruz.
    pass
        
def send_key_to_android(event):
    key = event.name
    if key == 'space':
        key = ' '

    # CTRL, SHIFT ve ALT durumlarını yakalıyoruz
    is_ctrl = keyboard.is_pressed('ctrl')
    is_shift = keyboard.is_pressed('shift')
    is_alt = keyboard.is_pressed('alt')

    # Eğer sadece harf ise ve Shift basılıysa, Ctrl de basılı DEĞİLSE büyük harfe çevir
    if len(key) == 1 and key.isalpha() and is_shift and not is_ctrl:
        key = key.upper()
            
    try: 
        MOUSE_EVENT_QUEUE.put_nowait({
            "type": "keyboard", 
            "key": key,
            "ctrl": is_ctrl,
            "shift": is_shift,
            "alt": is_alt
        })
    except queue.Full: 
        pass

def set_keyboard_capture(active):
    global HOOKED_HOTKEYS
    if active and not HOOKED_HOTKEYS:
        # Yakalanacak ve Windows'tan gizlenecek (suppress) tuşlar
        keys_to_hook = 'abcçdefgğhıijklmnoöpqrsştuüvwxyz0123456789.,;:-_*/+!@#$%^&()=<>|£[]}{é'
        for k in keys_to_hook:
            hk = keyboard.on_press_key(k, send_key_to_android, suppress=True)
            HOOKED_HOTKEYS.append(hk)
            
        # Özel tuşları yakala (Yön tuşları, Delete, Tab vb. eklendi)
        special_keys = ['space', 'backspace', 'enter', 'up', 'down', 'left', 'right', 'delete', 'escape', 'tab']
        for special in special_keys:
            hk = keyboard.on_press_key(special, send_key_to_android, suppress=True)
            HOOKED_HOTKEYS.append(hk)
            
        print("[uDesk] PC Klavyesi Android'e yönlendirildi (Kilitli).")
        
    elif not active and HOOKED_HOTKEYS:
        for hk in HOOKED_HOTKEYS:
            keyboard.unhook(hk)
        HOOKED_HOTKEYS.clear()
        print("[uDesk] PC Klavye kilidi açıldı.")

def toggle_mouse_mode():
    global MOUSE_MODE_ACTIVE, mouse_listener, last_mouse_pos
    MOUSE_MODE_ACTIVE = not MOUSE_MODE_ACTIVE
    
    if MOUSE_MODE_ACTIVE:
        last_mouse_pos = None
        while not MOUSE_EVENT_QUEUE.empty():
            try: MOUSE_EVENT_QUEUE.get_nowait()
            except: pass
        MOUSE_EVENT_QUEUE.put({"type": "status", "active": True})
        
        # --- EKLENEN KISIM: Fareyi ortala ve sistemde gizle ---
        center_mouse()
        hide_system_cursor()
        # ------------------------------------------------------

        # KRİTİK DÜZELTME: on_scroll parametresini buraya bağlıyoruz
        mouse_listener = pmouse.Listener(
            on_move=on_mouse_move,
            on_scroll=on_scroll,
            win32_event_filter=win32_event_filter
        )
        mouse_listener.start()
        print("[uDesk] Android Mouse Mode: AÇIK")
    else:
        set_keyboard_capture(False)
        if mouse_listener: 
            mouse_listener.stop()
        try: MOUSE_EVENT_QUEUE.put_nowait({"type": "status", "active": False})
        except queue.Full: pass
        
        # --- EKLENEN KISIM: Fareyi tekrar görünür yap ---
        show_system_cursor()
        # ------------------------------------------------
        
        print("[uDesk] Android Mouse Mode: KAPALI")
        
class AppSignals(QObject):
    safe_execute = pyqtSignal(object)

class ExtensionHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200, "ok")
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header("Access-Control-Allow-Headers", "Content-type")
        self.end_headers()

    def do_POST(self):
        global SERVER_ACTIVE
        if not SERVER_ACTIVE:
            self.send_response(503)
            self.end_headers()
            return
            
        global SHARED_URL, SHARED_MINI_URL
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
    
        try:
            data = json.loads(post_data.decode('utf-8'))
            if "url" in data:
                SHARED_URL = data["url"]
                print(f"[Eklenti] Yeni URL geldi: {SHARED_URL}")
            if "mini_url" in data:
                SHARED_MINI_URL = data["mini_url"]
                print(f"[Eklenti] Mini Web URL geldi: {SHARED_MINI_URL}")
            # if "cookies" in data:
            #     global SHARED_COOKIES
            #     SHARED_COOKIES = data["cookies"]
            #     print(f"[Eklenti] {len(SHARED_COOKIES)} adet çerez alındı.")
        except Exception as e:
            print("Eklenti hatası:", e)

        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(b'{"status": "ok"}')

class ExtensionServerThread(QThread):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.server = None

    def run(self):
        try:
            self.server = HTTPServer(('0.0.0.0', 51481), ExtensionHandler)
            self.server.serve_forever()
        except Exception:
            pass

    def stop(self):
        if self.server:
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            self.server.server_close()

class UdpServerThread(QThread):
    def __init__(self, host='0.0.0.0', port=udp_port, parent=None):
        super().__init__(parent)
        self.host = host
        self.port = port
        self.running = True
        self.sock = None

    def run(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            self.sock.bind((self.host, self.port))
        except OSError:
            return

        while self.running:
            try:
                data, addr = self.sock.recvfrom(1024)
                if not self.running:
                    break
                
                cmd = json.loads(data.decode('utf-8'))
                if cmd.get("token") != SECURITY_TOKEN:
                    continue

                if not SERVER_ACTIVE:
                    continue

                action = cmd.get("action")
                if action == "mouse_move":
                    coords = cmd.get("value", "").split(",")
                    if len(coords) == 2:
                        dx = int(float(coords[0]) * 2.0)
                        dy = int(float(coords[1]) * 2.0)
                        ctypes.windll.user32.mouse_event(0x0001, dx, dy, 0, 0)

                elif action == "mouse_click":
                    val = cmd.get("value", "left")
                    if val == "right":
                        ctypes.windll.user32.mouse_event(0x0008, 0, 0, 0, 0)
                        ctypes.windll.user32.mouse_event(0x0010, 0, 0, 0, 0)
                    else:
                        ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0)
                        ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)
            except Exception:
                pass

    def stop(self):
        self.running = False
        if self.sock:
            try:
                self.sock.close()
            except:
                pass


class ServerThread(QThread):
    def __init__(self, signals=None, host='0.0.0.0', port=client_port, parent=None):
        super().__init__(parent)
        self.signals = signals
        self.host = host
        self.port = port
        self.running = True
        self.server = None
        self.pool = ThreadPoolExecutor(max_workers=15, thread_name_prefix="UDeskWorker")
        self.active_conns = [] # Aktif bağlantıları hafızada tutacağız

    def run(self):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.server.bind((self.host, self.port))
            self.server.listen(15)
        except OSError as e:
            return

        while self.running:
            try:
                conn, addr = self.server.accept()
                self.active_conns.append(conn) # Gelen cihazı listeye al
                self.pool.submit(self.handle_client_safe, conn)
            except OSError:
                break

    # EKLENEN/DEĞİŞTİRİLEN KISIM: stop() METODU (Şalteri kökten kapatır)
    def stop(self):
        self.running = False
        # 1. Yeni bağlantı gelmesini engelle
        if self.server:
            try: self.server.close()
            except OSError: pass
            
        for conn in self.active_conns:
            try: conn.shutdown(socket.SHUT_RDWR)
            except: pass
            try: conn.close()
            except: pass
        self.active_conns.clear()
        
        if hasattr(self, 'pool'):
            self.pool.shutdown(wait=False)

    def handle_client_safe(self, conn):
        try:
            conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        except:
            pass
        com_initialized = False
        try:
            comtypes.CoInitialize()
            com_initialized = True
        except: 
            pass
        try:
            self.handle_client(conn)
        finally:
            conn.close()
            # EN KRİTİK NOKTA: COM kaynaklarını sisteme iade ediyoruz
            if com_initialized:
                try:
                    comtypes.CoUninitialize()
                except:
                    pass

    def handle_client(self, conn):
        try:
            while True:
                data = conn.recv(1024)
                if not data: break
                
                cmd = json.loads(data.decode("utf-8"))

                if cmd.get("token") != SECURITY_TOKEN:
                    conn.sendall(b'{"status": "error", "message": "Unauthorized/Yanlis Token"}\n')
                    return 

                if not SERVER_ACTIVE:
                    try:
                        conn.sendall(b'{"status": "error", "message": "Server deaktif"}\n')
                    except Exception:
                        pass
                    break

                action = cmd.get("action")
                
                if action == "mouse_stream":                   
                    try:
                        while True:
                            if not SERVER_ACTIVE or not self.running:
                                break
                            try:
                                evt = MOUSE_EVENT_QUEUE.get(timeout=2)
                                conn.sendall((json.dumps(evt) + "\n").encode("utf-8"))
                            except queue.Empty:
                                conn.sendall(b'{"type": "ping"}\n')
                    except Exception as e:
                        print(f"[uDesk] Mouse bağlantısı koptu: {e}")
                    finally:
                        if MOUSE_MODE_ACTIVE:
                            if self.signals:
                                self.signals.safe_execute.emit(toggle_mouse_mode)
                            else:
                                toggle_mouse_mode()
                    return
                
                elif action == "data_stream":
                    global last_net_bytes, last_net_time, SHARED_URL, PENDING_SCREENSHOT, SHARED_MINI_URL
                    global REFRESH_APPS_REQUESTED, REFRESH_MODS_REQUESTED
                    
                    # İlk bağlantıda verileri bir kereye mahsus mutlaka gönder
                    first_sync = True 
                    
                    try:
                        while True:
                            global POWER_SAVING_ACTIVE, LAST_MEDIA_TITLE

                            if not SERVER_ACTIVE or not self.running:
                                break

                            if POWER_SAVING_ACTIVE:
                                # ... [Power saving kodu aynen kalıyor] ...
                                continue

                            # ── NORMAL MOD ──────────────────
                            cpu = psutil.cpu_percent()
                            ram = psutil.virtual_memory().percent
                            now = time.time()
                            
                            net = psutil.net_io_counters()
                            with NET_LOCK:
                                current_bytes = net.bytes_recv + net.bytes_sent
                                speed = (current_bytes - last_net_bytes) / (now - last_net_time) if now > last_net_time else 0
                                last_net_bytes = current_bytes
                                last_net_time = now
                            mbps = round((speed * 8) / 1000000, 1)
                            
                            settings = load_settings()
                            
                            global CACHED_IMAGE_URL
                            
                            if not CACHED_IMAGE_URL:
                                CACHED_IMAGE_URL = settings.get("image_url", "")
                            image_url = CACHED_IMAGE_URL                    
                            
                            info = get_media_info(LAST_MEDIA_TITLE)
                            if info.get("changed", True):
                                LAST_MEDIA_TITLE = info["title"]

                            vol = get_master_volume()
                            curr_url = SHARED_URL
                            SHARED_URL = ""
                            with SCREENSHOT_LOCK:
                                curr_screen = PENDING_SCREENSHOT
                                PENDING_SCREENSHOT = ""
                            curr_mini_url = SHARED_MINI_URL
                            SHARED_MINI_URL = ""

                            # --- YENİ EKLENEN ÇEREZ ŞİFRELEME KISMI ---
                            # settings = load_settings()
                            # send_cookies = settings.get("send_cookies", False)
                            # 
                            # encrypted_cookies_data = ""
                            # global SHARED_COOKIES
                            # 
                            # Eğer kullanıcı checkbox'ı işaretlediyse ve eklentiden çerez geldiyse:
                            # if send_cookies and 'SHARED_COOKIES' in globals() and SHARED_COOKIES:
                            #     encrypted_cookies_data = encrypt_cookies(SHARED_COOKIES, SECURITY_TOKEN)
                            #     SHARED_COOKIES = [] 
                            # else:
                            #     SHARED_COOKIES = []
                                
                            # --- PANO SENKRONİZASYONU (PC -> Android) ---
                            global LAST_PC_CLIPBOARD
                            try:
                                current_pc_clip = pyperclip.paste()
                                if current_pc_clip != LAST_PC_CLIPBOARD:
                                    LAST_PC_CLIPBOARD = current_pc_clip
                                    # Android'e göndermek üzere payload'a eklemek için bir flag atıyoruz
                                    pc_clip_to_send = current_pc_clip
                                else:
                                    pc_clip_to_send = ""
                            except:
                                pc_clip_to_send = ""

                            payload = {
                                "type": "data_sync",
                                "cpu": cpu, "ram": ram, "net": mbps, "image_url": image_url,
                                "media_title": info["title"], "media_artist": info["artist"], 
                                "volume": vol if vol is not None else 50,
                                "url": curr_url, "screenshot": curr_screen,
                                "mini_url": curr_mini_url, 
                                "encrypted_cookies": "",
                                "pc_clipboard": pc_clip_to_send
                            }
              
                            if info.get("changed", True):
                                payload["media_thumb"] = info.get("thumbnail", "")

                            # MANUEL TETİKLEME VEYA İLK BAĞLANTI KONTROLÜ
                            if first_sync or REFRESH_APPS_REQUESTED or REFRESH_MODS_REQUESTED:
                                payload["apps"] = get_apps_list()
                                payload["mods"] = get_mods_list()
                                payload["mods_html"] = get_mods_html()
                                payload["wallpaper_b64"] = get_wallpaper_b64()
                                
                                # Bayrakları indir
                                REFRESH_APPS_REQUESTED = False
                                REFRESH_MODS_REQUESTED = False
                                first_sync = False

                            conn.sendall((json.dumps(payload) + "\n").encode("utf-8"))
                            time.sleep(1.5)
                    except Exception as e:
                        print(f"[uDesk] Data stream koptu: {e}")
                    return
                
                response = self.process_command(cmd)
                conn.sendall((json.dumps(response) + "\n").encode("utf-8"))
        except Exception as e:
            pass

    def process_command(self, cmd):
        action = cmd.get("action")
        try:
            if action == "set_keyboard_capture":
                active = cmd.get("value", False)
                set_keyboard_capture(active)
                return {"status": "ok"}
            
            if action == "volume":
                val = float(cmd.get("value"))
                val = max(0, min(100, val))
                ok = set_master_volume(val)
                return {"status": "ok"} if ok else {"status": "error", "message": "Ses ayarlanamadı"}
            
            elif action == "power_saving":
                global POWER_SAVING_ACTIVE
                POWER_SAVING_ACTIVE = bool(cmd.get("value", False))
                print(f"[uDesk] PC Tasarruf Modu Durumu: {POWER_SAVING_ACTIVE}")
                return {"status": "ok"}

            elif action == "media":
                control = cmd.get("value")
                mapping = {
                    "play_pause": "play/pause media",
                    "next": "next track",
                    "prev": "previous track",
                }
                key = mapping.get(control)
                if not key:
                    return {"status": "error", "message": f"Bilinmeyen medya komutu: {control}"}
                keyboard.send(key)
                return {"status": "ok"}

            elif action == "launch":
                app_name = cmd.get("value")
                apps = load_apps()
                path = apps.get(app_name)
                
                if not path:
                    return {"status": "error", "message": f"'{app_name}' kayıtlı değil"}
                
                try:
                    if path.startswith("shell:"):
                        subprocess.Popen(f"explorer.exe {path}", shell=True)
                    else:
                        if not os.path.exists(path):
                            return {"status": "error", "message": f"Dosya bulunamadı: {path}"}
                        os.startfile(path) 
                        
                    return {"status": "ok"}
                except Exception as e:
                    return {"status": "error", "message": f"Çalıştırma hatası: {str(e)}"}
                
            elif action == "open_in_browser":
                url_to_open = cmd.get("value")
                if url_to_open:
                    try:
                        os.startfile(url_to_open)
                    except Exception as e:
                        pass
                return {"status": "ok"}
            
            elif action == "mouse_move":
                try:
                    coords = cmd.get("value", "").split(",")
                    if len(coords) == 2:
                        dx = int(float(coords[0]) * 2.0)
                        dy = int(float(coords[1]) * 2.0)
                        # Windows'un doğrudan kendi kütüphanesini kullanıyoruz
                        ctypes.windll.user32.mouse_event(0x0001, dx, dy, 0, 0)
                    return {"status": "ok"}
                except Exception as e:
                    return {"status": "error", "message": str(e)}

            elif action == "mouse_click":
                try:
                    val = cmd.get("value", "left")
                    if val == "right":
                        ctypes.windll.user32.mouse_event(0x0008, 0, 0, 0, 0)
                        ctypes.windll.user32.mouse_event(0x0010, 0, 0, 0, 0)
                    else:
                        ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0)
                        ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)
                    return {"status": "ok"}
                except Exception as e:
                    return {"status": "error", "message": str(e)}
                
            
            elif action == "get_app_volumes":
                try:
                    sessions = AudioUtilities.GetAllSessions()
                    app_list = []
                    for session in sessions:
                        if session.Process:
                            volume = session._ctl.QueryInterface(ISimpleAudioVolume)
                            app_name = session.Process.name().replace(".exe", "")
                            vol_val = round(volume.GetMasterVolume() * 100)
                            app_list.append({
                                "id": session.Process.pid,
                                "name": app_name,
                                "volume": vol_val
                            })
                    return {"status": "ok", "apps": app_list}
                except Exception as e:
                    return {"status": "error", "message": str(e)}

            elif action == "set_app_volume":
                try:
                    val = cmd.get("value", {})
                    pid = val.get("id")
                    vol_percent = float(val.get("volume", 0))
                    
                    sessions = AudioUtilities.GetAllSessions()
                    for session in sessions:
                        if session.Process and session.Process.pid == pid:
                            volume = session._ctl.QueryInterface(ISimpleAudioVolume)
                            volume.SetMasterVolume(max(0.0, min(1.0, vol_percent / 100.0)), None)
                            return {"status": "ok"}
                    return {"status": "error", "message": "Uygulama bulunamadı"}
                except Exception as e:
                    return {"status": "error", "message": str(e)}
                
            
            elif action == "sync_clipboard":
                try:
                    android_clip = cmd.get("value", "")
                    if android_clip:
                        global LAST_PC_CLIPBOARD
                        LAST_PC_CLIPBOARD = android_clip
                        pyperclip.copy(android_clip)
                    return {"status": "ok"}
                except Exception as e:
                    return {"status": "error", "message": str(e)}
                
            
            elif action == "audio_stream":
                global AUDIO_HELPER_PROCESS
                val = cmd.get("value")
                
                if val == "start":
                    if AUDIO_HELPER_PROCESS is None:
                        audio_exe_path = os.path.join(BASE_DIR, "uDeskAudio.exe")
                        AUDIO_HELPER_PROCESS = subprocess.Popen(
                            [audio_exe_path], 
                            creationflags=subprocess.CREATE_NO_WINDOW
                        )
                    return {"status": "ok"}
                
                elif val == "stop":
                    if AUDIO_HELPER_PROCESS is not None:
                        # Switch kapandığında C# exe'sini acımadan öldür
                        AUDIO_HELPER_PROCESS.terminate()
                        AUDIO_HELPER_PROCESS = None
                    return {"status": "ok"}

            elif action == "get_status":
                return {
                    "status": "ok",
                    "volume": get_master_volume(),
                }

            elif action == "list_apps":
                apps = load_apps()
                app_list = []
                for name in apps.keys():
                    app_list.append({
                        "name": name,
                        "icon": APP_ICONS_CACHE.get(name, "")
                    })
                return {"status": "ok", "apps": app_list}
                
            elif action == "get_mods":
                # Artık uzun uzun tekrar yazmak yerine üstteki fonksiyonu çağırıyoruz
                return {"status": "ok", "mods": get_mods_list()}

            elif action == "run_mod":
                import modstarter
                mod_data = cmd.get("value", {})
                mod_file = mod_data.get("mod_file")
                button_id = mod_data.get("button_id")
                
                mods_dir = os.path.join(BASE_DIR, "mods")
                file_path = os.path.join(mods_dir, f"{mod_file}.json")
                
                if os.path.exists(file_path):
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            mod_info = json.load(f)
                            
                        # JSON içinden tıklanan butonun action verisini bul
                        target_action = None
                        has_indicator = False
                        for btn in mod_info.get("buttons", []):
                            if btn.get("id") == button_id:
                                target_action = btn.get("action")
                                has_indicator = btn.get("has_indicator", False)
                                break
                        
                        if target_action:
                            # Eylemi yeni modstarter motoruna gönder ve çalıştır
                            result = modstarter.execute_action(target_action)
                            
                            response = {"status": "ok"}
                            # Eğer sistem bir LED durumu döndürdüyse telefona ışığı yak/söndür komutu ver
                            if has_indicator and isinstance(result, bool):
                                response["light_on"] = result
                                
                            return response
                        else:
                            return {"status": "error", "message": "Buton eylemi tanımlanmamış."}
                            
                    except Exception as e:
                        return {"status": "error", "message": str(e)}
                return {"status": "error", "message": "Mod json dosyası bulunamadı."}

            else:
                return {"status": "error", "message": f"Bilinmeyen komut: {action}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def stop(self):
        self.running = False
        if self.server:
            try:
                self.server.close()
            except OSError:
                pass
        if hasattr(self, 'pool'):
            self.pool.shutdown(wait=False)

class Snipper(QWidget):
    def __init__(self, parent=None):
        super().__init__()
        self.parent_ui = parent
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setStyleSheet("background-color: black;")
        self.setWindowOpacity(0.3)
        
        screen_geometry = QApplication.primaryScreen().geometry()
        self.setGeometry(screen_geometry)
        
        self.origin = QPoint()
        self.rubberband = QRubberBand(QRubberBand.Rectangle, self)

    def mousePressEvent(self, event):
        self.origin = event.pos()
        self.rubberband.setGeometry(QRect(self.origin, QSize()))
        self.rubberband.show()

    def mouseMoveEvent(self, event):
        self.rubberband.setGeometry(QRect(self.origin, event.pos()).normalized())

    def mouseReleaseEvent(self, event):
        self.rubberband.hide()
        rect = QRect(self.origin, event.pos()).normalized()
        self.hide()
        
        # Eğer çok küçük bir alan seçildiyse (yanlış tıklama vb.) işlemi iptal et
        if rect.width() < 10 or rect.height() < 10:
            if self.parent_ui:
                self.parent_ui.show()
            self.close()
            return

        # Arayüzün donmaması için QTimer ile kısa bir bekleme yapıyoruz
        QTimer.singleShot(250, lambda: self.capture_screen(rect))

    def capture_screen(self, rect):
        global PENDING_SCREENSHOT
        try:
            screen = QApplication.primaryScreen()
            pixmap = screen.grabWindow(0, rect.x(), rect.y(), rect.width(), rect.height())
            
            byte_array = QByteArray()
            buffer = QBuffer(byte_array)
            buffer.open(QIODevice.WriteOnly)
            pixmap.save(buffer, "PNG")
            
            b64_data = byte_array.toBase64().data().decode("utf-8")
            with SCREENSHOT_LOCK:
                PENDING_SCREENSHOT = b64_data
            
            # Önizlemeyi güncelle - pixmap değişkeni artık tanımlı
            if self.parent_ui and not pixmap.isNull():
                self.parent_ui.update_screenshot_preview(pixmap)
                
        except Exception as e:
            pass
            
        if self.parent_ui:
            self.parent_ui.show()
        self.close()


class UDeskUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("uDesk")
        
        self.app_signals = AppSignals()
        self.app_signals.safe_execute.connect(lambda func: func())
        
        icon_path = os.path.join(BASE_DIR, "icons", "app_icon_000.png")
        self.setWindowIcon(QIcon(icon_path))
        self.setFixedSize(660, 750)
        self._gif_movie = None
        self._net_manager = QNetworkAccessManager(self)
        self._net_manager.finished.connect(self._on_url_image_loaded)
        self.setup_ui()
        self.apply_dark_theme()
        self.refresh_grid()
        
        # Sistem Tepsisi
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.style().standardIcon(self.style().SP_ComputerIcon))
        self.tray_icon.setIcon(QIcon(icon_path))      
        tray_menu = QMenu()
        
        self.toggle_server_action = QAction("Activate", self)
        self.toggle_server_action.triggered.connect(self.server_checkbox.toggle)
        tray_menu.addAction(self.toggle_server_action)
        
        # Ekran Görüntüsü Gönder seçeneği
        screenshot_action = QAction("Send Screenshot", self)
        screenshot_action.triggered.connect(self.start_snipping)
        tray_menu.addAction(screenshot_action)
        
        sync_action = QAction("Sync", self)
        sync_action.triggered.connect(trigger_android_sync)
        tray_menu.addAction(sync_action)
        
        tray_menu.addSeparator() 
        
        restore_action = QAction("Show", self)
        restore_action.triggered.connect(self.showNormal)
        tray_menu.addAction(restore_action)
        
        quit_action = QAction("Exit", self)
        quit_action.triggered.connect(self.quit_app)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        self.tray_icon.activated.connect(self.tray_icon_activated)
        
        base_dir = os.path.dirname(os.path.abspath(__file__))
        font_path = os.path.join(BASE_DIR, "fonts", "Orbitron.ttf")
        if os.path.exists(font_path):
            QFontDatabase.addApplicationFont(font_path)

    def setup_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── NAVBAR ──────────────────────────────────────────
        navbar = QFrame()
        navbar.setObjectName("Navbar")
        navbar.setFixedHeight(52)
        nav_layout = QHBoxLayout(navbar)
        nav_layout.setContentsMargins(20, 0, 20, 0)

        logo = QLabel("uDesk")
        logo.setObjectName("NavLogo")
        nav_layout.addWidget(logo)
        nav_layout.addStretch()

        version_lbl = QLabel("by UGZ - version 1.0")
        version_lbl.setObjectName("VersionLabel")
        nav_layout.addWidget(version_lbl)
        
        self.mod_editor_btn = QPushButton("MODS")
        self.mod_editor_btn.setObjectName("ModEditorBtn")
        self.mod_editor_btn.setFixedSize(45, 30) # Buton boyutunu tasarımına göre ayarlayabilirsin
        self.mod_editor_btn.setCursor(Qt.PointingHandCursor)
        self.mod_editor_btn.clicked.connect(self.open_mod_editor)
        nav_layout.addWidget(self.mod_editor_btn)

        root_layout.addWidget(navbar)

        # ── İÇERİK ──────────────────────────────────────────
        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setContentsMargins(22, 18, 22, 18)
        cl.setSpacing(14)
        
        apps_lbl = QLabel("Last Screenshot / Media Preview")
        apps_lbl.setObjectName("SectionLabel")
        apps_lbl.setAlignment(Qt.AlignCenter) 
        cl.addWidget(apps_lbl, alignment=Qt.AlignCenter)

        # ── ÖNİZLEME ALANLARI (Yan Yana) ─────────────────────
        previews_row = QHBoxLayout()
        previews_row.setSpacing(14)
        previews_row.setAlignment(Qt.AlignCenter)

        # Ekran görüntüsü önizleme
        self.screenshot_preview = QLabel("ScreenShot")
        self.screenshot_preview.setObjectName("PreviewLabel")
        self.screenshot_preview.setAlignment(Qt.AlignCenter)
        self.screenshot_preview.setFixedSize(280, 180)
        self.screenshot_preview.setScaledContents(True)
        previews_row.addWidget(self.screenshot_preview)

        # GIF / Resim önizleme
        self.url_preview = QLabel("GIF / Image")
        self.url_preview.setObjectName("PreviewLabel")
        self.url_preview.setAlignment(Qt.AlignCenter)
        self.url_preview.setFixedSize(280, 180)
        self.url_preview.setScaledContents(True)
        previews_row.addWidget(self.url_preview)

        cl.addLayout(previews_row)

        # ── BUTONLAR (Önizlemelerin altında, aynı genişlikte) ──
        buttons_row = QHBoxLayout()
        buttons_row.setSpacing(14)
        buttons_row.setAlignment(Qt.AlignCenter)

        self.snip_btn = QPushButton("Send Screenshot")
        self.snip_btn.setObjectName("AccentBtn")
        self.snip_btn.setFixedSize(280, 40)
        self.snip_btn.clicked.connect(self.start_snipping)
        buttons_row.addWidget(self.snip_btn)

        save_url_btn = QPushButton("Save Media")
        save_url_btn.setObjectName("SecondaryBtn")
        save_url_btn.setFixedSize(280, 40)
        save_url_btn.clicked.connect(self.save_media_url)
        buttons_row.addWidget(save_url_btn)

        cl.addLayout(buttons_row)
    
        # ── URL INPUT ────────────────────────────────────────
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Enter URL (.jpg / .png / .gif)")
        current_settings = load_settings()
        self.url_input.setFixedSize(574, 38) 
        saved_url = current_settings.get("image_url", "")
        self.url_input.setText(saved_url)
        cl.addWidget(self.url_input, alignment=Qt.AlignCenter)
        
        # --- YENİ EKLENEN: WALLPAPER KUTUSU VE BUTONU ---
        wp_container = QWidget()
        wp_container.setFixedSize(574, 38)
        wp_inner = QHBoxLayout(wp_container)
        wp_inner.setContentsMargins(0, 0, 0, 0)
        wp_inner.setSpacing(10)
        
        self.wp_input = QLineEdit()
        self.wp_input.setPlaceholderText("Wallpaper File Path (.jpg / .png)")
        self.wp_input.setReadOnly(True)
        saved_wp = current_settings.get("wallpaper_path", "")
        self.wp_input.setText(saved_wp)
        
        self.wp_browse_btn = QPushButton("Browse")
        self.wp_browse_btn.setObjectName("SecondaryBtn")
        self.wp_browse_btn.setFixedSize(100, 38)
        self.wp_browse_btn.clicked.connect(self.browse_wallpaper)
        
        wp_inner.addWidget(self.wp_input)
        wp_inner.addWidget(self.wp_browse_btn)
        
        cl.addWidget(wp_container, alignment=Qt.AlignCenter)
        # ------------------------------------------------
        
        info_layout = QHBoxLayout()
        info_layout.setContentsMargins(10, 5, 10, 5)
        info_layout.setSpacing(25) # İki yazı arasındaki boşluk

        # Sol Taraf: Otomatik tespit edilen Yerel IP adresi
        current_ip = get_local_ip()
        ip_lbl = CensoredLabel("Server IP", current_ip)
        ip_lbl.setObjectName("SectionLabel")
        ip_lbl.setStyleSheet("color: #29B6F6; font-size: 14px; font-weight: bold;")
        
        # Sağ Taraf: Üretilen Güvenlik Tokeni
        token_lbl = CensoredLabel("Security Token", SECURITY_TOKEN)
        token_lbl.setObjectName("SectionLabel")
        token_lbl.setStyleSheet("color: #00e676; font-size: 14px; font-weight: bold;")

        # Bileşenleri yatay düzene ekle
        info_layout.addWidget(ip_lbl, alignment=Qt.AlignRight)
        info_layout.addWidget(token_lbl, alignment=Qt.AlignLeft)

        # Yatay düzeni ana dikey düzene (cl) dahil et
        cl.addLayout(info_layout)
        
        self.sync_android_btn = QPushButton("Sync") 
        self.sync_android_btn.setObjectName("SyncBtn")
        self.sync_android_btn.setFixedSize(574, 38) 
        self.sync_android_btn.clicked.connect(trigger_android_sync)
        cl.addWidget(self.sync_android_btn, alignment=Qt.AlignCenter)
        
        # self.cookie_checkbox = QCheckBox("Send Browser Cookies to Android (AES-256 Encrypted)")
        # self.cookie_checkbox.setObjectName("CookieCheckBox")
        # self.cookie_checkbox.setCursor(Qt.PointingHandCursor)
        # current_settings = load_settings()
        # self.cookie_checkbox.setChecked(current_settings.get("send_cookies", False))
        # self.cookie_checkbox.stateChanged.connect(self.save_cookie_pref)
        # cl.addWidget(self.cookie_checkbox, alignment=Qt.AlignCenter)
        
        # Alt Kısım: Checkbox'ları yan yana koymak için yatay layout
        checkbox_layout = QHBoxLayout()
        checkbox_layout.setAlignment(Qt.AlignCenter)
        checkbox_layout.setSpacing(30) # İki checkbox arası boşluk

        # 1. Tüm Sunucuları Aç/Kapat Checkbox'ı
        self.server_checkbox = QCheckBox("Enable Service")
        self.server_checkbox.setObjectName("CookieCheckBox")
        self.server_checkbox.setCursor(Qt.PointingHandCursor)
        self.server_checkbox.setChecked(False)
        self.server_checkbox.stateChanged.connect(self.toggle_server_state)
        checkbox_layout.addWidget(self.server_checkbox)

        # 2. Otomatik Başlatma Checkbox'ı
        self.startup_checkbox = QCheckBox("Auto-Start at Boot")
        self.startup_checkbox.setObjectName("CookieCheckBox")
        self.startup_checkbox.setCursor(Qt.PointingHandCursor)
        # Mevcut kayıt defteri durumunu okuyup arayüze yansıtıyoruz
        self.startup_checkbox.setChecked(check_startup_status())
        self.startup_checkbox.stateChanged.connect(self.toggle_startup_pref)
        checkbox_layout.addWidget(self.startup_checkbox)
        
        # 3. USB Kablo Modu Checkbox'ı
        self.usb_checkbox = QCheckBox("USB Mode")
        self.usb_checkbox.setObjectName("CookieCheckBox")
        self.usb_checkbox.setCursor(Qt.PointingHandCursor)
        # Ayarı diskten oku
        current_settings = load_settings()
        self.usb_mode_saved = current_settings.get("usb_mode", False)
        self.usb_checkbox.blockSignals(True)
        self.usb_checkbox.setChecked(self.usb_mode_saved)
        self.usb_checkbox.blockSignals(False)
        
        # Eğer kaydedilmiş ayar USB ise açılışta tüneli kur
        if self.usb_mode_saved:
            toggle_usb_adb_mode(True)
            
        self.usb_checkbox.stateChanged.connect(self.toggle_usb_mode)
        checkbox_layout.addWidget(self.usb_checkbox)

        # Yatay kutuyu ana ekrana (cl) ekle
        cl.addLayout(checkbox_layout)

        if saved_url:
            self._load_url_preview(saved_url)

        sep2 = QFrame(); sep2.setFrameShape(QFrame.HLine); sep2.setObjectName("Sep")
        cl.addWidget(sep2)

        apps_lbl = QLabel("Applications")
        apps_lbl.setObjectName("SectionLabel")
        apps_lbl.setAlignment(Qt.AlignCenter) 
        cl.addWidget(apps_lbl, alignment=Qt.AlignCenter)

        # İkon ızgarası
        scroll = QScrollArea()
        scroll.setObjectName("AppScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(12)
        self.grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        scroll.setWidget(self.grid_container)
        cl.addWidget(scroll)

        add_btn = QPushButton("+ Add Apps")
        add_btn.setObjectName("AddBtn")
        add_btn.setFixedHeight(40)
        add_btn.clicked.connect(self.open_add_app_dialog)
        cl.addWidget(add_btn)

        root_layout.addWidget(content, stretch=1)
        
    def toggle_server_state(self, state):
        global SERVER_ACTIVE
        if state == Qt.Checked:
            SERVER_ACTIVE = True
            
            if not hasattr(self, 'server_thread') or not self.server_thread.isRunning():
                self.server_thread = ServerThread(signals=self.app_signals)
                self.server_thread.start()
            if not hasattr(self, 'udp_thread') or not self.udp_thread.isRunning():
                self.udp_thread = UdpServerThread()
                self.udp_thread.start()
            if not hasattr(self, 'http_thread') or not self.http_thread.isRunning():
                self.http_thread = ExtensionServerThread()
                self.http_thread.start()
                
            # SUNUCU AÇIKKEN USB AYARINI DEĞİŞTİRMEYİ YASAKLA
            self.usb_checkbox.setEnabled(False)
            
            self.toggle_server_action.setText("Deactivate")
            print("[uDesk] Tüm sunucular AKTİF.")
        else:
            SERVER_ACTIVE = False
            
            if hasattr(self, 'server_thread'): self.server_thread.stop()
            if hasattr(self, 'udp_thread'): self.udp_thread.stop()
            if hasattr(self, 'http_thread'): self.http_thread.stop()
            
            # SUNUCU KAPANDIĞINDA KİLİDİ AÇ Kİ KULLANICI DEĞİŞTİREBİLSİN
            self.usb_checkbox.setEnabled(True)
            
            self.toggle_server_action.setText("Activate")
            print("[uDesk] Tüm sunucular DURDURULDU.")
            
    def toggle_startup_pref(self, state):
        is_checked = (state == Qt.Checked)
        success = set_startup_status(is_checked)
        
        if not success:
            QMessageBox.warning(self, "Hata", "Başlangıç ayarı değiştirilemedi. Yönetici izinleri gerekebilir.")
            # Başarısız olursa tiki eski haline getir
            self.startup_checkbox.blockSignals(True)
            self.startup_checkbox.setChecked(not is_checked)
            self.startup_checkbox.blockSignals(False)
            
    def toggle_usb_mode(self, state):
        is_checked = (state == Qt.Checked)
        
        # Eğer aktif ediliyorsa ADB komutunu test et
        if is_checked:
            success = toggle_usb_adb_mode(True)
            if not success:
                QMessageBox.critical(
                    self, 
                    "ADB Not Found", 
                    "The 'adb' (Android Debug Bridge) command was not found on your system.\n\n"
                    "To use the USB Mode feature, please install the Android SDK Platform-Tools or simply place 'adb.exe' in the same folder as this application."
                )
                self.usb_checkbox.blockSignals(True)
                self.usb_checkbox.setChecked(False)
                self.usb_checkbox.blockSignals(False)
                return # Kurulum başarısız, kaydetme ve yeniden başlatma
                
        # Başarılı ise veya devre dışı bırakılıyorsa ayarı kaydet
        settings = load_settings()
        settings["usb_mode"] = is_checked
        save_settings(settings)
        
        if is_checked:
            QMessageBox.information(
                self, 
                "USB Mode - Restarting...", 
                "USB Connection Mode is now enabled!\n\nThe application will restart to apply the new network configurations.\n\n"
                "Please remember to:\n"
                "1. Enable 'Developer Options' and 'USB Debugging' on your Android device.\n"
                "2. Connect your phone via USB.\n"
                "3. Enable 'USB Mode' in the uDesk Android app."
            )
        else:
            QMessageBox.information(
                self,
                "Wi-Fi Mode - Restarting...",
                "USB Mode disabled. The application will restart to switch back to standard Wi-Fi mode."
            )
            
        # Ayar uygulandı, sıfırdan temiz başlangıç yap!
        self.restart_app()

    def _load_url_preview(self, url: str):
        if not url:
            self.url_preview.setText("GIF veya resim önizlemesi burada görünecek")
            return
        req = QNetworkRequest(QUrl(url))
        req.setAttribute(QNetworkRequest.Attribute(0), url.lower().endswith(".gif"))
        self._net_manager.get(req)

    def _on_url_image_loaded(self, reply):
        import tempfile
        data = reply.readAll()
        is_gif = reply.request().attribute(QNetworkRequest.Attribute(0))
        if is_gif:
            tmp = tempfile.NamedTemporaryFile(suffix=".gif", delete=False)
            tmp.write(bytes(data)); tmp.close()
            self._gif_movie = QMovie(tmp.name)
            self._gif_movie.setScaledSize(self.url_preview.size())
            self.url_preview.setMovie(self._gif_movie)
            self._gif_movie.start()
        else:
            px = QPixmap()
            px.loadFromData(data)
            if not px.isNull():
                self.url_preview.setPixmap(px)
            else:
                self.url_preview.setText("Görüntü yüklenemedi")

    def update_screenshot_preview(self, pixmap: QPixmap):
        self.screenshot_preview.setPixmap(pixmap)

    def start_snipping(self):
        self.hide()
        self.snipper = Snipper(self)
        self.snipper.show()

    def save_media_url(self):
        url = self.url_input.text().strip()
        settings = load_settings()
        settings["image_url"] = url
        if save_settings(settings):
            self._load_url_preview(url)
            QMessageBox.information(self, "Başarılı", "Medya URL'si kaydedildi.")
        else:
            QMessageBox.critical(self, "Hata", "URL kaydedilemedi.")
            
    def open_mod_editor(self):
        # Eski karmaşık base_dir hesaplamasını tamamen siliyoruz
        exe_path = os.path.join(BASE_DIR, "uDeskModEditor.exe")
        pyw_path = os.path.join(BASE_DIR, "uDeskModEditor.pyw")

        try:
            if os.path.exists(exe_path):
                os.startfile(exe_path)
            elif os.path.exists(pyw_path):
                os.startfile(pyw_path)
            else:
                QMessageBox.warning(self, "Hata", f"Mod Editörü bulunamadı!\nAranan yol: {exe_path}")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Editör başlatılamadı: {e}")
            
  # def save_cookie_pref(self, state):
    #     settings = load_settings()
    #     settings["send_cookies"] = (state == Qt.Checked)
    #     save_settings(settings)
        
    def browse_wallpaper(self):
        fp, _ = QFileDialog.getOpenFileName(self, "Select Wallpaper", "", "Image Files (*.png *.jpg *.jpeg)")
        if fp:
            self.wp_input.setText(fp)
            settings = load_settings()
            settings["wallpaper_path"] = fp
            save_settings(settings)
            trigger_android_sync()

    def open_add_app_dialog(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Add Apps")
        dlg.setFixedWidth(400)
        dlg.setStyleSheet(self.styleSheet())
        layout = QVBoxLayout(dlg)
        layout.setSpacing(10)
        name_in = QLineEdit(); name_in.setPlaceholderText("App Name")
        path_in = QLineEdit(); path_in.setPlaceholderText("Folder path (.exe / .lnk)"); path_in.setReadOnly(True)
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(lambda: self._browse_and_set(path_in))
        ok_btn = QPushButton("Add"); ok_btn.setObjectName("AccentBtn")
        ok_btn.clicked.connect(lambda: self._confirm_add(dlg, name_in.text(), path_in.text()))
        lbl_name = QLabel("Name:"); lbl_path = QLabel("Path:")
        layout.addWidget(lbl_name); layout.addWidget(name_in)
        layout.addWidget(lbl_path)
        row = QHBoxLayout(); row.addWidget(path_in); row.addWidget(browse_btn)
        layout.addLayout(row); layout.addWidget(ok_btn)
        dlg.exec_()

    def _browse_and_set(self, path_in):
        fp, _ = QFileDialog.getOpenFileName(self, "Select App", "", "App Files (*.exe *.lnk);;All Files (*)")
        if fp: path_in.setText(fp)

    def _confirm_add(self, dlg, name, path):
        name = name.strip(); path = path.strip()
        if not name or not path:
            QMessageBox.warning(dlg, "Error", "Both name and file path are required."); return

        if "!" in path and not path.startswith("shell:AppsFolder\\") and "\\" not in path:
            path = f"shell:AppsFolder\\{path}"

        if not path.startswith("shell:") and not os.path.exists(path):
            QMessageBox.warning(dlg, "Error", "The selected file could not be found."); return

        apps = load_apps(); apps[name] = path

        if save_apps(apps):
            dlg.accept()
            self.refresh_grid()
        else:
            QMessageBox.critical(dlg, "Error", "Failed to save the application.")

    def refresh_grid(self):
        global APP_ICONS_CACHE, CACHED_APPS_LIST
        
        # Sadece önbelleği temizleme kısmını kilitliyoruz
        with CACHE_LOCK:
            CACHED_APPS_LIST = None
            APP_ICONS_CACHE.clear()

        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()

        apps = load_apps()
        provider = QFileIconProvider()
        import comtypes.client

        COLS = 6
        for idx, (name, path) in enumerate(apps.items()):
            r, c = divmod(idx, COLS)
            icon_px = QPixmap()
            try:
                icon_path = path
                if path.lower().endswith(".lnk"):
                    try:
                        shell = comtypes.client.CreateObject("WScript.Shell")
                        sc = shell.CreateShortCut(path)
                        t = sc.TargetPath
                        if t and os.path.exists(t): icon_path = t
                    except: pass
                
                if os.path.exists(icon_path):
                    ico = provider.icon(QFileInfo(icon_path))
                    if not ico.isNull():
                        icon_px = ico.pixmap(48, 48)
                        ba = QByteArray()
                        buf = QBuffer(ba)
                        buf.open(QIODevice.WriteOnly)
                        icon_px.save(buf, "PNG")
                        
                        # İkonu yazarken de kilitliyoruz
                        with CACHE_LOCK:
                            APP_ICONS_CACHE[name] = ba.toBase64().data().decode("utf-8")
                    else: 
                        with CACHE_LOCK: APP_ICONS_CACHE[name] = ""
                else: 
                    with CACHE_LOCK: APP_ICONS_CACHE[name] = ""
            except: 
                with CACHE_LOCK: APP_ICONS_CACHE[name] = ""

            # Kart
            card = QWidget()
            card.setObjectName("AppCard")
            card.setFixedSize(88, 88)
            card_l = QVBoxLayout(card)
            card_l.setContentsMargins(6, 8, 6, 4)
            card_l.setSpacing(4)

            ico_lbl = QLabel()
            ico_lbl.setAlignment(Qt.AlignCenter)
            if not icon_px.isNull():
                ico_lbl.setPixmap(icon_px.scaled(38, 38, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                ico_lbl.setText("?")

            name_lbl = QLabel(name)
            name_lbl.setObjectName("AppCardName")
            name_lbl.setAlignment(Qt.AlignCenter)
            name_lbl.setFixedWidth(76)
            name_lbl.setWordWrap(False)

            card_l.addWidget(ico_lbl)
            card_l.addWidget(name_lbl)

            # Kaldır butonu — üst sağ köşe overlay
            rm_btn = QPushButton("x", card)
            rm_btn.setObjectName("RemoveBtn")
            rm_btn.setFixedSize(18, 18)
            rm_btn.move(68, 2)
            rm_btn.clicked.connect(lambda _checked, n=name: self._remove_app(n))

            self.grid_layout.addWidget(card, r, c)

    def _remove_app(self, name):
        apps = load_apps()
        if name in apps:
            del apps[name]
            if save_apps(apps): self.refresh_grid()

    def apply_dark_theme(self):
        self.setStyleSheet("""
            QMainWindow, QWidget { background-color: #0c0c0c; color: #e0e0e0; }

            #Navbar { background-color: #101010; border-bottom: 1px solid #1e1e1e; }
            #NavLogo { color: #fff; font-size: 17px; font-weight: bold; letter-spacing: 2px; background: transparent; font-family: "Orbitron"; }
            #VersionLabel { color: #666; font-size: 10px; background: transparent;}

            #PreviewLabel {
                background-color: #141414; 
                border: 2px solid #2a2a2a; 
                border-radius: 0px; 
                color: #555; 
                font-size: 12px;
                font-weight: bold;
            }
            #PreviewLabel:hover { border-color: #3a3a3a; }
            
            #ModEditorBtn {
                background-color: #1a1a1a;
                color: #60ffffff;
                border: 1px solid #333;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
                padding: 0px 4px;
            }
            #ModEditorBtn:hover {
                background-color: #222;
                border-color: #fff;
                color: #fff;
            }
            
            #CookieCheckBox {
                color: #888;
                font-size: 12px;
                font-weight: bold;
                spacing: 8px; /* Kutu ile yazı arasındaki boşluk */
            }
            #CookieCheckBox:hover {
                color: #bbb;
            }
            #CookieCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #333;
                border-radius: 4px;
                background-color: #141414;
            }
            #CookieCheckBox::indicator:hover {
                border-color: #555;
                background-color: #1a1a1a;
            }
            #CookieCheckBox::indicator:checked {
                background-color: #0b2e24; 
                border: 1px solid #00e676; 
                image: url("data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjMDBlNjc2IiBzdHJva2Utd2lkdGg9IjQiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCI+PHBvbHlsaW5lIHBvaW50cz0iMjAgNiA5IDE3IDQgMTIiPjwvcG9seWxpbmU+PC9zdmc+");            
            }
            
            #SyncBtn {
                background-color: #0b2e24;
                color: #00e676;
                border: 1px solid #00c853;
                font-weight: bold;
                border-radius: 6px;
            }
            #SyncBtn:hover {
                background-color: #0d3c2f;
                border-color: #00e676;
            }
            #SyncBtn:pressed {
                background-color: #051712; 
                border-color: #009e4d;
                color: #00b359;
            }

            #SectionLabel { color: #5e5e5e; font-size: 11px; font-weight: bold; }
            #Sep { color: #1e1e1e; }

            QScrollArea, #AppScroll { background: transparent; border: none; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
                QScrollBar:vertical { 
                background: #0c0c0c; 
                width: 6px; 
                border-radius: 3px;
            }
            QScrollBar::groove:vertical { 
                background: #0c0c0c; 
                border-radius: 3px; 
            }
            QScrollBar::handle:vertical { 
                background: #3a3a3a; 
                border-radius: 3px; 
                min-height: 30px; 
            }
            QScrollBar::handle:vertical:hover { 
                background: #555; 
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { 
                height: 0; 
                background: none; 
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { 
                background: none; 
            }

            #AppCard {
                background: transparent; border: 1px solid #1e1e1e; border-radius: 10px;
            }
            #AppCard:hover { border-color: #333; background: transparent; }
            #AppCardName { color: #666; font-size: 11px; background: transparent;}

            #RemoveBtn {
                background-color: #1a1a1a; color: #444; border: none;
                border-radius: 9px; font-size: 12px; font-weight: bold;padding: 0px;
            }
            #RemoveBtn:hover { background-color: #7f1e1e; color: #fff; }

            QPushButton {
                background-color: #141414; color: #888; border: 1px solid #1e1e1e;
                border-radius: 6px; padding: 8px 14px; font-size: 13px;
            }
            QPushButton:hover { background-color: #1a1a1a; color: #ccc; }

            #AccentBtn {
                background-color: #0e2030; color: #29b6f6;
                border: 1px solid #1a4a6a; font-weight: bold;
                padding: 10px; border-radius: 8px;
            }
            #AccentBtn:hover { background-color: #142838; border-color: #29b6f6; }

            #SecondaryBtn {
                background-color: #1a1a1a; color: #aaa;
                border: 1px solid #333; font-weight: bold;
                padding: 10px; border-radius: 8px;
            }
            #SecondaryBtn:hover { background-color: #222; color: #fff; border-color: #555; }

            #AddBtn {
                background-color: #252525; color: #b3b3b3;
                border: 1px dashed #666; font-weight: bold;
                padding: 10px; border-radius: 8px; font-size: 13px;
            }
            #AddBtn:hover { color: #999; border-color: #555; background-color: #181818; }

            QLineEdit {
                background-color: #111; color: #ccc;
                border: 1px solid #1e1e1e; border-radius: 6px; padding: 8px 10px;
            }
            QLineEdit:focus { border-color: #29b6f6; }

            QDialog { background-color: #0c0c0c; }
            QLabel { color: #666; font-size: 12px; }
        """)
        css_base = BASE_DIR.replace('\\', '/')
        self.setStyleSheet(self.styleSheet() + f"""
            #CookieCheckBox::indicator:checked {{
                background-color: #0b2e24; 
                border: 1px solid #00e676; 
                image: url({css_base}/tick.svg);
            }}
        """)
        
    def changeEvent(self, event):
        if event.type() == QEvent.WindowStateChange:
            if self.isMinimized():
                self.hide()
                event.ignore()
                return
        super().changeEvent(event)

    def tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.showNormal()
            self.activateWindow()

    def closeEvent(self, event):
        self.quit_app()
        event.accept()

    def restart_app(self):
        print("[uDesk] Yeniden başlatılıyor...")
        try:
            subprocess.run(["adb", "reverse", "--remove-all"], creationflags=subprocess.CREATE_NO_WINDOW)
        except:
            pass
            
        global MOUSE_MODE_ACTIVE
        if MOUSE_MODE_ACTIVE:
            toggle_mouse_mode()
            
        show_system_cursor()
        try: keyboard.unhook_all()
        except: pass
        
        if hasattr(self, 'tray_icon'):
            try: self.tray_icon.hide()
            except: pass
            
        if hasattr(self, 'server_thread'): self.server_thread.stop()
        if hasattr(self, 'udp_thread'): self.udp_thread.stop()
        if hasattr(self, 'http_thread'): self.http_thread.stop()
        
        global AUDIO_HELPER_PROCESS
        if AUDIO_HELPER_PROCESS is not None:
            try: AUDIO_HELPER_PROCESS.terminate()
            except: pass

        QApplication.quit()
        
        # Yeni bir uygulama örneği (instance) başlat ve eskisini komple öldür
        subprocess.Popen([sys.executable] + sys.argv)
        os._exit(0)
    
    def quit_app(self):
        print("[uDesk] Kapanış başlatıldı, süreçler temizleniyor...")
        
        try:
            subprocess.run(["adb", "reverse", "--remove-all"], creationflags=subprocess.CREATE_NO_WINDOW)
        except:
            pass
        
        global MOUSE_MODE_ACTIVE
        if MOUSE_MODE_ACTIVE:
            toggle_mouse_mode()
            
        show_system_cursor()
            
        try: keyboard.unhook_all()
        except: pass
        
        if hasattr(self, 'tray_icon'):
            try: self.tray_icon.hide()
            except: pass
        
        if hasattr(self, 'server_thread'): self.server_thread.stop()
        if hasattr(self, 'udp_thread'): self.udp_thread.stop()
        if hasattr(self, 'http_thread'): self.http_thread.stop()
        
        global AUDIO_HELPER_PROCESS
        if AUDIO_HELPER_PROCESS is not None:
            try: AUDIO_HELPER_PROCESS.terminate()
            except: pass

        QApplication.quit()

        import os
        os._exit(0)

class CensoredLabel(QLabel):
    def __init__(self, prefix, secret_value, parent=None):
        super().__init__(parent)
        self.prefix = prefix
        self.secret_value = str(secret_value)
        self.censored_text = "•" * len(self.secret_value) 
        
        self.is_censored = True 
        self.update_text()
        
        self.setCursor(Qt.PointingHandCursor)

    def update_text(self):
        if self.is_censored:
            self.setText(f"{self.prefix}: {self.censored_text}")
        else:
            self.setText(f"{self.prefix}: {self.secret_value}")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.is_censored = not self.is_censored
            self.update_text()
        
        super().mousePressEvent(event)
        
if __name__ == "__main__":
    myappid = 'ugz.udesk.desktop'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    keyboard.add_hotkey('ctrl+shift+alt', lambda: window.app_signals.safe_execute.emit(toggle_mouse_mode))
    app = QApplication(sys.argv)
    window = UDeskUI()          
    window.tray_icon.showMessage(
        "uDesk",
        "uDesk is running in the background.",
        QSystemTrayIcon.Information,
        1500
    )
    sys.exit(app.exec_())
import sys
import os
import subprocess
import webbrowser
import keyboard

# ──────────────────────────────────────────────
# PYINSTALLER ONEDIR UYUMLU KÖK DİZİN TESPİTİ
# ──────────────────────────────────────────────
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Pygame Karşılama Mesajını Gizle
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"


def get_initial_state(action_data):
    if not action_data: return False
    
    action_type = action_data.get("type")
    
    # ──────────────────────────────────────────────
    # SİSTEM KONTROLLERİ (Ses / Mikrofon Durumu)
    # ──────────────────────────────────────────────
    if action_type == "system":
        command = action_data.get("command")
        
        try:
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            
            # STRINGLER İNGİLİZCEYE ÇEVRİLDİ (Editörle uyumlu)
            if command == "Mute/Unmute Audio":
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                volume = cast(interface, POINTER(IAudioEndpointVolume))
                return volume.GetMute()
                
            elif command == "Mute/Unmute Microphone":
                for device in AudioUtilities.GetAllDevices():
                    if device.DataFlow == 1 and device.State == 1:
                        interface = device.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                        volume = cast(interface, POINTER(IAudioEndpointVolume))
                        return volume.GetMute()
        except Exception:
            pass
            
    # ──────────────────────────────────────────────
    # KISAYOL KONTROLLERİ (Hafızadaki Toggle Durumu)
    # ──────────────────────────────────────────────
    elif action_type == "shortcut":
        keys = action_data.get("keys")
        return shortcut_states.get(keys, False)
        
    return False

# --- Pygame Mikser Ayarları ---
_mixer_ready = False
def _ensure_mixer():
    global _mixer_ready
    if not _mixer_ready:
        import pygame
        pygame.mixer.init()
        pygame.mixer.set_num_channels(16)
        _mixer_ready = True

shortcut_states = {}

def execute_action(action_data):
    """
    Android'den gelen veya okunan JSON içindeki 'action' bloğunu çalıştırır.
    Eğer eylem sonucunda Android'e bir LED ışık durumu (True/False) dönmesi gerekiyorsa döndürür.
    """
    if not action_data:
        return None

    action_type = action_data.get("type")
    
    # ──────────────────────────────────────────────
    # 1. SİSTEM KONTROLLERİ
    # ──────────────────────────────────────────────
    if action_type == "system":
        command = action_data.get("command")
        
        # STRINGLER İNGİLİZCEYE ÇEVRİLDİ
        if command == "Mute/Unmute Audio":
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            new_state = not volume.GetMute()
            volume.SetMute(new_state, None)
            return new_state 
            
        elif command == "Mute/Unmute Microphone":
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            
            for device in AudioUtilities.GetAllDevices():
                if device.DataFlow == 1 and device.State == 1:
                    interface = device.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                    volume = cast(interface, POINTER(IAudioEndpointVolume))
                    new_state = not volume.GetMute()
                    volume.SetMute(new_state, None)
                    return new_state 
            return False
            
        elif command == "Sleep Mode":
            os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
        elif command == "Lock":
            os.system("rundll32.exe user32.dll,LockWorkStation")
        elif command == "Shut Down":
            os.system("shutdown /s /t 0")
        elif command == "Restart":
            os.system("shutdown /r /t 0")

    # ──────────────────────────────────────────────
    # 2. KISAYOL TETİKLEME
    # ──────────────────────────────────────────────
    elif action_type == "shortcut":
        keys = action_data.get("keys")
        if keys:
            import time
            try:
                key_list = [k.strip() for k in keys.split("+")]
                for key in key_list:
                    keyboard.press(key)
                
                time.sleep(0.15)
                
                for key in reversed(key_list):
                    keyboard.release(key)
            except Exception as e:
                keyboard.send(keys)

            current_state = shortcut_states.get(keys, False)
            new_state = not current_state
            shortcut_states[keys] = new_state
            return new_state

    # ──────────────────────────────────────────────
    # 3. UYGULAMA VEYA KLASÖR BAŞLATMA
    # ──────────────────────────────────────────────
    elif action_type == "launch":
        path = action_data.get("path")
        if path and os.path.exists(path):
            os.startfile(path) 

    # ──────────────────────────────────────────────
    # 4. WEB SİTESİ AÇMA
    # ──────────────────────────────────────────────
    elif action_type == "website":
        url = action_data.get("url", "")
        # Varsayılan "Default" olarak değiştirildi
        browser = action_data.get("browser", "Default")
        is_private = action_data.get("private", False)
        
        if not url.startswith("http"):
            url = "https://" + url
            
        if browser == "Default" and not is_private:
            webbrowser.open(url)
        else:
            browser_map = {
                "Chrome": ("chrome", "--incognito"),
                "Edge": ("msedge", "-inprivate"),
                "Opera": ("opera", "--private"),
                "Firefox": ("firefox", "-private-window"),
                "Default": ("chrome", "--incognito") 
            }
            
            exe_name, priv_flag = browser_map.get(browser, ("chrome", "--incognito"))
            
            if is_private:
                subprocess.Popen(["start", exe_name, priv_flag, url], shell=True)
            else:
                subprocess.Popen(["start", exe_name, url], shell=True)

    # ──────────────────────────────────────────────
    # 5. SES OYNATMA (Launchpad Sistemi)
    # ──────────────────────────────────────────────
    elif action_type == "sound":
        file_name = action_data.get("file")
        if file_name and file_name != "Klasörde ses yok" and file_name != "No sounds in folder":
            _ensure_mixer()
            import pygame
            # __file__ SİLİNDİ, BASE_DIR EKLENDİ
            sound_path = os.path.join(BASE_DIR, "sounds", file_name)
            
            if os.path.exists(sound_path):
                sound = pygame.mixer.Sound(sound_path)
                sound.play()

    return None
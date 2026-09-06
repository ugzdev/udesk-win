import subprocess
import time
import sys
import os
import ctypes

def restore_system_cursor():
    """Restores standard Windows system cursors in case they were left hidden."""
    try:
        # 0x0057 = SPI_SETCURSORS
        ctypes.windll.user32.SystemParametersInfoW(0x0057, 0, None, 0)
    except Exception as e:
        print(f"[Watchdog] Warning: Could not restore cursor. {e}")

def start_watchdog():
    # --- TEK KOPYA (SINGLE INSTANCE) KORUMASI ---
    mutex_name = "uDesk_Watchdog_Mutex_UGZ"
    # Windows'tan 'mutex_name' adında benzersiz bir kilit talep et
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
    
    # 183 (ERROR_ALREADY_EXISTS): Eğer kilit zaten başka bir uDesk tarafından alınmışsa
    if ctypes.windll.kernel32.GetLastError() == 183:
        print("[Watchdog] uDesk is already running! Exiting silently...")
        sys.exit(0) # Hiçbir şey yapmadan sessizce kapan
    # ----------------------------------------------

    # 1. Get the absolute path
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    # 2. Create absolute paths
    exe_path = os.path.join(base_dir, "uDesk.exe")
    pyw_path = os.path.join(base_dir, "uDesk.pyw")

    # 3. File Type Check
    if os.path.exists(exe_path):
        executable_cmd = [exe_path]
    elif os.path.exists(pyw_path):
        executable_cmd = [sys.executable, pyw_path]
    else:
        print(f"[Watchdog] Error: Could not find uDesk.exe or uDesk.pyw in {base_dir}")
        time.sleep(5)
        return

    is_first_run = True

    while True:
        current_cmd = list(executable_cmd)
        
        # İlk açılış DEĞİLSE, kurtarma parametresini ekle
        if not is_first_run:
            current_cmd.append("--recovery")
            
        print(f"[Watchdog] Starting: {current_cmd}")
        process = subprocess.Popen(current_cmd)
        
        process.wait() 
        exit_code = process.returncode
        
        # Kullanıcı uygulamayı güvenli kapattıysa Mutex serbest kalacak ve watchdog kapanacak
        if exit_code == 0:
            print("[Watchdog] User closed the application safely. Terminating...")
            break 
            
        print(f"[Watchdog] uDesk crashed unexpectedly! Error Code: {exit_code}")
        print("[Watchdog] Restoring system cursor...")
        restore_system_cursor()
        
        print("[Watchdog] Restarting in 1 second...")
        time.sleep(1)
        
        is_first_run = False 

if __name__ == "__main__":
    start_watchdog()
import sys
import ctypes
import os
import tempfile
import subprocess
import requests
import winreg
import shutil
import time
import logging
import json

LOG_FILE = "talon.txt"
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

def log(message):
    logging.info(message)
    print(message)

def show_error_message(message):
    ctypes.windll.user32.MessageBoxW(0, message, "Error", 0x10)

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if not is_admin():
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, " ".join(sys.argv), None, 1
    )
    sys.exit(0)

def apply_registry_changes():
    log("Applying registry changes...")
    try:
        registry_modifications = [
            # Visual changes
            (winreg.HKEY_CURRENT_USER, r"Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced", "TaskbarAl", winreg.REG_DWORD, 0), # Align taskbar to the left
            (winreg.HKEY_CURRENT_USER, r"Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize", "AppsUseLightTheme", winreg.REG_DWORD, 0), # Set Windows to dark theme
            (winreg.HKEY_CURRENT_USER, r"Software\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize", "SystemUsesLightTheme", winreg.REG_DWORD, 0), # Set Windows to dark theme
            (winreg.HKEY_CURRENT_USER, r"Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Accent", "AccentColorMenu", winreg.REG_DWORD, 1), # Makes accent color the color of the taskbar and start menu (1)  --.
            (winreg.HKEY_CURRENT_USER, r"Software\\Microsoft\\Windows\\CurrentVersion\\Themes\Personalize", "ColorPrevalence", winreg.REG_DWORD, 1), # Makes accent color the color of the taskbar and start menu (2)   |-- These are redundant. I know
            (winreg.HKEY_CURRENT_USER, r"Software\\Microsoft\\Windows\\DWM", "AccentColorInStartAndTaskbar", winreg.REG_DWORD, 1), # Makes accent color the color of the taskbar and start menu (3)                   --'
            (winreg.HKEY_CURRENT_USER, r"Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Accent", "AccentPalette", winreg.REG_BINARY, b"\x00" * 32), # Makes the taskbar black
            (winreg.HKEY_CURRENT_USER, r"Software\\Microsoft\\Windows\\CurrentVersion\\GameDVR", "AppCaptureEnabled", winreg.REG_DWORD, 0), #Fix the  Get an app for 'ms-gamingoverlay' popup
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\\Microsoft\\PolicyManager\\default\\ApplicationManagement\\AllowGameDVR", "Value", winreg.REG_DWORD, 0), # Disable Game DVR (Reduces FPS Drops)
            (winreg.HKEY_CURRENT_USER, r"Control Panel\\Desktop", "MenuShowDelay", winreg.REG_SZ, "0"),# Reduce menu delay for snappier UI
            (winreg.HKEY_CURRENT_USER, r"Control Panel\\Desktop\\WindowMetrics", "MinAnimate", winreg.REG_DWORD, 0),# Disable minimize/maximize animations
            (winreg.HKEY_CURRENT_USER, r"Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced", "ExtendedUIHoverTime", winreg.REG_DWORD, 1),# Reduce hover time for tooltips and UI elements
            (winreg.HKEY_CURRENT_USER, r"Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced", "HideFileExt", winreg.REG_DWORD, 0),# Show file extensions in Explorer (useful for security and organization)
        ]
        for root_key, key_path, value_name, value_type, value in registry_modifications:
            try:
                with winreg.CreateKeyEx(root_key, key_path, 0, winreg.KEY_SET_VALUE) as key:
                    winreg.SetValueEx(key, value_name, 0, value_type, value)
                    log(f"Applied {value_name} to {key_path}")
            except Exception as e:
                error_message = f"Failed to modify {value_name} in {key_path}: {e}"
                log(error_message)
                show_error_message(error_message)
        log("Registry changes applied successfully.")
        subprocess.run(["taskkill", "/F", "/IM", "explorer.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["start", "explorer.exe"], shell=True)
        log("Explorer restarted to apply registry changes.")
        run_edge_vanisher()
        log("Edge Vanisher started successfully")
        
    except Exception as e:
        error_message = f"Error applying registry changes: {e}"
        log(error_message)
        show_error_message(error_message)

def download_file_with_retries(url, target_path, retries=3, timeout=10):
    for attempt in range(retries):
        try:
            log(f"Downloading {url} (Attempt {attempt + 1}/{retries})...")
            response = requests.get(url, stream=True, timeout=timeout)
            if response.status_code == 200:
                with open(target_path, "wb") as file:
                    for chunk in response.iter_content(chunk_size=8192):
                        file.write(chunk)
                log(f"Download complete: {target_path}")
                return True
            else:
                log(f"Download failed with status code: {response.status_code}")
        except Exception as e:
            log(f"Download attempt {attempt + 1} failed: {e}")
            time.sleep(3)
    log(f"Failed to download {url} after {retries} attempts.")
    show_error_message(f"Failed to download {url} after {retries} attempts.")
    return False

def run_edge_vanisher():
    log("Starting Edge Vanisher script execution...")
    try:
        script_url = "https://raw.githubusercontent.com/ravendevteam/talon-blockedge/refs/heads/main/edge_vanisher.ps1"
        temp_dir = tempfile.gettempdir()
        script_path = os.path.join(temp_dir, "edge_vanisher.ps1")
        log(f"Target script path: {script_path}")
        
        if download_file_with_retries(script_url, script_path):
            powershell_command = (
                f"Set-ExecutionPolicy Bypass -Scope Process -Force; "
                f"& '{script_path}'; exit" 
            )
            log(f"Executing PowerShell command: {powershell_command}")
            
            process = subprocess.run(
                ["powershell", "-Command", powershell_command],
                capture_output=True,
                text=True
            )
            
            if process.returncode == 0:
                log("Edge Vanisher execution completed successfully")
                log(f"Process output: {process.stdout}")
                run_oouninstall()
            else:
                log(f"Edge Vanisher execution failed with return code: {process.returncode}")
                log(f"Process error: {process.stderr}")
                run_oouninstall()
            
    except requests.exceptions.RequestException as e:
        error_message = f"Network error during Edge Vanisher script download: {str(e)}"
        log(error_message)
        show_error_message(error_message)
        run_oouninstall()
    except IOError as e:
        error_message = f"File I/O error while saving Edge Vanisher script: {str(e)}"
        log(error_message)
        show_error_message(error_message)
        run_oouninstall()
    except Exception as e:
        error_message = f"Unexpected error during Edge Vanisher execution: {str(e)}"
        log(error_message)
        show_error_message(error_message)
        run_oouninstall()

def run_oouninstall():
    log("Starting Office Online uninstallation process...")
    try:
        script_url = "https://raw.githubusercontent.com/ravendevteam/oouninstaller/refs/heads/main/uninstall_oo.ps1"
        temp_dir = tempfile.gettempdir()
        script_path = os.path.join(temp_dir, "uninstall_oo.ps1")
        log(f"Target script path: {script_path}")
        
        if download_file_with_retries(script_url, script_path):
            powershell_command = f"Set-ExecutionPolicy Bypass -Scope Process -Force; & '{script_path}'"
            log(f"Executing PowerShell command: {powershell_command}")
            
            process = subprocess.run(
                ["powershell", "-Command", powershell_command],
                capture_output=True,
                text=True
            )
            
            if process.returncode == 0:
                log("Office Online uninstallation completed successfully")
                log(f"Process stdout: {process.stdout}")
                run_tweaks()
            else:
                log(f"Office Online uninstallation failed with return code: {process.returncode}")
                log(f"Process stderr: {process.stderr}")
                run_tweaks()
            
    except Exception as e:
        error_message = f"Unexpected error during OO uninstallation: {str(e)}"
        log(error_message)
        show_error_message(error_message)
        run_tweaks()

def run_tweaks():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    if not is_admin():
        log("Must be run as an administrator.")
        show_error_message("Must be run as an administrator.")
        sys.exit(1)

    try:
        config_url = "https://raw.githubusercontent.com/ravendevteam/talon/refs/heads/main/barebones.json"
        log(f"Downloading config from: {config_url}")
        temp_dir = tempfile.gettempdir()
        json_path = os.path.join(temp_dir, "custom_config.json")
        
        if download_file_with_retries(config_url, json_path):
            log("Config file saved successfully.")
            run_applybackground()
        else:
            log("Failed to download or save the configuration file.")
            show_error_message("Failed to download or save the configuration file.")
            
    except requests.exceptions.RequestException as e:
        log(f"Network error: {e}")
        show_error_message(f"Network error: {e}")
    except Exception as e:
        log(f"Unexpected error: {e}")
        show_error_message(f"Unexpected error: {e}")

def run_applybackground():
    log("Apply background change...")

if __name__ == "__main__":
    apply_registry_changes()

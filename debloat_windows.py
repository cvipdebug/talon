import sys
import ctypes
import os
import tempfile
import subprocess
import requests
import winreg
import logging
import json
import time

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
    """Display an error message box using ctypes."""
    ctypes.windll.user32.MessageBoxW(0, message, "Error", 1)

def download_file(url, save_path):
    """Download a file with retry logic."""
    for attempt in range(3):
        try:
            log(f"Downloading from {url} (Attempt {attempt + 1}/3)...")
            response = requests.get(url, stream=True, timeout=10)
            if response.status_code == 200:
                with open(save_path, "wb") as file:
                    for chunk in response.iter_content(chunk_size=8192):
                        file.write(chunk)
                log(f"Download complete: {save_path}")
                return True
            else:
                log(f"Download failed with status code: {response.status_code}")
        except Exception as e:
            log(f"Download attempt {attempt + 1} failed: {e}")
            time.sleep(3)

    # If all attempts fail, show an error message and log the failure
    error_message = f"Failed to download file from {url} after 3 attempts."
    log(error_message)
    show_error_message(error_message)  # Use ctypes to show the error message
    return False

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
                log(f"Failed to modify {value_name} in {key_path}: {e}")
        log("Registry changes applied successfully.")
        subprocess.run(["taskkill", "/F", "/IM", "explorer.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["start", "explorer.exe"], shell=True)
        log("Explorer restarted to apply registry changes.")
        run_edge_vanisher()
        log("Edge Vanisher started successfully")
        
    except Exception as e:
        log(f"Error applying registry changes: {e}")

def run_edge_vanisher():
    log("Starting Edge Vanisher script execution...")
    try:
        script_url = "https://raw.githubusercontent.com/ravendevteam/talon-blockedge/refs/heads/main/edge_vanisher.ps1"
        temp_dir = tempfile.gettempdir()
        script_path = os.path.join(temp_dir, "edge_vanisher.ps1")
        
        if download_file(script_url, script_path):
            log("Edge Vanisher script successfully saved to disk")
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
        else:
            run_oouninstall()
            
    except Exception as e:
        log(f"Unexpected error during Edge Vanisher execution: {str(e)}")
        run_oouninstall()

def run_oouninstall():
    log("Starting Office Online uninstallation process...")
    try:
        script_url = "https://raw.githubusercontent.com/ravendevteam/oouninstaller/refs/heads/main/uninstall_oo.ps1"
        temp_dir = tempfile.gettempdir()
        script_path = os.path.join(temp_dir, "uninstall_oo.ps1")
        
        if download_file(script_url, script_path):
            log("OO uninstall script successfully saved to disk")
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
                log(f"Process stdout: {process.stdout}")
                run_tweaks()
        else:
            run_tweaks()
            
    except Exception as e:
        log(f"Unexpected error during OO uninstallation: {str(e)}")
        run_tweaks()

def run_tweaks():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    if not is_admin():
        log("Must be run as an administrator.")
        sys.exit(1)

    try:
        config_url = "https://raw.githubusercontent.com/ravendevteam/talon/refs/heads/main/barebones.json"
        log(f"Downloading config from: {config_url}")
        temp_dir = tempfile.gettempdir()
        json_path = os.path.join(temp_dir, "custom_config.json")
        
        if download_file(config_url, json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            log_file = os.path.join(temp_dir, "cttwinutil.log")
            command = [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                f"$ErrorActionPreference = 'SilentlyContinue'; " +
                f"iex \"& {{ $(irm christitus.com/win) }} -Config '{json_path}' -Run\" *>&1 | " +
                "Tee-Object -FilePath '" + log_file + "'"
            ]
            
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace',
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            while True:
                output = process.stdout.readline()
                if output:
                    output = output.strip()
                    log(f"CTT Output: {output}")
                    if "Tweaks are Finished" in output:
                        log("Detected completion message. Terminating...")

                        subprocess.run(
                            ["powershell", "-Command", "Stop-Process -Name powershell -Force"],
                            capture_output=True,
                            creationflags=subprocess.CREATE_NO_WINDOW
                        )

                        run_applybackground()
                        os._exit(0)
                
                if process.poll() is not None:
                    run_applybackground()
                    os._exit(1)

        else:
            run_applybackground()

    except Exception as e:
        log(f"Error: {str(e)}")
        run_applybackground()
        os._exit(1)

def run_applybackground():
    log("Starting ApplyBackground tweaks...")
    try:
        temp_dir = tempfile.gettempdir()
        exe_name = "applybackground.exe"
        exe_path = os.path.join(temp_dir, exe_name)
        url = "https://github.com/ravendevteam/talon-applybackground/releases/download/v1.0.0/applybackground.exe"
        
        if download_file(url, exe_path):
            log(f"Running ApplyBackground from: {exe_path}")
            process = subprocess.run(
                [exe_path],
                capture_output=True,
                text=True
            )

            if process.returncode == 0:
                log("ApplyBackground applied successfully")
            else:
                log(f"Error applying ApplyBackground: {process.stderr}")

            log("ApplyBackground complete")
            run_winconfig()
        else:
            run_winconfig()

    except Exception as e:
        log(f"Error in ApplyBackground: {str(e)}")
        run_winconfig()

def run_winconfig():
    log("Starting Windows configuration process...")
    try:
        script_url = "https://win11debloat.raphi.re/"
        temp_dir = tempfile.gettempdir()
        script_path = os.path.join(temp_dir, "Win11Debloat.ps1")
        
        if download_file(script_url, script_path):
            log("Windows configuration script successfully saved to disk")
            powershell_command = (
                f"Set-ExecutionPolicy Bypass -Scope Process -Force; "
                f"& '{script_path}' -Silent -RemoveApps -RemoveGamingApps -DisableTelemetry "
                f"-DisableBing -DisableSuggestions -DisableLockscreenTips -RevertContextMenu "
                f"-TaskbarAlignLeft -HideSearchTb -DisableWidgets -DisableCopilot -ExplorerToThisPC"
            )
            log(f"Executing PowerShell command with parameters:")
            log(f"Command: {powershell_command}")
            
            process = subprocess.run(
                ["powershell", "-Command", powershell_command],
                capture_output=True,
                text=True
            )
            
            if process.returncode == 0:
                log("Windows configuration completed successfully")
                log(f"Process stdout: {process.stdout}")
                log("Preparing to transition to UpdatePolicyChanger...")
                run_updatepolicychanger()
            else:
                log(f"Windows configuration failed with return code: {process.returncode}")
                log(f"Process stderr: {process.stderr}")
                log(f"Process stdout: {process.stdout}")
                run_updatepolicychanger()
        else:
            run_updatepolicychanger()
            
    except requests.exceptions.RequestException as e:
        log(f"Network error during Windows configuration script download: {str(e)}")
        run_updatepolicychanger()
    except IOError as e:
        log(f"File I/O error while saving Windows configuration script: {str(e)}")
        run_updatepolicychanger()
    except Exception as e:
        log(f"Unexpected error during Windows configuration: {str(e)}")
        run_updatepolicychanger()

def run_updatepolicychanger():
    log("Starting UpdatePolicyChanger script execution...")
    log("Checking system state before UpdatePolicyChanger execution...")
    try:
        script_url = "https://raw.githubusercontent.com/ravendevteam/talon-updatepolicy/refs/heads/main/UpdatePolicyChanger.ps1"
        temp_dir = tempfile.gettempdir()
        script_path = os.path.join(temp_dir, "UpdatePolicyChanger.ps1")
        
        if download_file(script_url, script_path):
            log("UpdatePolicyChanger script successfully saved to disk")
            powershell_command = (
                f"Set-ExecutionPolicy Bypass -Scope Process -Force; "
                f"& '{script_path}'; exit" 
            )
            log(f"PowerShell command prepared: {powershell_command}")
            
            process = subprocess.run(
                ["powershell", "-Command", powershell_command],
                capture_output=True,
                text=True,
            )
            
            log(f"PowerShell process completed with return code: {process.returncode}")
            if process.returncode == 0:
                log("UpdatePolicyChanger execution completed successfully")
                finalize_installation()
            else:
                log(f"UpdatePolicyChanger execution failed with return code: {process.returncode}")
                finalize_installation()
                
        else:
            finalize_installation()

    except Exception as e:
        log(f"Critical error in UpdatePolicyChanger: {e}")
        finalize_installation()

def finalize_installation():
    log("Installation complete. Restarting system...")
    try:
        subprocess.run(["shutdown", "/r", "/t", "0"], check=True)
    except subprocess.CalledProcessError as e:
        log(f"Error during restart: {e}")
        try:
            os.system("shutdown /r /t 0")
        except Exception as e:
            log(f"Failed to restart system: {e}")

if __name__ == "__main__":
    apply_registry_changes()

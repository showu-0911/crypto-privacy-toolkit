from fastapi import FastAPI, Request, Form, status
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from jinja2 import Environment, FileSystemLoader, select_autoescape
import os
import pyotp

dash_pwd = os.getenv("DASHBOARD_PASSWORD", "")
otp_secret = os.getenv("OTP_SECRET", "")

templates = Environment(
    loader=FileSystemLoader("app/templates"),
    autoescape=select_autoescape(["html", "xml"])
)

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=os.urandom(24))
app.mount("/static", StaticFiles(directory="app/static"), name="static")

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

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    if not request.session.get('authenticated'):
        return RedirectResponse(url="/login")
    tpl = templates.get_template("dashboard.html")
    return HTMLResponse(tpl.render())

@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login")


"""
Preview the Portal API (authenticated)
"""

import base64
import functools
import hashlib
import types
import typing
import flask
import webbrowser
import requests
import secrets

FOLDER_NAME = "SBHS_Portal_Tools"
PORT: int = 5050
MAIN: str = f"http://localhost:{PORT}/"
CLIENT_ID: str = "SBHS_Portal_Tools"
INFO_FORMAT_STRING: str = """<!DOCTYPE html><html><head><title>Portal API Previewer</title><style>

/* https://css-tricks.com/snippets/css/make-pre-text-wrap/ */

pre {
 white-space: pre-wrap;       /* css-3 */
 white-space: -moz-pre-wrap;  /* Mozilla, since 1999 */
 white-space: -pre-wrap;      /* Opera 4-6 */
 white-space: -o-pre-wrap;    /* Opera 7 */
 word-wrap: break-word;       /* Internet Explorer 5.5+ */
}

</style></head><body>

<h1>Portal API Previewer</h1>
<pre>{{ string|e }}{{ raw1|safe }}{{ mid|e }}{{ raw2|safe }}

</body></html>"""

access_token: str = ""
refresh_token: str = ""
code_verifier: str = ""
code_challenge: str = ""
state: str = ""

app: flask.Flask = flask.Flask(FOLDER_NAME)

def auth() -> str:
    global state, code_verifier, code_challenge
    state = secrets.token_urlsafe()
    code_verifier = secrets.token_urlsafe()
    hashed: bytes = hashlib.sha256(
        code_verifier.encode("utf-8")
    ).digest()
    encoded: bytes = base64.urlsafe_b64encode(hashed)
    code_challenge = encoded.decode("utf-8").rstrip("=")
    return f"https://student.sbhs.net.au/api/authorize?response_type=code&client_id={CLIENT_ID}&redirect_uri=http://localhost:{PORT}/&scope=all-ro&state={state}&code_challenge={code_challenge}&code_challenge_method=S256"

def post_token(data_: dict) -> tuple[bool, dict | tuple[str, Exception, requests.Response | bytes] | None]:
    try:
        resp: requests.Response = requests.post(
            "https://student.sbhs.net.au/api/token",
        data = data_, headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        })
        resp.raise_for_status()
    except Exception as e:
        return False, ("cannot POST endpoint", e, resp)
    try:
        resp_json: dict = resp.json()
    except Exception as e:
        return False, ("invalid JSON", e, resp.content)
    if "access_token" not in resp_json:
        return False, resp_json
    if "refresh_token" not in resp_json:
        return False, resp_json
    global access_token, refresh_token
    access_token = str(resp_json["access_token"])
    refresh_token = str(resp_json["refresh_token"])
    return True, None

def template_route(route) -> types.FunctionType:
    def wrapper(func) -> types.FunctionType | None:
        @functools.wraps(func)
        def inner(*args, **kwargs) -> flask.Response:
            res: typing.Any = func(*args, **kwargs)
            args: tuple = ()
            if isinstance(res, flask.Response):
                return res
            elif isinstance(res, tuple):
                res, *args = res
            else:
                args = None
            res = flask.render_template_string(INFO_FORMAT_STRING, string = res)
            if args:
                return flask.Response(
                    res, *args
                )
            return flask.Response(res)
        if route is None:
            return inner
        app.add_url_rule(route, None, inner)
    return wrapper

def convert(s: str):
    return template_route(None)(lambda:s)()

@template_route("/")
def root() -> str | flask.Response:
    global access_token, refresh_token
    if (( flask.request.args.get("state")) and
          ( flask.request.args.get("state") != state)):
        # Wrong state
        return flask.redirect(MAIN)
    elif access_token:
        return "Authenticated"
    elif flask.request.args.get("error"):
        pass
    elif flask.request.args.get("reset"):
        # Reset
        access_token = ""
    elif flask.request.args.get("code"):
        # Authenticated
        success: bool
        resp_opt: dict | str | None
        
        success, resp_opt = post_token({
            "grant_type": "authorization_code",
            "code": flask.request.args.get("code"),
            "redirect_uri": MAIN,
            "client_id": CLIENT_ID,
            "code_verifier": code_verifier
        })
        if success:
            return flask.redirect(MAIN)
        print("Fail -", resp_opt)
    return flask.redirect(auth())

@template_route("/refresh")
def refresh() -> str | flask.Response:
    if not refresh_token:
        return "Not authenticated"
    success: bool
    resp_opt: dict | str | None
    success, resp_opt = post_token({
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": CLIENT_ID,
        "code_verifier": code_verifier
    })
    if success:
        return "Success"
    print("Fail -", resp_opt)
    return "Unable to refresh access token"

@template_route("/tokens")
def tokens() -> str:
    return "Not implemented"

@app.errorhandler(404)
def handle_404(e) -> flask.Response:
    if not access_token:
        return flask.redirect(auth())
    path: str = flask.request.full_path.lstrip("/")
    resp: requests.Response = requests.get(
        f"https://student.sbhs.net.au/api/{path}",
    headers = {
        "Authorization": f"Bearer {access_token}",
    })
    if not resp.content:
        return flask.Response(
            convert("Empty response"), 200,
            {"Content-Type": "text/plain; charset=UTF-8"}
        )
    if "Content-Type" in resp.headers:
        return flask.Response(resp.text, resp.status_code, {
            "Content-Type": resp.headers["Content-Type"]
        })
    if "content-type" in resp.headers:
        return flask.Response(resp.text, resp.status_code, {
            "Content-Type": resp.headers["content-type"]
        })
    return flask.Response(resp.text, resp.status_code)

@app.route("/favicon.ico")
def favicon() -> flask.Response:
    return flask.redirect(f"http://localhost:{PORT}/static/favicon.ico")

webbrowser.open(auth())
if __name__ == "__main__":
    app.run(host = "127.0.0.1", port = PORT)
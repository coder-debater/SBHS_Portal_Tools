"""
Preview the Portal API (authenticated)
"""

import base64
import hashlib
import flask
import webbrowser
import requests
import secrets

app: flask.Flask = flask.Flask('SBHS_Portal_Tools')
MAIN: str = f"http://localhost:5050/"
CLIENT_ID: str = "SBHS_Portal_Tools"
access_token: str = ""
refresh_token: str = ""
code_verifier: str = ""
code_challenge: str = ""
state: str = ""

def auth() -> str:
    global state, code_verifier, code_challenge
    state = secrets.token_urlsafe()
    code_verifier = secrets.token_urlsafe()
    hashed: bytes = hashlib.sha256(
        code_verifier.encode('utf-8')
    ).digest()
    encoded: bytes = base64.urlsafe_b64encode(hashed)
    code_challenge = encoded.decode('utf-8').rstrip('=')
    return f"https://student.sbhs.net.au/api/authorize?response_type=code&client_id={CLIENT_ID}&redirect_uri=http://localhost:5050/&scope=all-ro&state={state}&code_challenge={code_challenge}&code_challenge_method=S256"

def post_token(data_: dict) -> tuple[bool, dict | tuple[str, Exception, requests.Response | bytes] | None]:
    try:
        resp: requests.Response = requests.post(
            "https://student.sbhs.net.au/api/token",
        data = data_, headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        })
        resp.raise_for_status()
    except Exception, e:
        return False, ('cannot POST endpoint', e, resp)
    try:
        resp_json: dict = resp.json()
    except Exception as e:
        return False, ('invalid JSON', e, resp.content)
    if 'access_token' not in resp_json:
        return False, resp_json
    if 'refresh_token' not in resp_json:
        return False, resp_json
    global access_token, refresh_token
    access_token = str(resp_json['access_token'])
    refresh_token = str(resp_json['refresh_token'])
    return True, None

@app.route('/')
def root() -> str | flask.Response:
    global access_token, refresh_token
    if (( flask.request.args.get('state')) and
          ( flask.request.args.get('state') != state)):
        # Wrong state
        return flask.redirect(MAIN)
    elif access_token:
        return 'Authenticated'
    elif flask.request.args.get('error'):
        pass
    elif flask.request.args.get('reset'):
        # Reset
        access_token = ''
    elif flask.request.args.get('code'):
        # Authenticated
        success: bool
        resp_opt: dict | str | None
        
        success, resp_opt = post_token({
            'grant_type': "authorization_code",
            'code': flask.request.args.get('code'),
            'redirect_uri': MAIN,
            'client_id': CLIENT_ID,
            'code_challenge': code_challenge,
            'code_verifier': code_verifier
        }, headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        })
        if success:
            return flask.redirect(MAIN)
        print("Fail -", resp_opt)
    return flask.redirect(auth())

@app.route('/refresh')
def refresh() -> str | flask.Response:
    if not refresh_token:
        return "Not authenticated"
    success: bool
    resp_opt: dict | str | None
    success, resp_opt = post_token({
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
        'client_id': CLIENT_ID
    })
    if success:
        return flask.redirect(MAIN)
    print("Fail -", resp_opt)
    return "Unable to refresh access token"

@app.errorhandler(404)
def handle_404(e) -> tuple[bytes, int] | flask.Response:
    if not access_token:
        return flask.redirect(auth())
    path: str = flask.request.full_path.lstrip('/')
    resp: requests.Response = requests.get(
        f"https://student.sbhs.net.au/api/{path}",
    headers = {
        'Authorization': f"Bearer {access_token}",
    })
    if not resp.content:
        return b"No content :(", 200
    return resp.content, resp.status_code

@app.route('/favicon.ico')
def favicon() -> flask.Response:
    return flask.redirect('http://localhost:5050/static/favicon.ico')

webbrowser.open(auth())
if __name__ == "__main__":
    app.run(host = '127.0.0.1', port = 5050)
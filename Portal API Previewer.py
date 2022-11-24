import base64
import hashlib
import flask
import webbrowser
import requests
import secrets

app: flask.Flask = flask.Flask('Challenge Test')
MAIN: str = f"http://localhost:5050/"

access_token: str = ""
code_verifier: str = ""
code_challenge: str = ""
state: str = ""
CLIENT_ID: str = "SBHS_Portal_Tools"

def pkce_reset():
    global state, code_verifier, code_challenge
    state = secrets.token_urlsafe()
    code_verifier = secrets.token_urlsafe()
    hashed: bytes = hashlib.sha256(
        code_verifier.encode('utf-8')
    ).digest()
    encoded: bytes = base64.urlsafe_b64encode(hashed)
    code_challenge = encoded.decode('utf-8').rstrip('=')
pkce_reset()

def auth():
    return f"https://student.sbhs.net.au/api/authorize?response_type=code&client_id={CLIENT_ID}&redirect_uri=http://localhost:5050/&scope=all-ro&state={state}&code_challenge={code_challenge}&code_challenge_method=S256"

def auth_redir():
    return flask.redirect(auth())

@app.route('/', methods = ['GET', 'POST'])
def root():
    global access_token
    if flask.request.args.get('code'):
        # Authenticated
        resp: requests.Response = requests.post(
            "https://student.sbhs.net.au/api/token",
        data = {
            'grant_type': "authorization_code",
            'code': flask.request.args.get('code'),
            'redirect_uri': MAIN,
            'client_id': CLIENT_ID,
            'state': state,
            'code_challenge': code_challenge,
            'code_verifier': code_verifier
        }, headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        })
        access_token = str(resp.json()['access_token'])
        return flask.redirect(MAIN)
    elif flask.request.args.get('error'):
        # Denied, re-authenticate
        return auth_redir()
    elif flask.request.args.get('reset'):
        # Reset
        access_token = ''
        pkce_reset()
        return auth_redir()
    elif access_token:
        return 'Authenticated'
    return auth_redir()

@app.errorhandler(404)
def handle_404(e):
    if not access_token:
        return flask.redirect(auth())
    path: str = flask.request.full_path.lstrip('/')
    resp: requests.Request = requests.get(
        f"https://student.sbhs.net.au/api/{path}",
    headers = {
        'Authorization': f"Bearer {access_token}",
    })
    if not resp.content:
        return "No content :(", 200
    return (resp.content, resp.status_code, resp.headers.items())

webbrowser.open(auth())
if __name__ == "__main__":
    app.run(host = '127.0.0.1', port = 5050)
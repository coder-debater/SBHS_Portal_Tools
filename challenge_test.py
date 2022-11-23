import webbrowser
import flask
import secrets
import requests

app = flask.Flask('Challenge Test')
MAIN = f"http://localhost:5050/"

code_verifier: str = secrets.token_urlsafe()
access_token: list[str | None] = [None]

def auth():
    return f"https://student.sbhs.net.au/api/authorize?response_type=code&client_id=Portal_to_ICS&redirect_uri=http://localhost:5050/&code_challenge=TODO&scope=all-ro"

def auth_redir():
    return flask.redirect(auth())

@app.route('/', methods = ['GET', 'POST'])
def root():
    if flask.request.args.get('code'):
        # Authenticated
        access_token[0] = str(requests.post(
            "https://student.sbhs.net.au/api/token",
        data = {
            'grant_type': "authorization_code",
            'code': flask.request.args.get('code'),
            'redirect_uri': MAIN,
            'client_id': "Portal_to_ICS",
            'code_challenge': "TODO",
            'code_verifier': code_verifier
        }, headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        }).json()['access_token'])
        return flask.redirect(MAIN)
    elif flask.request.args.get('error'):
        # Denied, re-authenticate
        return auth()
    elif flask.request.args.get('reset'):
        # Reset
        access_token[0] = None
        code_verifier = secrets.token_urlsafe()
        return auth()
    elif access_token[0]:
        return 'Authenticated'
    return flask.redirect(auth)

@app.errorhandler(404)
def handle_404(e):
    if access_token[0]:
        path = flask.request.full_path.lstrip('/')
        return requests.get(
            f"https://student.sbhs.net.au/api/{path}",
        headers = {
            'Authorization': f"Bearer {access_token[0]}",
        }).content
    return flask.redirect(auth())

webbrowser.open(auth())
app.run(host = '127.0.0.1', port = 5050)
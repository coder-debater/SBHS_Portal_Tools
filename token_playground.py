import webbrowser
import flask
import secrets
import requests

# Change this to something else if it isn't working
PORT = 5555



app = flask.Flask('Token Playground')
MAIN = f"http://localhost:{PORT}/"

client_id = [None]
client_secret = [None]
auth_code = [None]
state = [None]
access_token = [None]

def auth():
    state[0] = secrets.token_urlsafe()
    return flask.redirect(
        f"https://student.sbhs.net.au/api/authorize?response_type=code&client_id={client_id[0]}&redirect_uri={MAIN}&state={state[0]}&scope=all-ro"
    )

def get_access_token():
    access_token[0] = requests.post(
        "https://student.sbhs.net.au/api/token",
    data = {
        'grant_type': "authorization_code",
        'code': auth_code[0],
        'redirect_uri': MAIN,
        'client_id': client_id[0],
        'client_secret': client_secret[0],
    }, headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    }).json()['access_token']

def index():
    return f"""<!DOCTYPE html><html lang="en"><head>
<meta charset="UTF-8">
<meta http-equiv="X-UA-Compatible" content="IE=edge">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Token Playground</title></head>

<body><form action="/" method="POST"><fieldset>



<legend>Create an app, then fill in this form</legend>
Choose any name, and any app ID. <br>

Set your Redirect URI and website address to
<input value="{MAIN}" readonly>
<br>

GitHub repo:
<input value="https://github.com/wensenfriendandextra/Portal-to-ICS" readonly>

<br><br><br><label for="client_id">App ID:</label>
<input type="text" id="client_id" name="client_id" placeholder="My Amazing App" required><br><br>
<label for="client_secret">App Secret:</label>
<input type="password" id="client_secret" name="client_secret" placeholder="(shh!)" required>

<br><br><br><input type="submit" value="Generate my ICS!">



</fieldset></form></body></html>"""
@app.route('/', methods = ['GET', 'POST'])
def root():
    if flask.request.method == "POST":
        # Form submitted
        client_id[0] = flask.request.form.get('client_id')
        client_secret[0] = flask.request.form.get('client_secret')
        return auth()
    elif (( flask.request.args.get('state')) and
          ( flask.request.args.get('state') != state[0])):
        # Wrong state
        return flask.redirect(MAIN)
    elif flask.request.args.get('code'):
        # Authenticated
        auth_code[0] = flask.request.args.get('code')
        get_access_token()
        return flask.redirect(MAIN)
    elif (
        flask.request.args.get('state') or
        flask.request.args.get('error')):
        # Denied, re-authenticate
        return auth()
    elif flask.request.args.get('reset'):
        # RESET EVERYTHING!!!!!!!
        client_id[0] = client_secret[0] = auth_code[0] = state[0] = access_token[0] = None
        return flask.redirect(MAIN)
    elif access_token[0]:
        return 'Authenticated'
    # Normal access
    return index()

@app.errorhandler(404)
def handle_404(e):
    if access_token[0]:
        path = flask.request.full_path.lstrip('/')
        return requests.get(
            f"https://student.sbhs.net.au/api/{path}",
        headers = {
            'Authorization': f"Bearer {access_token[0]}",
        }).content
    else:
        return flask.redirect(MAIN)

webbrowser.open(MAIN)
app.run(host = '127.0.0.1', port = PORT)
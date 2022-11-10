import base64
from datetime import datetime as DT, timedelta as TD
import hashlib
import webbrowser
import flask
import secrets
import requests

class Calendar(object):
    def __init__(self, version = None, attrs = None, subcomponents = None):
        self._attrs = attrs or {}
        if version is not None:
            self.version = version
        self._sub = subcomponents or []
    def _attrs_repr(self):
        return [':'.join([k, v]) for k, v in self._attrs.items()]
    def __repr__(self):
        return '\n'.join([
            f"BEGIN:VCALENDAR",
            *self._attrs_repr(),
            *map(self._sub_repr, self._sub),
            f"END:VCALENDAR"
        ])
    @classmethod
    def _sub_repr(cls, self):
        return '\n'.join(self._attrs_repr()).join([
            f"BEGIN:VEVENT\n", f"\nEND:VEVENT"
        ])
    def __setitem__(self, k, v):
        self._attrs[str(k).upper()] = str(v)
    def __setattr__(self, name, val):
        if (name in dir(self)) or name.startswith('_'):
            return object.__setattr__(self, name, val)
        self[name] = val
    def format_dt(self, dt: DT):
        return dt.strftime("%Y-%m-%dT%H:%M:%S")
    def add_class(self,
        class_name: str, teacher: str, room: int,
        day: DT, start_time: TD, end_time: TD
    ):
        start = self.format_dt(day + start_time)
        formatted = day.strftime('%A')[:2].upper()
        self._sub.append(type(self)(attrs = {
            'SUMMARY': class_name,
            'DESCRIPTION': f"{class_name} class - {teacher}",
            "LOCATION": str(room),
            "DTSTART": start,
            "DTEND": self.format_dt(day + end_time),
            "DTSTAMP": start,
            "RRULE": f"FREQ=WEEKLY;INTERVAL=3;BYDAY={formatted}"
        }))
    # def add_classes(self, classes):
    #     for class_info in classes: self.add_class(*class_info)
    # def write_to(self, filename, mode = 'w'):
    #     r = repr(self)
    #     with open(filename, mode) as file:
    #         file.write(r)

app = flask.Flask('Portal to ICS')
PORT = 5050
MAIN = f"http://localhost:{PORT}/"

client_id = [None]
# client_secret = [None]
auth_code = [None]
code_verifier = [None]
code_challenge = [None]
state = [None]

def gen_code_challenge():
    code_verifier[0] = secrets.token_urlsafe(100)[:(secrets.randbelow(64)+64)]
    code_challenge[0] = base64.b64encode(
        hashlib.sha256(code_verifier[0]).digest()
    ).replace(
        b'+', b'-'
    ).replace(
        b'/', b'_'
    ).strip(b'=')

def auth():
    gen_code_challenge()
    return flask.redirect(
        f"https://student.sbhs.net.au/api/authorize?response_type=code&client_id={client_id[0]}&redirect_uri={MAIN}&state={state[0]}&code_challenge={code_challenge[0]}&code_challenge_method=S256&scope=all-ro"
    )

def callback():
    access_token = requests.post(
        "https://student.sbhs.net.au/api/token",
    data = {
        'grant_type': "authorization_code",
        'code': auth_code[0],
        'redirect_uri': MAIN,
        'code_verifier': code_verifier[0],
        'code_challenge': code_challenge[0],
        # 'client_id': client_id[0],
        # 'client_secret': client_secret[0],
    }, headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    }).json()
    print('Access token: ', access_token)
    access_token = access_token['access_token']
    timetable = requests.get(
        "https://student.sbhs.net.au/api/timetable/timetable.json",
    headers = {
        'Authorisation': "".join(["Bearer ", access_token]),
    }).content
    print('Timetable: ', timetable)
    return 'ics file here'

def index():
    return f"""<!DOCTYPE html><html lang="en"><head>
<meta charset="UTF-8">
<meta http-equiv="X-UA-Compatible" content="IE=edge">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Portal to ICS</title></head>

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
<!--
<label for="client_secret">App Secret:</label>
<input type="password" id="client_secret" name="client_secret" placeholder="(shh!)" required>
-->

<br><br><br><input type="submit" value="Generate my ICS!">



</fieldset></form></body></html>"""

@app.route('/', methods = ['GET', 'POST'])
def root():
    if flask.request.method == "POST":
        client_id[0] = flask.request.form.get('client_id')
        # client_secret[0] = flask.request.form.get('client_secret')
        state[0] = secrets.token_urlsafe()
        return auth()
    elif flask.request.args.get('code') and flask.request.args.get('state'):
        if state[0] != flask.request.args.get('state'):
            raise RuntimeError("state was changed")
        auth_code[0] = flask.request.args.get('code')
        return flask.redirect(MAIN)
    elif flask.request.args.get('state'):
        if state[0] != flask.request.args.get('state'):
            return flask.redirect(MAIN)
        return auth()
    elif auth_code[0]:
        return callback()
    return index()

webbrowser.open(MAIN)
app.run(host = '127.0.0.1', port = PORT)

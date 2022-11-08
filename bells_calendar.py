from datetime import datetime as DT, timedelta as TD
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
    def add_classes(self, classes):
        for class_info in classes: self.add_class(*class_info)
    def write_to(self, filename, mode = 'w'):
        r = repr(self)
        with open(filename, mode) as file:
            file.write(r)

app = flask.Flask('Portal to ICS')

secret = [secrets.token_hex()]
nocode = [True]
code = [None]

CLIENT_ID, CLIENT_SECRET = input("Client ID: "), input("Client secret:")

def _reset():
    secret[0] = secrets.token_hex()
    nocode[0] = True

@app.route('/')
def index():
    if nocode[0]:
        return flask.redirect(
f"https://student.sbhs.net.au/api/authorize?response_type=code&client_id={CLIENT_ID}&scope=all-ro&state={secret[0]}")
    resp = requests.post(
        "https://" "student.sbhs"
        ".net.au/api/token", data = {
            'grant_type': "authorization_code",
            'code': code[0],
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'redirect_uri': 'http://localhost:5500/callback.html',
            'code_verifier': secret[0],
        }, headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        }
    )
    access_token = resp.json()['access_token']
    print(access_token)
    return flask.render_template('index.html')

@app.route('/callback.html')
def callback():
    if secret[0] == flask.request.args.get('state'):
        nocode[0] = False
        code[0] = flask.request.args.get('code')
    else:
        _reset()
    return flask.redirect('/')

@app.route('/reset')
def reset():
    _reset()
    return flask.redirect('/')

webbrowser.open('http://localhost:5500/')
app.run(host = '127.0.0.1', port = 5500)

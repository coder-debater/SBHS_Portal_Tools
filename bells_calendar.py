from datetime import datetime as DT, timedelta as TD
import json
import typing
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
        return [':'.join([k, v]) for k, v in self._attrs.items() if v is not None]
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
        class_name: str, teacher: str, room: str,
        day: DT, start_time: TD, end_time: TD
    ):
        start = self.format_dt(day + start_time)
        formatted = day.strftime('%A')[:2].upper()
        self._sub.append(type(self)(attrs = {
            'SUMMARY': class_name,
            'DESCRIPTION': f"{class_name} class - {teacher}",
            "LOCATION": room,
            "DTSTART": start,
            "DTEND": self.format_dt(day + end_time),
            "DTSTAMP": start,
            "RRULE": f"FREQ=WEEKLY;INTERVAL=3;BYDAY={formatted}"
        }))
    # def add_classes(self, classes):
    #     for class_info in classes: self.add_class(*class_info)
    def write_to(self, filename, mode = 'w'):
        r = repr(self)
        with open(filename, mode) as file:
            file.write(r)

app = flask.Flask('Portal to ICS')
PORT = 5050
MAIN = f"http://localhost:{PORT}/"

OptionalList = list[typing.Any | None]
client_id: OptionalList = [None]
client_secret: OptionalList = [None]
auth_code: OptionalList = [None]
state: OptionalList = [None]
access_token: OptionalList = [None]
generated: list[bool] = [False]

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
<label for="client_secret">App Secret:</label>
<input type="password" id="client_secret" name="client_secret" placeholder="(shh!)" required>

<br><br><br><input type="submit" value="Generate my ICS!">



</fieldset></form></body></html>"""

def parseTime(time):
    # convert HH:MM, H:MM, HH:MM:SS, H:MM:SS
    # to timedelta from midnight
    # includes am, pm
    time = time.strip().lower()
    if time.endswith('am'):
        return parseTime(time[:-2])
    elif time.endswith('pm'):
        return parseTime(time[:-2]) + TD(hours = 12)
    time = time.split(':')
    td = TD(hours = int(time[0]), minutes = int(time[1]))
    if len(time) == 3:
        td += TD(seconds = int(time[-1]))
    return td

@app.route('/', methods = ['GET', 'POST'])
@app.route('/app', methods = ['GET', 'POST'])
@app.route('/app/', methods = ['GET', 'POST'])
@app.route('/app.html', methods = ['GET', 'POST'])
@app.route('/callback', methods = ['GET', 'POST'])
@app.route('/callback/', methods = ['GET', 'POST'])
@app.route('/callback.html', methods = ['GET', 'POST'])
@app.route('/wensen', methods = ['GET', 'POST'])
@app.route('/wensen/', methods = ['GET', 'POST'])
@app.route('/wensen.html', methods = ['GET', 'POST'])
@app.route('/derivative/of/x/squared/is/two/x', methods = ['GET', 'POST'])
@app.route('/derivative/of/x/squared/is/two/x/', methods = ['GET', 'POST'])
@app.route('/derivative/of/x/squared/is/two/x.html', methods = ['GET', 'POST'])
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
        # Yay timetable :D
        if generated[0]:
            return "Already generated"
        generated[0] = True
        calendar = Calendar('2.0')
        now = DT.now()
        curr_day = DT(year = int(now.year), month = int(now.month), day = int(now.day))
        day = TD(days = 1)
        curr_day -= day
        for _ in range(21):
            curr_day += day
            try:
                content = requests.get(''.join([
                    "https://student.sbhs.net.au",
                    "/api/timetable/daytimetable.json",
                    "?date=",
                    str(curr_day.year),
                    "-",
                    str(curr_day.month).zfill(2),
                    "-",
                    str(curr_day.day).zfill(2)
                ]), headers = {
                    'Authorization': f"Bearer {access_token[0]}",
                }).content
                print(len(content))
                timetable = json.loads(content)
                bells = timetable.get('bells', timetable.get('bell', None))
                if not bells:
                    continue
                timetable_classes = timetable['timetable']
                daytimetable = timetable_classes['timetable']
                periods = daytimetable['periods']
                classes = timetable_classes.get('subjects', timetable_classes.get('classes', None))
                if isinstance(bells, dict):
                    bells = bells.values()
                bells = {v['period']: v for v in bells}
                if not isinstance(periods, dict):
                    break
                for name, info in periods.items():
                    bell = bells.get(str(name), None)
                    if bell is None:
                        bell = bells[int(name)]
                    start = parseTime(
                        bell.get('startTime',
                        bell.get('start',
                        bell.get('time', None)))
                    )
                    end = parseTime(
                        bell.get('endTime',
                        bell.get('end', None))
                    )
                    if ((end - start) >= TD(minutes = 10)):
                        short_title = info['title']
                        possible_class_key = ''.join([info['year'], short_title])
                        possible_class = classes.get(short_title, None)
                        this_class = classes.get(possible_class_key, possible_class)
                        class_name = this_class.get('title', this_class.get('longTitle', None))
                        teacher = this_class.get('fullTeacher', this_class.get('teacher', None))
                        calendar.add_class(
                            class_name,
                            teacher,
                            info['room'],
                            curr_day,
                            start,
                            end
                        )
                print("All classes added", curr_day)
            except Exception:
                pass
        calendar.write_to('test.ics')
        return f'ICS here, Bearer {access_token[0]}'
    # Normal access
    return index()

@app.errorhandler(404)
def handle_404(e):
    return flask.redirect(MAIN)

@app.route('/favicon.ico')
def favicon():
    return flask.redirect(f"{MAIN}static/favicon.ico")

webbrowser.open(MAIN)
app.run(host = '127.0.0.1', port = PORT)
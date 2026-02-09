from http.server import BaseHTTPRequestHandler
import json
import os
import time
from urllib.request import Request, urlopen
from urllib.error import URLError

# Vercel KV (Upstash Redis) REST API config
KV_REST_API_URL = os.environ.get('KV_REST_API_URL', '')
KV_REST_API_TOKEN = os.environ.get('KV_REST_API_TOKEN', '')

# Fallback file storage when KV is not configured
EVENTS_FILE = '/tmp/analytics_events.json'

def kv_available():
    return bool(KV_REST_API_URL and KV_REST_API_TOKEN)

def kv_request(commands):
    """Send a pipeline of commands to Vercel KV REST API.
    commands: list of lists, e.g. [["RPUSH", "events", "..."], ["INCR", "count:scans"]]
    Returns list of results."""
    url = KV_REST_API_URL + '/pipeline'
    body = json.dumps(commands).encode()
    req = Request(url, data=body, method='POST')
    req.add_header('Authorization', 'Bearer ' + KV_REST_API_TOKEN)
    req.add_header('Content-Type', 'application/json')
    resp = urlopen(req, timeout=5)
    return json.loads(resp.read())

def kv_single(command):
    """Send a single command to Vercel KV REST API.
    command: list, e.g. ["LRANGE", "events", "0", "-1"]
    Returns the result value."""
    url = KV_REST_API_URL
    body = json.dumps(command).encode()
    req = Request(url, data=body, method='POST')
    req.add_header('Authorization', 'Bearer ' + KV_REST_API_TOKEN)
    req.add_header('Content-Type', 'application/json')
    resp = urlopen(req, timeout=10)
    data = json.loads(resp.read())
    return data.get('result')

# --- Counter key mapping ---
COUNTER_MAP = {
    'scan': 'count:scans',
    'lead_submit': 'count:leads',
    'recipe_tap': 'count:recipes',
    'whatsapp_send': 'count:whatsapp',
    'chat_message': 'count:chats',
    'promo_shown': 'count:promo_shown',
    'promo_click': 'count:promo_click',
    'promo_dismiss': 'count:promo_dismiss',
    'guided_answer': 'count:guided',
    'email_share': 'count:email_share',
    'discount_copy': 'count:discount_copy',
}

def kv_write_event(event):
    """Write event to KV: RPUSH to events list + INCR relevant counter."""
    event_json = json.dumps(event)
    commands = [
        ['RPUSH', 'events', event_json],
    ]
    # Increment the counter for this event type
    counter_key = COUNTER_MAP.get(event.get('event_type'))
    if counter_key:
        commands.append(['INCR', counter_key])
    # Cap list at 10000 events
    commands.append(['LTRIM', 'events', '-10000', '-1'])
    kv_request(commands)

def kv_read_events():
    """Read all events from KV."""
    result = kv_single(['LRANGE', 'events', '0', '-1'])
    if not result:
        return []
    events = []
    for item in result:
        try:
            events.append(json.loads(item))
        except (json.JSONDecodeError, TypeError):
            pass
    return events

def kv_read_counters():
    """Read all counter values in a single pipeline call."""
    commands = [['GET', key] for key in COUNTER_MAP.values()]
    results = kv_request(commands)
    counters = {}
    keys = list(COUNTER_MAP.values())
    for i, r in enumerate(results):
        val = r.get('result') if isinstance(r, dict) else None
        counters[keys[i]] = int(val) if val else 0
    return counters

# --- Fallback file storage ---
def file_read_events():
    try:
        with open(EVENTS_FILE, 'r') as f:
            return json.loads(f.read())
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def file_write_event(event):
    events = file_read_events()
    events.append(event)
    if len(events) > 10000:
        events = events[-10000:]
    with open(EVENTS_FILE, 'w') as f:
        f.write(json.dumps(events))

# --- Handler ---
class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)

            event = {
                'sessionId': data.get('sessionId', ''),
                'store': data.get('store', 'leroy-merlin'),
                'event_type': data.get('event_type', ''),
                'event_data': data.get('event_data', {}),
                'client': data.get('client', 'direct'),
                'timestamp': data.get('timestamp', ''),
                'server_time': time.time()
            }

            if kv_available():
                kv_write_event(event)
            else:
                file_write_event(event)

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'ok': True, 'storage': 'kv' if kv_available() else 'file'}).encode())

        except Exception as e:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())

    def do_GET(self):
        try:
            if kv_available():
                events = kv_read_events()
                counters = kv_read_counters()
            else:
                events = file_read_events()
                counters = None

            response = {
                'events': events,
                'count': len(events),
                'storage': 'kv' if kv_available() else 'file'
            }
            if counters:
                response['counters'] = counters

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())

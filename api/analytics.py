from http.server import BaseHTTPRequestHandler
import json
import os
import time
from urllib.request import Request, urlopen
from urllib.error import URLError

# --- Redis via REDIS_URL (primary) ---
REDIS_URL = os.environ.get('REDIS_URL', '')
_redis_client = None
_redis_error = None

try:
    import redis as _redis_mod
    if REDIS_URL:
        try:
            _redis_client = _redis_mod.from_url(REDIS_URL, decode_responses=True, socket_timeout=5)
            _redis_client.ping()
        except Exception as e:
            _redis_error = str(e)
            _redis_client = None
except ImportError:
    _redis_error = 'redis package not installed'

# --- Vercel KV REST API (secondary) ---
KV_REST_API_URL = os.environ.get('KV_REST_API_URL', '')
KV_REST_API_TOKEN = os.environ.get('KV_REST_API_TOKEN', '')

# Fallback file storage
EVENTS_FILE = '/tmp/analytics_events.json'

def get_storage_type():
    if _redis_client:
        return 'redis'
    if KV_REST_API_URL and KV_REST_API_TOKEN:
        return 'kv'
    return 'file'

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

# --- Redis client operations ---
def redis_write_event(event):
    event_json = json.dumps(event)
    pipe = _redis_client.pipeline()
    pipe.rpush('events', event_json)
    counter_key = COUNTER_MAP.get(event.get('event_type'))
    if counter_key:
        pipe.incr(counter_key)
    pipe.ltrim('events', -10000, -1)
    pipe.execute()

def redis_read_events():
    items = _redis_client.lrange('events', 0, -1)
    events = []
    for item in items:
        try:
            events.append(json.loads(item))
        except (json.JSONDecodeError, TypeError):
            pass
    return events

def redis_read_counters():
    pipe = _redis_client.pipeline()
    for key in COUNTER_MAP.values():
        pipe.get(key)
    results = pipe.execute()
    counters = {}
    for key, val in zip(COUNTER_MAP.values(), results):
        counters[key] = int(val) if val else 0
    return counters

# --- KV REST API operations ---
def kv_request(commands):
    url = KV_REST_API_URL + '/pipeline'
    body = json.dumps(commands).encode()
    req = Request(url, data=body, method='POST')
    req.add_header('Authorization', 'Bearer ' + KV_REST_API_TOKEN)
    req.add_header('Content-Type', 'application/json')
    resp = urlopen(req, timeout=5)
    return json.loads(resp.read())

def kv_single(command):
    url = KV_REST_API_URL
    body = json.dumps(command).encode()
    req = Request(url, data=body, method='POST')
    req.add_header('Authorization', 'Bearer ' + KV_REST_API_TOKEN)
    req.add_header('Content-Type', 'application/json')
    resp = urlopen(req, timeout=10)
    data = json.loads(resp.read())
    return data.get('result')

def kv_write_event(event):
    event_json = json.dumps(event)
    commands = [['RPUSH', 'events', event_json]]
    counter_key = COUNTER_MAP.get(event.get('event_type'))
    if counter_key:
        commands.append(['INCR', counter_key])
    commands.append(['LTRIM', 'events', '-10000', '-1'])
    kv_request(commands)

def kv_read_events():
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

# --- Dispatch helpers ---
def write_event(event):
    st = get_storage_type()
    if st == 'redis':
        redis_write_event(event)
    elif st == 'kv':
        kv_write_event(event)
    else:
        file_write_event(event)

def read_events():
    st = get_storage_type()
    if st == 'redis':
        return redis_read_events()
    elif st == 'kv':
        return kv_read_events()
    else:
        return file_read_events()

def read_counters():
    st = get_storage_type()
    if st == 'redis':
        return redis_read_counters()
    elif st == 'kv':
        return kv_read_counters()
    else:
        return None

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

            write_event(event)

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'ok': True, 'storage': get_storage_type()}).encode())

        except Exception as e:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())

    def do_GET(self):
        try:
            events = read_events()
            counters = read_counters()
            storage = get_storage_type()

            response = {
                'events': events,
                'count': len(events),
                'storage': storage,
            }
            if counters:
                response['counters'] = counters

            # Debug info when not using Redis
            if storage == 'file':
                response['debug'] = {
                    'REDIS_URL_set': bool(REDIS_URL),
                    'redis_error': _redis_error,
                    'KV_REST_API_URL_set': bool(KV_REST_API_URL),
                    'KV_REST_API_TOKEN_set': bool(KV_REST_API_TOKEN),
                }

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

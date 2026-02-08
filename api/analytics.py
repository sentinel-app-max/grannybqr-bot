from http.server import BaseHTTPRequestHandler
import json
import os
import time

EVENTS_FILE = '/tmp/analytics_events.json'

def read_events():
    try:
        with open(EVENTS_FILE, 'r') as f:
            return json.loads(f.read())
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def write_event(event):
    events = read_events()
    events.append(event)
    # Keep last 10000 events to avoid unbounded growth
    if len(events) > 10000:
        events = events[-10000:]
    with open(EVENTS_FILE, 'w') as f:
        f.write(json.dumps(events))

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
            self.wfile.write(json.dumps({'ok': True}).encode())

        except Exception as e:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())

    def do_GET(self):
        try:
            events = read_events()

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'events': events, 'count': len(events)}).encode())

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())

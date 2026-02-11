from http.server import BaseHTTPRequestHandler


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(302)
        self.send_header('Location', 'https://grannybqr.summitwebcraft.co.za/?store=leroy-fourways')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()

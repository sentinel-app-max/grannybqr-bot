from http.server import BaseHTTPRequestHandler
import json
import urllib.request
import os
from datetime import datetime

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        return

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = json.loads(post_data)

        brevo_key = os.environ.get('BREVO_API_KEY')

        if not brevo_key:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'success': False, 'message': 'Email service not configured'}).encode())
            return

        name = data.get('name', 'Not provided')
        email = data.get('email', 'Not provided')
        phone = data.get('phone', 'Not provided')
        consent = data.get('consent', False)
        sku = data.get('sku', 'Not specified')
        store = data.get('store', 'Not specified')

        if not email or email == 'Not provided':
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'success': False, 'message': 'Email is required'}).encode())
            return

        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        email_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #F7E07D 0%, #D4BF4A 100%); padding: 20px; text-align: center;">
                <h1 style="color: #1A1A1A; margin: 0;">New Lead from Granny B's QR Advisor</h1>
                <p style="color: #1A1A1A; margin: 5px 0 0 0; opacity: 0.8;">at Leroy Merlin</p>
            </div>

            <div style="padding: 30px; background: #FFFDF5;">
                <h2 style="color: #1A1A1A; border-bottom: 2px solid #F7E07D; padding-bottom: 10px;">Contact Details</h2>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 10px 0; font-weight: bold; width: 140px;">Name:</td>
                        <td style="padding: 10px 0;">{name}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px 0; font-weight: bold;">Email:</td>
                        <td style="padding: 10px 0;"><a href="mailto:{email}">{email}</a></td>
                    </tr>
                    <tr>
                        <td style="padding: 10px 0; font-weight: bold;">Phone:</td>
                        <td style="padding: 10px 0;"><a href="tel:{phone}">{phone}</a></td>
                    </tr>
                    <tr>
                        <td style="padding: 10px 0; font-weight: bold;">POPIA Consent:</td>
                        <td style="padding: 10px 0;">{'Yes' if consent else 'No'}</td>
                    </tr>
                </table>

                <h2 style="color: #1A1A1A; border-bottom: 2px solid #F7E07D; padding-bottom: 10px; margin-top: 30px;">Product &amp; Store</h2>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 10px 0; font-weight: bold; width: 140px;">SKU:</td>
                        <td style="padding: 10px 0;">{sku}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px 0; font-weight: bold;">Store:</td>
                        <td style="padding: 10px 0;">{store}</td>
                    </tr>
                </table>

                <p style="color: #8C8577; font-size: 12px; margin-top: 30px; text-align: center;">
                    Submitted via Granny B's Paint Advisor (QR Code)<br>
                    {timestamp}
                </p>
            </div>
        </body>
        </html>
        """

        brevo_url = "https://api.brevo.com/v3/smtp/email"

        brevo_data = {
            "sender": {
                "name": "Granny B's QR Advisor",
                "email": "hello@grannyb.co.za"
            },
            "to": [
                {
                    "email": "design@summitwebcraft.co.za",
                    "name": "Granny B's Paint Advisor"
                },
                {
                    "email": "hello@grannyb.co.za",
                    "name": "Granny B's"
                },
                {
                    "email": "dcwgw@hotmail.com",
                    "name": "Granny B's Backup"
                }
            ],
            "replyTo": {
                "email": email,
                "name": name
            },
            "subject": f"New Lead from Granny B's QR Advisor at Leroy Merlin - {name}",
            "htmlContent": email_html
        }

        req = urllib.request.Request(
            brevo_url,
            json.dumps(brevo_data).encode(),
            {
                'Content-Type': 'application/json',
                'api-key': brevo_key
            }
        )

        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode())
                success = True
                message = "You're all set! Enjoy your paint advice."
        except urllib.error.HTTPError as e:
            error_body = e.read().decode() if e.fp else ''
            print(f"Brevo Error: {e.code} - {error_body}")
            success = False
            message = "There was an issue saving your details. No worries, you can still chat!"
        except Exception as e:
            print(f"Error: {str(e)}")
            success = False
            message = "There was an issue saving your details. No worries, you can still chat!"

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({'success': success, 'message': message}).encode())

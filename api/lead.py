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
        interest_type = data.get('interestType', 'Not specified')
        organisation = data.get('organisation', 'Not specified')
        details = data.get('details', 'No additional details')
        
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
            <div style="background: linear-gradient(135deg, #CC5500 0%, #8B3A00 100%); padding: 20px; text-align: center;">
                <h1 style="color: white; margin: 0;">New Enquiry from HAIBO PHANDA</h1>
            </div>
            
            <div style="padding: 30px; background: #f8f9fa;">
                <h2 style="color: #333; border-bottom: 2px solid #CC5500; padding-bottom: 10px;">Contact Details</h2>
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
                </table>
                
                <h2 style="color: #333; border-bottom: 2px solid #CC5500; padding-bottom: 10px; margin-top: 30px;">Enquiry Details</h2>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 10px 0; font-weight: bold; width: 140px;">Interested In:</td>
                        <td style="padding: 10px 0;">{interest_type}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px 0; font-weight: bold;">Organisation:</td>
                        <td style="padding: 10px 0;">{organisation}</td>
                    </tr>
                </table>
                
                <h2 style="color: #333; border-bottom: 2px solid #CC5500; padding-bottom: 10px; margin-top: 30px;">Additional Details</h2>
                <p style="background: white; padding: 15px; border-radius: 8px; border: 1px solid #e1e8ed;">{details}</p>
                
                <p style="color: #666; font-size: 12px; margin-top: 30px; text-align: center;">
                    Submitted via HAIBO PHANDA AI Assistant (Onalerona)<br>
                    {timestamp}
                </p>
            </div>
        </body>
        </html>
        """
        
        brevo_url = "https://api.brevo.com/v3/smtp/email"
        
        brevo_data = {
            "sender": {
                "name": "HAIBO PHANDA AI",
                "email": "ai@haibophanda.org.za"
            },
            "to": [
                {
                    "email": "ai@haibophanda.org.za",
                    "name": "HAIBO PHANDA"
                }
            ],
            "replyTo": {
                "email": email,
                "name": name
            },
            "subject": f"🔥 New Enquiry: {name} - {interest_type}",
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
                message = "Sharp sharp! Your details have been submitted. We'll be in touch soon. Remember, everything we offer is 100% FREE!"
        except urllib.error.HTTPError as e:
            error_body = e.read().decode() if e.fp else ''
            print(f"Brevo Error: {e.code} - {error_body}")
            success = False
            message = "Eish, there was an issue. Please email us directly at ai@haibophanda.org.za"
        except Exception as e:
            print(f"Error: {str(e)}")
            success = False
            message = "Eish, there was an issue. Please email us directly at ai@haibophanda.org.za"
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({'success': success, 'message': message}).encode())

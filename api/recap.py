from http.server import BaseHTTPRequestHandler
import json
import urllib.request
import os

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

        api_key = os.environ.get('ANTHROPIC_API_KEY')

        if not api_key:
            self.send_error(500, "API key not configured")
            return

        history = data.get('history', [])
        language = data.get('language', 'en')

        if not history:
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'success': False, 'error': 'No conversation history'}).encode())
            return

        conversation_text = ""
        for msg in history:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            conversation_text += f"{role}: {content}\n"

        system_prompt = """You are a data extraction assistant. Extract structured paint project data from the conversation below.

Return ONLY valid JSON with these fields (use empty string "" if not mentioned):
{
  "projectType": "e.g. Furniture project, Kitchen cabinets, Upcycle, Wall, Arts & crafts",
  "specificPiece": "e.g. Dresser, Cabinet doors, Old chair, Bedroom accent wall",
  "surface": "e.g. Bare wood, Melamine, Metal, Stained wood",
  "dreamLook": "e.g. Vintage distressed, Clean modern, Rustic farmhouse",
  "recommendedColour": "e.g. Daisy, Hurricane, Vanilla Cream",
  "sealer": "e.g. Armour Sealer, Clear Wax, Classic Seal",
  "prepSteps": "Brief prep instructions as mentioned by the advisor",
  "paintSteps": "Brief painting instructions as mentioned by the advisor",
  "sealSteps": "Brief sealing instructions as mentioned by the advisor",
  "leroyProducts": "Any Leroy Merlin complementary products mentioned with aisle numbers"
}

Extract what was actually discussed. Do not invent information not present in the conversation."""

        url = "https://api.anthropic.com/v1/messages"

        api_data = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 512,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": conversation_text}
            ]
        }

        req = urllib.request.Request(url, json.dumps(api_data).encode(), {
            'Content-Type': 'application/json',
            'x-api-key': api_key,
            'anthropic-version': '2023-06-01'
        })

        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode())
                raw_text = result['content'][0]['text']

                start = raw_text.find('{')
                end = raw_text.rfind('}') + 1
                if start >= 0 and end > start:
                    recap = json.loads(raw_text[start:end])
                else:
                    recap = json.loads(raw_text)

                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'success': True, 'recap': recap}).encode())

        except Exception as e:
            print(f"Recap Error: {str(e)}")
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'success': False, 'error': 'Could not extract recap'}).encode())

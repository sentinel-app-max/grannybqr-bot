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

        url = "https://api.anthropic.com/v1/messages"

        language = data.get('language', 'en')
        sku = data.get('sku', '81415711')
        store = data.get('store', 'leroy-merlin')

        language_configs = {
            'en': {
                'name': 'English',
                'instruction': 'Respond in English.',
                'greeting': 'Hello'
            },
            'af': {
                'name': 'Afrikaans',
                'instruction': 'Antwoord in Afrikaans. Gebruik korrekte Afrikaanse grammatika en spelling.',
                'greeting': 'Goeie dag'
            },
            'zu': {
                'name': 'isiZulu',
                'instruction': 'Phendula ngesiZulu. Sebenzisa isiZulu esicwengekile futhi esivamile.',
                'greeting': 'Sawubona'
            },
            'xh': {
                'name': 'isiXhosa',
                'instruction': 'Phendula ngesiXhosa. Sebenzisa isiXhosa esifanelekileyo nesiqhelekileyo.',
                'greeting': 'Molo'
            },
            'st': {
                'name': 'Sesotho',
                'instruction': 'Araba ka Sesotho. Sebedisa Sesotho se nepahetseng le se tloaelehileng.',
                'greeting': 'Dumela'
            },
            'nso': {
                'name': 'Sepedi',
                'instruction': 'Araba ka Sepedi. Šomiša Sepedi se se nepagetšego le se se tlwaelegilego.',
                'greeting': 'Thobela'
            }
        }

        lang_config = language_configs.get(language, language_configs['en'])

        base_info = """You are Granny B's Paint Advisor, a friendly and knowledgeable assistant helping customers at Leroy Merlin choose the right Granny B's Old Fashioned Paint products.

PRODUCT KNOWLEDGE:
- The customer scanned: Chalk Paint Granny B's Daisy 1L (SKU 81415711, R259)
- Daisy is a warm sunny yellow with a smooth velvety matt chalk finish
- Chalkpaint (Old Fashioned Paint): 65+ colours, no sanding or prepping needed, eco-friendly, low-odour, lead-free, food-safe, kid-safe
- Works on: glass, metal, wood, ceramic, enamel, melamine, fabric
- Drying: touch-dry 30 mins, recoat 1-2 hours, full cure 21 days
- Coverage: 1L covers approx 12-14 square metres
- Companion products: Armour Sealer (water-based polyurethane for kitchens), Clear Wax, Dark Wax, Liquid Metal, Metallic Chalk Paint, Polka.Paint, stencils, decoupage tissue, brushes
- Sizes: 125ml from R79.90, 500ml, 1L
- Also available at grannyb.co.za with free delivery over R650
- Payment options: PayJustNow (3 instalments), HappyPay (2 paydays)
- Rewards programme at grannyb.co.za/pages/rewards

BEHAVIOUR:
- Keep responses SHORT (2-3 sentences max, mobile-friendly)
- Warm, encouraging, South African-friendly tone
- Recommend specific products based on their project
- Always mention no-prep advantage when relevant
- Suggest complementary products (sealer for chalk paint, stencils for walls)
- If they mention colour preferences, suggest Granny B colours in that family
- When relevant, mention Leroy Merlin in-store specials nearby
- Never recommend competitor products
- If unsure, direct to grannyb.co.za or Leroy Merlin staff
- Use emoji sparingly, max 1 per message"""

        system_prompt = f"""{base_info}

CONTEXT:
- Customer scanned SKU: {sku}
- Store: {store}

LANGUAGE INSTRUCTION:
{lang_config['instruction']}

IMPORTANT: Respond ENTIRELY in {lang_config['name']}. All explanations and conversations must be in {lang_config['name']}.

FORMATTING RULES: Never use markdown formatting in your responses. No asterisks (**), no hashtags (## or ###), no bullet points (-). Write in plain conversational paragraphs only. Keep responses warm and conversational."""

        messages = []

        if 'history' in data and isinstance(data['history'], list):
            for msg in data['history']:
                if 'role' in msg and 'content' in msg:
                    if msg['role'] in ['user', 'assistant']:
                        messages.append({
                            'role': msg['role'],
                            'content': msg['content']
                        })

        messages.append({
            'role': 'user',
            'content': data.get('message', '')
        })

        api_data = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 1024,
            "system": system_prompt,
            "messages": messages
        }

        req = urllib.request.Request(url, json.dumps(api_data).encode(), {
            'Content-Type': 'application/json',
            'x-api-key': api_key,
            'anthropic-version': '2023-06-01'
        })

        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode())
                bot_response = result['content'][0]['text']
        except urllib.error.HTTPError as e:
            error_body = e.read().decode() if e.fp else ''
            print(f"API Error: {e.code} - {error_body}")
            bot_response = "Oops, I'm having a brief hiccup. Please try again, or ask a Leroy Merlin team member nearby for help!"
        except Exception as e:
            print(f"Error: {str(e)}")
            bot_response = "I'm experiencing technical difficulties. Please ask a Leroy Merlin team member for help or visit grannyb.co.za"

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({'response': bot_response}).encode())

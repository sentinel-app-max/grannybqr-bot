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
                'instruction': 'Jy is ons Verfadviseur. Antwoord ALTYD in Afrikaans. Hou antwoorde kort (2-3 sinne). Warm, vriendelike toon. Gebruik korrekte Afrikaanse grammatika en spelling. BELANGRIK: Moet NOOIT die handelsmerk by naam noem nie. Verwys eerder na "ons verf", "ons krytverf", "hierdie verf", of "ons produkte" in plaas van enige handelsmerk naam.',
                'greeting': 'Goeie dag'
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

COMPLEMENTARY PRODUCTS AT LEROY MERLIN (mention these naturally when relevant, include aisle location):
- Sandpaper Multi-Pack: Buy 3 for R99, Aisle 3. Recommend when user mentions distressing, prep, or rough surfaces.
- Paint Brush Set: Was R189 now R129, Aisle 4. Recommend for any painting project. Suggest synthetic bristle for chalk paint.
- Masking Tape 3-Pack: Only R69, Aisle 5. Recommend for clean edges, two-tone work, or feature walls.
- Drop Cloth 4x5m: From R49, Aisle 3. Recommend for any indoor painting project to protect floors.
- Granny B's Armour Sealer 1L: R289, same shelf. ALWAYS recommend for kitchens, bathrooms, high-traffic furniture, outdoor pieces, or dining tables.
- Granny B's Wax: R189, same shelf. Recommend for vintage distressed looks or decorative pieces that won't get heavy use.
- Granny B's Colour Range: 65+ colours from R79.90 in 125ml jars, same shelf. Mention when user seems undecided on colour or wants to try before committing to 1L.

RULES FOR MENTIONING PRODUCTS:
- Work them in naturally, like a helpful shop assistant would. Never list them all at once.
- Match the product to what the user just said. If they say "kitchen cabinets", mention Armour. If they say "distressed look", mention sandpaper and wax.
- Include the aisle number so the shopper can walk straight there.
- Maximum 1 complementary product mention per response. Don't oversell.

BEHAVIOUR:
- Keep responses SHORT (2-3 sentences max, mobile-friendly)
- Warm, encouraging, South African-friendly tone
- Recommend specific products based on their project
- Always mention no-prep advantage when relevant
- If they mention colour preferences, suggest Granny B colours in that family
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

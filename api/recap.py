from http.server import BaseHTTPRequestHandler
import json
import urllib.request
import os
import re

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
        brevo_key = os.environ.get('BREVO_API_KEY')

        if not api_key:
            self._respond({'success': False, 'error': 'API key not configured'})
            return

        # Accept both field names for backwards compatibility
        history = data.get('chatHistory', data.get('history', []))
        language = data.get('language', 'en')
        name = data.get('name', '')
        email = data.get('email', '')
        answers = data.get('answers', [])
        flow = data.get('flow', 'product')
        sku = data.get('sku', '')
        store = data.get('store', 'leroy-merlin')

        if not history:
            self._respond({'success': False, 'error': 'No conversation history'})
            return

        # Step 1: Extract structured recap via Claude
        recap = self._extract_recap(api_key, history)

        if not recap:
            print(f"Recap extraction failed for {email or 'unknown'}, history length: {len(history)}")
            self._respond({'success': False, 'error': 'Could not extract recap'})
            return

        print(f"Recap extracted OK: {json.dumps(recap)[:500]}")

        # Step 2: Send Granny's Recipe email via Brevo (if email provided)
        email_sent = False
        if email and brevo_key:
            email_sent = self._send_recipe_email(brevo_key, name, email, language, recap, flow, sku, store)

        self._respond({'success': True, 'recap': recap, 'emailSent': email_sent})

    def _respond(self, data):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _extract_recap(self, api_key, history):
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
                print(f"Claude recap raw: {raw_text[:300]}")

                start = raw_text.find('{')
                end = raw_text.rfind('}') + 1
                if start >= 0 and end > start:
                    parsed = json.loads(raw_text[start:end])
                else:
                    parsed = json.loads(raw_text)

                # Validate we got at least some content
                has_content = any(parsed.get(k) for k in ['projectType', 'recommendedColour', 'prepSteps', 'paintSteps'])
                if not has_content:
                    print(f"Warning: recap parsed but all fields empty: {parsed}")

                return parsed
        except json.JSONDecodeError as e:
            print(f"Recap JSON parse error: {str(e)}, raw: {raw_text[:200] if 'raw_text' in dir() else 'N/A'}")
            return None
        except Exception as e:
            print(f"Recap extraction error: {str(e)}")
            return None

    def _send_recipe_email(self, brevo_key, name, email, language, recap, flow, sku, store):
        is_af = language == 'af'

        display_name = name if name else ('Vriend' if is_af else 'Friend')

        subject = f"Hier is jou resep van Granny B's, {display_name}! \U0001f3a8" if is_af else f"Here's your recipe from Granny B's, {display_name}! \U0001f3a8"

        title = "Granny se Resep" if is_af else "Granny's Recipe"
        subtitle = "Jou persoonlike krytverf plan" if is_af else "Your personal chalk paint plan"

        lbl_project = "Projek" if is_af else "Project"
        lbl_surface = "Oppervlak" if is_af else "Surface"
        lbl_look = "Voorkoms" if is_af else "Look"
        lbl_colour = "Aanbevole Kleur" if is_af else "Recommended Colour"
        lbl_sealer = "Seler" if is_af else "Sealer"
        lbl_prep = "VOORBEREIDING" if is_af else "PREP"
        lbl_paint = "VERF" if is_af else "PAINT"
        lbl_seal = "SEEL" if is_af else "SEAL"
        lbl_leroy = "Leroy Merlin Produkte" if is_af else "Leroy Merlin Products"
        lbl_discount = "Afslagkode" if is_af else "Discount Code"
        lbl_discount_note = "10% afslag op jou volgende Granny B's aanlyn bestelling" if is_af else "10% off your next Granny B's online order"
        lbl_shop = "Koop Granny B's Aanlyn" if is_af else "Shop Granny B's Online"
        lbl_footer = "Jy het hierdie resep ontvang van Granny B's se Verfadviseur by Leroy Merlin." if is_af else "You received this recipe from Granny B's Paint Advisor at Leroy Merlin."

        r = recap
        project_text = r.get('projectType', '')
        if r.get('specificPiece'):
            project_text += f" \u2014 {r['specificPiece']}"

        # Build detail rows
        detail_rows = ""
        if project_text:
            detail_rows += self._email_row(lbl_project, project_text)
        if r.get('surface'):
            detail_rows += self._email_row(lbl_surface, r['surface'])
        if r.get('dreamLook'):
            detail_rows += self._email_row(lbl_look, r['dreamLook'])
        if r.get('recommendedColour'):
            detail_rows += self._email_row(lbl_colour, r['recommendedColour'], '#DD2222', 'https://www.grannyb.co.za/collections/old-fashioned-paint')
        if r.get('sealer'):
            detail_rows += self._email_row(lbl_sealer, r['sealer'])

        # Build steps sections
        steps_html = ""
        if r.get('prepSteps'):
            steps_html += self._email_step_section(lbl_prep, r['prepSteps'], '#FF9800')
        if r.get('paintSteps'):
            steps_html += self._email_step_section(lbl_paint, r['paintSteps'], '#DD2222')
        if r.get('sealSteps'):
            steps_html += self._email_step_section(lbl_seal, r['sealSteps'], '#4CAF50')

        leroy_html = ""
        if r.get('leroyProducts'):
            linked_products = self._linkify_leroy_products(r['leroyProducts'])
            leroy_html = f"""
            <div style="margin-top:20px;padding:16px;background:#F5F5F5;border-radius:8px;">
                <h3 style="margin:0 0 8px 0;font-size:14px;color:#1A1A1A;">{lbl_leroy}</h3>
                <p style="margin:0;font-size:13px;color:#555;line-height:1.8;white-space:pre-line;">{linked_products}</p>
            </div>"""

        email_html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><meta http-equiv="Content-Type" content="text/html; charset=UTF-8"></head>
<body style="margin:0;padding:0;font-family:'Segoe UI',Tahoma,Geneva,Verdana,sans-serif;background:#F5F5F5;-webkit-text-size-adjust:100%;-ms-text-size-adjust:100%;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#F5F5F5;padding:20px 0;">
<tr><td align="center">
<table width="100%" cellpadding="0" cellspacing="0" style="max-width:600px;background:#FFFFFF;border-radius:12px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.08);">

    <!-- Header -->
    <tr><td style="background:#DD2222;padding:32px 24px;text-align:center;">
        <h1 style="margin:0;font-size:28px;color:#FFFFFF;">\U0001f3a8 {title}</h1>
        <p style="margin:6px 0 0 0;font-size:14px;color:rgba(255,255,255,0.85);">{subtitle}</p>
    </td></tr>

    <!-- Greeting -->
    <tr><td style="padding:28px 24px 0 24px;">
        <p style="margin:0;font-size:16px;color:#1A1A1A;">Hi {self._escape(display_name)},</p>
        <p style="margin:8px 0 0 0;font-size:14px;color:#555;">{"Hier is jou persoonlike krytverf resep gebaseer op jou konsultasie." if is_af else "Here's your personalised chalk paint recipe based on your consultation."}</p>
    </td></tr>

    <!-- Details -->
    <tr><td style="padding:20px 24px;">
        <table width="100%" cellpadding="0" cellspacing="0" style="border:1px solid #F0E0E0;border-radius:8px;overflow:hidden;">
            {detail_rows}
        </table>
    </td></tr>

    <!-- Steps -->
    <tr><td style="padding:0 24px;">
        {steps_html}
    </td></tr>

    <!-- Leroy Products -->
    <tr><td style="padding:0 24px;">
        {leroy_html}
    </td></tr>

    <!-- Discount -->
    <tr><td style="padding:24px;text-align:center;">
        <div style="border:2px dashed #DD2222;border-radius:12px;padding:20px;display:inline-block;min-width:200px;">
            <p style="margin:0;font-size:12px;color:#8C8577;text-transform:uppercase;letter-spacing:1px;">{lbl_discount}</p>
            <p style="margin:6px 0;font-size:28px;font-weight:800;color:#1A1A1A;letter-spacing:3px;">GRANNYB10</p>
            <p style="margin:0;font-size:13px;color:#7A9B6D;font-weight:600;">{lbl_discount_note}</p>
            <p style="margin:10px 0 0 0;font-size:12px;"><a href="https://www.grannyb.co.za" target="_blank" style="color:#DD2222;text-decoration:underline;">grannyb.co.za</a></p>
        </div>
    </td></tr>

    <!-- CTA -->
    <tr><td style="padding:0 24px 24px;text-align:center;">
        <a href="https://www.grannyb.co.za/collections/old-fashioned-paint" target="_blank" style="display:inline-block;background:#DD2222;color:#FFFFFF;text-decoration:none;padding:14px 32px;border-radius:8px;font-size:15px;font-weight:700;">{lbl_shop} &rarr;</a>
    </td></tr>

    <!-- Footer -->
    <tr><td style="padding:20px 24px;text-align:center;border-top:1px solid #F0E0E0;">
        <p style="margin:0;font-size:11px;color:#8C8577;">{lbl_footer}</p>
        <p style="margin:8px 0 0 0;font-size:12px;"><a href="https://grannybqr.summitwebcraft.co.za/?store=leroy-fourways" target="_blank" style="color:#DD2222;text-decoration:underline;font-weight:600;">Try Granny B's Paint Advisor &rarr;</a></p>
        <p style="margin:8px 0 0 0;font-size:11px;color:#8C8577;">Powered by SUMMITWEBCRAFT &times; Granny B's &times; Leroy Merlin</p>
    </td></tr>

</table>
</td></tr>
</table>
</body></html>"""

        # Debug: verify HTML contains real <a> tags, not escaped
        has_a_tags = '<a href=' in email_html
        has_escaped_tags = '&lt;a href=' in email_html
        print(f"Email HTML length: {len(email_html)}, has <a> tags: {has_a_tags}, has escaped tags: {has_escaped_tags}")
        print(f"Email htmlContent first 500 chars: {email_html[:500]}")

        brevo_url = "https://api.brevo.com/v3/smtp/email"

        brevo_data = {
            "sender": {
                "name": "Granny B's Paint Advisor",
                "email": "hello@grannyb.co.za"
            },
            "to": [
                {
                    "email": email,
                    "name": display_name
                }
            ],
            "subject": subject,
            "htmlContent": email_html
        }

        payload = json.dumps(brevo_data, ensure_ascii=False).encode('utf-8')
        print(f"Brevo payload keys: {list(brevo_data.keys())}, payload size: {len(payload)}")

        req = urllib.request.Request(
            brevo_url,
            payload,
            {
                'Content-Type': 'application/json; charset=utf-8',
                'Accept': 'application/json',
                'api-key': brevo_key
            }
        )

        try:
            with urllib.request.urlopen(req) as response:
                json.loads(response.read().decode())
                return True
        except urllib.error.HTTPError as e:
            error_body = e.read().decode() if e.fp else ''
            print(f"Brevo Recap Email Error: {e.code} - {error_body}")
            return False
        except Exception as e:
            print(f"Recap Email Error: {str(e)}")
            return False

    def _email_row(self, label, value, value_color='#1A1A1A', link=None):
        escaped_value = self._escape(value)
        if link:
            value_html = f'<a href="{link}" target="_blank" style="color:#DD2222;text-decoration:underline;">{escaped_value}</a>'
        else:
            value_html = escaped_value
        return f"""<tr>
                <td style="padding:10px 14px;font-size:12px;font-weight:600;color:#8C8577;width:140px;border-bottom:1px solid #F5F5F5;">{self._escape(label)}</td>
                <td style="padding:10px 14px;font-size:14px;color:{value_color};border-bottom:1px solid #F5F5F5;">{value_html}</td>
            </tr>"""

    def _email_step_section(self, label, content, accent_color):
        return f"""<div style="margin-top:16px;padding:16px;background:#FFFDF5;border-left:4px solid {accent_color};border-radius:4px;">
                <h3 style="margin:0 0 8px 0;font-size:14px;color:{accent_color};">{self._escape(label)}</h3>
                <p style="margin:0;font-size:13px;color:#555;line-height:1.6;white-space:pre-line;">{self._escape(content)}</p>
            </div>"""

    LEROY_PRODUCT_LINKS = [
        ('sandpaper', 'https://www.leroymerlin.co.za/search?q=sandpaper'),
        ('skuurpapier', 'https://www.leroymerlin.co.za/search?q=sandpaper'),
        ('paint brush', 'https://www.leroymerlin.co.za/search?q=paint+brush+set'),
        ('brush set', 'https://www.leroymerlin.co.za/search?q=paint+brush+set'),
        ('verfkwas', 'https://www.leroymerlin.co.za/search?q=paint+brush+set'),
        ('masking tape', 'https://www.leroymerlin.co.za/search?q=masking+tape'),
        ('maskeerband', 'https://www.leroymerlin.co.za/search?q=masking+tape'),
        ('drop cloth', 'https://www.leroymerlin.co.za/search?q=drop+cloth'),
        ('stooflap', 'https://www.leroymerlin.co.za/search?q=drop+cloth'),
        ('armour sealer', 'https://www.leroymerlin.co.za/search?q=granny+b+armour'),
        ('armour', 'https://www.leroymerlin.co.za/search?q=granny+b+armour'),
    ]

    def _linkify_leroy_products(self, text):
        escaped = self._escape(text)
        linked_urls = set()
        for keyword, url in self.LEROY_PRODUCT_LINKS:
            if url in linked_urls:
                continue
            pattern = re.compile(re.escape(self._escape(keyword)), re.IGNORECASE)
            match = pattern.search(escaped)
            if match:
                matched_text = match.group(0)
                link_html = f'<a href="{url}" target="_blank" style="color:#DD2222;text-decoration:underline;">{matched_text}</a>'
                escaped = escaped[:match.start()] + link_html + escaped[match.end():]
                linked_urls.add(url)
        return escaped

    @staticmethod
    def _escape(text):
        if not text:
            return ''
        return str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

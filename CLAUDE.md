# Granny B's Paint Advisor — In-Store QR Bot

## Purpose
In-store QR code chatbot for **Granny B's Old Fashioned Paint** at **Leroy Merlin** stores.
Customers scan a QR code on the product shelf to get instant paint advice, project guidance,
and product recommendations powered by Claude AI.

## Tech Stack
- **Frontend**: Single-page HTML app (vanilla JS, no frameworks)
- **Backend**: Python serverless functions (stdlib only, zero dependencies)
- **Hosting**: Vercel (serverless deployment)
- **AI**: Anthropic Claude (`claude-sonnet-4-20250514`)
- **Voice**: OpenAI Whisper (STT), ElevenLabs + Google Cloud (TTS)
- **Email**: Brevo (formerly Sendinblue) for lead capture

## File Structure
```
grannybqr-bot/
├── public/
│   └── index.html           # Complete SPA (UI, CSS, JS)
├── api/
│   ├── chat.py               # Claude AI chat endpoint
│   ├── chat.py.backup         # Old HAIBO PHANDA version (archived)
│   ├── lead.py                # Lead capture + Brevo email
│   ├── stt.py                 # Speech-to-text (OpenAI Whisper)
│   └── tts.py                 # Text-to-speech (ElevenLabs/Google)
├── vercel.json                # Vercel routing config
├── requirements.txt           # Python deps (none — stdlib only)
├── CLAUDE.md                  # This file
└── .gitignore
```

## Production URL
`https://grannybqr.summitwebcraft.co.za`

## URL Schema & Dual Flow Routing
The app supports two flows based on the `?sku=` URL parameter:

| Param   | Description                                    | Default          |
|---------|------------------------------------------------|------------------|
| `sku`   | Product SKU scanned (triggers product flow)    | _(empty)_        |
| `store` | Store identifier (e.g. `leroy-fourways`)       | `leroy-merlin`   |

**Routing logic:**
- `?sku=81415711&store=leroy-fourways` → **Product Flow** (existing single-product mode)
- `?store=leroy-fourways` (no SKU) → **Consultation Flow** (full range advisory mode)

Both flows share the same lead form, header, promo triggers, thank you screen, and chat infrastructure.

## Flow 1: Product Mode (SKU present)
URL example: `https://grannybqr.summitwebcraft.co.za/?sku=81415711&store=leroy-fourways`

1. **Lead Form** — Captures first name, email, mobile with POPIA consent. Can skip.
2. **Product Badge** — Shows scanned product (Daisy 1L, R259, SKU) with Done button.
3. **4 Guided Questions:**
   - Q1: What are you painting today?
   - Q2: What surface will you be painting on?
   - Q3: Have you used chalk paint before?
   - Q4: What look are you going for?
4. **Free Chat** — Product-focused advice about the scanned item.
5. **Promo Cards** — Keyword-triggered. Armour Sealer auto-shows after Q2.
6. **Thank You** — Discount code GRANNYB10, shop links.

### Daisy Product Knowledge
- **Product**: Chalk Paint Granny B's Daisy 1L | **SKU**: 81415711 | **Price**: R259
- **Colour**: Warm sunny yellow, smooth velvety matt chalk finish
- **Coverage**: 12–14 sqm/L | **Dry**: Touch-dry 30 min, recoat 1–2 hrs, full cure 21 days
- **Surfaces**: Glass, metal, wood, ceramic, enamel, melamine, fabric
- **Properties**: Eco-friendly, low-odour, lead-free, food-safe, kid-safe

## Flow 2: Consultation Mode (no SKU)
URL example: `https://grannybqr.summitwebcraft.co.za/?store=leroy-fourways`

1. **Lead Form** — Same as product flow.
2. **No Product Badge** — Done button moves to header.
3. **5 Guided Questions:**
   - Q1: What brings you here today? (project type)
   - Q2: Conditional follow-up based on Q1 answer (specific piece/item)
   - Q3: What surface are we working with?
   - Q4: What's the dream? (desired aesthetic)
   - Q5: Experience with chalk paint?
4. **AI delivers full personalised recommendation** after Q5: colour(s), tin size, surface prep, sealer, complementary products, adjusted to experience level.
5. **Free Chat** — Full range advisory.
6. **Promo Cards** — Surface-based triggers after Q3, distress trigger after Q4, brush set after Q5.
7. **Thank You** — Same as product flow.

### Colour Recommendations (AI knowledge)
Daisy, Hessian, Hurricane, Vanilla Cream, Olive Charm, Peppermint Twist, Pretty Flamingo, Tropical Cocktail, Mushroom, Midnight Sky, Classic White, French Lavender, Fired Brick — each matched to aesthetic/project types.

## Leroy Merlin Promo Card Triggers
| Trigger Keywords                     | Product                      | Deal              | Location   |
|--------------------------------------|------------------------------|--------------------|------------|
| sand, prep, wood                     | Sandpaper Multi-Pack         | Buy 3 for R99      | Aisle 3    |
| brush, tool, roller                  | Premium Brush Set            | Was R189 → R129    | Aisle 4    |
| edge, clean, line, tape              | Masking Tape 3-Pack          | Only R69            | Aisle 5    |
| floor, protect, mess                 | Drop Cloth 4×5m              | From R49            | Aisle 3    |
| seal, protect, kitchen, water, durable | Granny B's Armour Sealer 1L | R289               | Same shelf |
| colour, color, other, different, range | 65+ Chalk Paint Colours     | From R79.90         | Same shelf |

## Brand Voice Rules
- Warm, encouraging, South African-friendly tone
- Short responses (2–3 sentences max, mobile-friendly)
- Emoji: max 1 per message
- Never recommend competitor products
- Always mention no-prep advantage when relevant
- Suggest complementary Granny B's products
- Direct to grannyb.co.za or Leroy Merlin staff if unsure

## Brand Colours
| Token        | Hex       | Usage                              |
|--------------|-----------|------------------------------------|
| Primary      | `#DD2222` | Granny B's red — header, buttons   |
| Background   | `#FFFFFF` | White — page background            |
| Text         | `#1A1A1A` | Charcoal — primary text            |
| Muted        | `#8C8577` | Muted text                         |
| Accent       | `#7A9B6D` | Sage green — success states        |
| Bot bubble   | `#FFFFFF` | White with #F0E0E0 border          |
| User bubble  | `#1A1A1A` | Charcoal with white text           |
| Product badge| `#FFF5F5` | Light pink bg, #DD2222 border      |
| Swatch       | `#F7E07D` | Daisy yellow (product colour)      |
| Recording    | `#e74c3c` | Red — mic recording indicator      |

Visual features: radial sunburst conic-gradient (red/white, circus style) at low opacity on backgrounds, paint tin watermark repeat on chat area.

## Environment Variables
```
ANTHROPIC_API_KEY       # Anthropic API for Claude chat
OPENAI_API_KEY          # OpenAI API for Whisper STT
ELEVENLABS_API_KEY      # ElevenLabs API for TTS voice
GOOGLE_TTS_API_KEY      # Google Cloud API for Afrikaans TTS
BREVO_API_KEY           # Brevo/Sendinblue for email delivery
```

## Deploy
```bash
# Production (auto-deploys on push to main)
# Custom domain: grannybqr.summitwebcraft.co.za
git push origin main

# Local development
vercel dev
```

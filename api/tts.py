from http.server import BaseHTTPRequestHandler
import json
import urllib.request
import os
import base64

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
        
        text = data.get('text', '')
        language = data.get('language', 'en')
        
        if not text:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'No text provided'}).encode())
            return
        
        if len(text) > 1000:
            text = text[:1000]
        
        # Use Google TTS for Afrikaans, ElevenLabs for everything else
        if language == 'af':
            audio_base64 = self.google_tts(text)
        else:
            audio_base64 = self.elevenlabs_tts(text)
        
        if audio_base64:
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({
                'audio': audio_base64,
                'format': 'mp3'
            }).encode())
        else:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'TTS generation failed'}).encode())
    
    def google_tts(self, text):
        api_key = os.environ.get('GOOGLE_TTS_API_KEY')
        
        if not api_key:
            return None
        
        url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={api_key}"
        
        payload = {
            "input": {"text": text},
            "voice": {
                "languageCode": "af-ZA",
                "name": "af-ZA-Standard-A",
                "ssmlGender": "FEMALE"
            },
            "audioConfig": {
                "audioEncoding": "MP3",
                "speakingRate": 1.0,
                "pitch": 0
            }
        }
        
        try:
            req = urllib.request.Request(
                url,
                json.dumps(payload).encode(),
                {'Content-Type': 'application/json'}
            )
            
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode())
                return result.get('audioContent', None)
                
        except Exception as e:
            print(f"Google TTS Error: {str(e)}")
            return None
    
    def elevenlabs_tts(self, text):
        api_key = os.environ.get('ELEVENLABS_API_KEY')
        
        if not api_key:
            return None
        
        voice_id = "SAhdygBsjizE9aIj39dz"  # Granny B's voice
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        
        payload = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
                "style": 0.0,
                "use_speaker_boost": True
            }
        }
        
        try:
            req = urllib.request.Request(
                url,
                json.dumps(payload).encode(),
                {
                    'Content-Type': 'application/json',
                    'xi-api-key': api_key,
                    'Accept': 'audio/mpeg'
                }
            )
            
            with urllib.request.urlopen(req) as response:
                audio_data = response.read()
                return base64.b64encode(audio_data).decode('utf-8')
                
        except Exception as e:
            print(f"ElevenLabs Error: {str(e)}")
            return None

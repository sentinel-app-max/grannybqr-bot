from http.server import BaseHTTPRequestHandler
import json
import urllib.request
import os
import cgi
import io

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        return

    def do_POST(self):
        api_key = os.environ.get('OPENAI_API_KEY')
        
        if not api_key:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'STT not configured'}).encode())
            return
        
        content_type = self.headers.get('Content-Type', '')
        
        try:
            if 'multipart/form-data' in content_type:
                # Handle FormData upload
                form = cgi.FieldStorage(
                    fp=self.rfile,
                    headers=self.headers,
                    environ={'REQUEST_METHOD': 'POST', 'CONTENT_TYPE': content_type}
                )
                
                # Accept both 'audio_file' (iOS) and 'audio' (legacy)
                audio_field = None
                for field_name in ['audio_file', 'audio', 'file']:
                    if field_name in form:
                        audio_field = field_name
                        break
                
                if not audio_field:
                    raise ValueError('No audio file in form data')
                
                audio_item = form[audio_field]
                audio_bytes = audio_item.file.read()
                filename = audio_item.filename or 'audio.m4a'
                
                # Determine content type from filename
                if filename.endswith('.webm'):
                    mime_type = 'audio/webm'
                elif filename.endswith('.m4a') or filename.endswith('.mp4'):
                    mime_type = 'audio/mp4'
                else:
                    mime_type = 'audio/mpeg'
                    
            else:
                # Handle JSON with base64 (fallback for non-iOS)
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data)
                
                import base64
                audio_bytes = base64.b64decode(data.get('audio', ''))
                filename = 'audio.m4a'
                mime_type = 'audio/mp4'
            
            if len(audio_bytes) < 1000:
                raise ValueError('Audio too short')
            
            # Create multipart form data for OpenAI
            boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
            
            body = []
            body.append(f'--{boundary}'.encode())
            body.append(f'Content-Disposition: form-data; name="file"; filename="{filename}"'.encode())
            body.append(f'Content-Type: {mime_type}'.encode())
            body.append(b'')
            body.append(audio_bytes)
            body.append(f'--{boundary}'.encode())
            body.append(b'Content-Disposition: form-data; name="model"')
            body.append(b'')
            body.append(b'whisper-1')
            body.append(f'--{boundary}--'.encode())
            
            body_data = b'\r\n'.join(body)
            
            req = urllib.request.Request(
                'https://api.openai.com/v1/audio/transcriptions',
                body_data,
                {
                    'Authorization': f'Bearer {api_key}',
                    'Content-Type': f'multipart/form-data; boundary={boundary}'
                }
            )
            
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode())
                transcribed_text = result.get('text', '')
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'text': transcribed_text}).encode())
                
        except Exception as e:
            print(f"STT Error: {str(e)}")
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())

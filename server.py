"""Local web interface using only Python's standard library."""
import json
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError

from agent import ROOT, chat_turn, new_conversation
from check_api import load_settings

TOKEN = secrets.token_urlsafe(32)
LOCK = threading.Condition()
MESSAGES = new_conversation()
EVENTS = []
STATE = {'busy': False, 'pending': None, 'decision': None}
SETTINGS = None


def emit(kind, data):
    with LOCK:
        EVENTS.append({'kind': kind, 'data': data})


def approve(command):
    with LOCK:
        identity = secrets.token_hex(12)
        STATE['pending'] = {'id': identity, 'command': command}
        STATE['decision'] = None
        LOCK.wait_for(lambda: STATE['decision'] is not None, timeout=300)
        decision = STATE['decision'] is True
        STATE['pending'] = None
        STATE['decision'] = None
        return decision


def work(text):
    # Restore history if a request fails partway through a tool batch.
    saved = list(MESSAGES)
    try:
        chat_turn(SETTINGS, MESSAGES, text, approve, emit)
    except HTTPError as error:
        MESSAGES[:] = saved
        emit('error', f'API request failed (HTTP {error.code}). Check credits, model, or rate limits and retry.')
    except Exception:
        MESSAGES[:] = saved
        emit('error', 'The request failed. Check your connection and configuration, then retry.')
    finally:
        with LOCK:
            STATE['busy'] = False
            STATE['pending'] = None


class Handler(BaseHTTPRequestHandler):
    def reply(self, data, status=200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.headers.get('Host') not in ('127.0.0.1:8765', 'localhost:8765'):
            return self.reply({'error': 'Invalid host'}, 403)
        if self.path == '/':
            body = (ROOT / 'index.html').read_text(encoding='utf-8').replace('__TOKEN__', TOKEN).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(body)
        elif self.path == '/state' and self.headers.get('X-Session-Token') == TOKEN:
            with LOCK:
                self.reply({'events': EVENTS, 'busy': STATE['busy'], 'pending': STATE['pending']})
        else:
            self.reply({'error': 'Not found'}, 404)

    def do_POST(self):
        if self.headers.get('X-Session-Token') != TOKEN:
            return self.reply({'error': 'Invalid session'}, 403)
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if size < 1 or size > 32000:
                raise ValueError()
            data = json.loads(self.rfile.read(size))
            with LOCK:
                if self.path == '/chat':
                    text = data.get('text')
                    if STATE['busy']:
                        return self.reply({'error': 'A turn is already running'}, 409)
                    if not isinstance(text, str) or not text.strip():
                        raise ValueError()
                    STATE['busy'] = True
                    EVENTS.append({'kind': 'user', 'data': text})
                    threading.Thread(target=work, args=(text,), daemon=True).start()
                elif self.path == '/approve':
                    pending = STATE['pending']
                    if not pending or data.get('id') != pending['id'] or STATE['decision'] is not None:
                        return self.reply({'error': 'Approval is no longer pending'}, 409)
                    if not isinstance(data.get('approve'), bool):
                        raise ValueError()
                    STATE['decision'] = data['approve']
                    LOCK.notify_all()
                else:
                    return self.reply({'error': 'Not found'}, 404)
            self.reply({'ok': True})
        except (ValueError, TypeError, AttributeError):
            self.reply({'error': 'Invalid request'}, 400)

    def log_message(self, *args):
        pass


if __name__ == '__main__':
    SETTINGS = load_settings()
    print('Pedro Agent: http://127.0.0.1:8765 (Ctrl+C to stop)', flush=True)
    ThreadingHTTPServer(('127.0.0.1', 8765), Handler).serve_forever()

from http.server import BaseHTTPRequestHandler
from urllib import parse
import re
import socket
import json
from contextlib import closing


class ApiHandler(BaseHTTPRequestHandler):

    def do_POST(self):
        parsed_path = parse.urlparse(self.path)
        m = re.search('^/bot(.*)/([a-zA-Z0-9]+)', parsed_path.path)
        # token = m[1]
        method = m[2]
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        response = {
            'ok': True
        }
        if method == 'sendMessage':
            response['result'] = {'message_id': 1}
        self.wfile.write(bytes(json.dumps(response), 'ascii'))

    def log_message(self, format, *args):
        return

def get_free_port():
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]
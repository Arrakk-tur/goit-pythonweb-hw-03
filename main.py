from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import mimetypes
import pathlib
import json
from datetime import datetime
from jinja2 import Environment, FileSystemLoader

env = Environment(loader=FileSystemLoader('templates'))
DATA_FILE = pathlib.Path('storage/data.json')

class HttpHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        route = parsed_url.path

        if route == '/':
            self.send_html_file('index.html')
        elif route == '/message.html':
            self.send_html_file('message.html')
        elif route.startswith('/static/') or route in ['/style.css', '/logo.png']:
            self.send_static()
        elif route == '/read':
            self.render_messages()
        else:
            self.send_html_file('error.html', status=404)

    def do_POST(self):
        if self.path == '/message':
            length = int(self.headers.get('Content-Length', 0))
            data = self.rfile.read(length).decode()
            parsed_data = urllib.parse.unquote_plus(data)
            form = {k: v for k, v in (pair.split('=') for pair in parsed_data.split('&'))}

            timestamp = str(datetime.now())
            if not DATA_FILE.exists():
                DATA_FILE.parent.mkdir(exist_ok=True)
                with open(DATA_FILE, 'w') as f:
                    json.dump({}, f)

            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                messages = json.load(f)

            messages[timestamp] = form

            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                json.dump(messages, f, ensure_ascii=False, indent=2)

            self.send_response(302)
            self.send_header('Location', '/')
            self.end_headers()
        else:
            self.send_html_file('error.html', status=404)

    def send_html_file(self, filename, status=200):
        try:
            self.send_response(status)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            with open(f'templates/{filename}', 'rb') as file:
                self.wfile.write(file.read())
        except FileNotFoundError:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'File not found')

    def send_static(self):
        file_path = self.path.lstrip('/')
        full_path = pathlib.Path(file_path)

        if full_path.exists():
            self.send_response(200)
            mime_type, _ = mimetypes.guess_type(str(full_path))
            self.send_header("Content-type", mime_type or 'application/octet-stream')
            self.end_headers()
            with open(full_path, 'rb') as f:
                self.wfile.write(f.read())
        else:
            self.send_html_file('error.html', 404)

    def render_messages(self):
        if DATA_FILE.exists():
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                messages = json.load(f)
        else:
            messages = {}

        template = env.get_template('read.html')
        content = template.render(messages=messages)

        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(content.encode('utf-8'))


def run(server_class=HTTPServer, handler_class=HttpHandler):
    server_address = ('', 3000)
    httpd = server_class(server_address, handler_class)
    httpd.serve_forever()

if __name__ == '__main__':
    run()
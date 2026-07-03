#!/usr/bin/env python3
"""
interface_layer/serve.py
Option B: HTTP interface for the operator layer.
Exposes /health and /run endpoints.
Closes INTERFACE_GAP for non-Slack integrations.
"""
from __future__ import annotations
import json
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

CASE_DIR = Path('examples/bundle_forensics_case')


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # suppress default logging

    def _json(self, code: int, body: dict) -> None:
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())

    def do_GET(self) -> None:
        if self.path == '/health':
            self._json(200, {'ok': True, 'case_dir': str(CASE_DIR)})
        else:
            self._json(404, {'error': 'not found'})

    def do_POST(self) -> None:
        if self.path == '/run':
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length)) if length else {}
            case_dir = body.get('case_dir', str(CASE_DIR))
            result = subprocess.run(
                ['python3', 'run_operator_layer.py', case_dir],
                capture_output=True, text=True
            )
            self._json(200, {
                'returncode': result.returncode,
                'stdout': result.stdout[-2000:],
                'stderr': result.stderr[-500:],
            })
        else:
            self._json(404, {'error': 'not found'})


def main(host: str = '0.0.0.0', port: int = 8080) -> None:
    print(f'Operator HTTP interface running on {host}:{port}')
    HTTPServer((host, port), Handler).serve_forever()


if __name__ == '__main__':
    main()

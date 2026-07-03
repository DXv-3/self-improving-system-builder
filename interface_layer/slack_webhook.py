#!/usr/bin/env python3
"""
interface_layer/slack_webhook.py
Option C: Slack slash-command webhook handler for the operator layer.
Closes INTERFACE_GAP for Slack-based triggering.

Deploy behind a public endpoint (e.g. ngrok, Fly.io, Railway).
Set SLACK_SIGNING_SECRET env var.

Slack slash command payload arrives as application/x-www-form-urlencoded.
Responds with a Slack-compatible JSON message.
"""
from __future__ import annotations
import hashlib
import hmac
import json
import os
import subprocess
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs

SIGNING_SECRET = os.environ.get('SLACK_SIGNING_SECRET', '')


def verify_slack_signature(body: bytes, timestamp: str, signature: str) -> bool:
    if not SIGNING_SECRET:
        return True  # skip verification in dev
    if abs(time.time() - int(timestamp)) > 300:
        return False
    sig_base = f'v0:{timestamp}:{body.decode()}'
    expected = 'v0=' + hmac.new(
        SIGNING_SECRET.encode(), sig_base.encode(), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def _json(self, code: int, body: dict) -> None:
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())

    def do_POST(self) -> None:
        length = int(self.headers.get('Content-Length', 0))
        raw_body = self.rfile.read(length)
        timestamp = self.headers.get('X-Slack-Request-Timestamp', '0')
        signature = self.headers.get('X-Slack-Signature', '')
        if not verify_slack_signature(raw_body, timestamp, signature):
            self._json(403, {'error': 'invalid signature'})
            return
        params = parse_qs(raw_body.decode())
        command = params.get('command', [''])[0]
        text = params.get('text', [''])[0]
        case_dir = text.strip() or 'examples/bundle_forensics_case'
        result = subprocess.run(
            ['python3', 'run_operator_layer.py', case_dir],
            capture_output=True, text=True
        )
        self._json(200, {
            'response_type': 'in_channel',
            'text': (
                f'*Operator cycle triggered* on `{case_dir}`\n'
                f'Exit: `{result.returncode}`\n'
                f'```{result.stdout[-1000:]}```'
            ),
        })


def main(host: str = '0.0.0.0', port: int = 8081) -> None:
    print(f'Slack webhook handler running on {host}:{port}')
    HTTPServer((host, port), Handler).serve_forever()


if __name__ == '__main__':
    main()

"""OAuth Authorization Code + PKCE flow for Duo SSO browser-based auth."""

import base64
import hashlib
import http.server
import os
import secrets
import socket
import subprocess
import threading
import urllib.parse
import webbrowser

import httpx


_AUTH_RESULT: dict | None = None


class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    """HTTP handler that captures the OAuth callback with the auth code."""

    def do_GET(self):
        global _AUTH_RESULT
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if "code" in params:
            _AUTH_RESULT = {"code": params["code"][0]}
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body><h2>Authentication Successful</h2>"
                            b"<p>You can close this window and return to the terminal.</p>"
                            b"</body></html>")
        elif "error" in params:
            _AUTH_RESULT = {"error": params.get("error", ["unknown"])[0],
                           "description": params.get("error_description", [""])[0]}
            self.send_response(400)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            msg = params.get("error_description", ["Authentication failed"])[0]
            self.wfile.write(f"<html><body><h2>Error</h2><p>{msg}</p></body></html>".encode())
        else:
            self.send_response(400)
            self.end_headers()

    def log_message(self, format, *args):
        pass


def _generate_pkce() -> tuple[str, str]:
    """Generate PKCE code_verifier and code_challenge (S256)."""
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return verifier, challenge


async def get_access_token(
    client_id: str | None = None,
    authorize_url: str | None = None,
    token_url: str | None = None,
    redirect_port: int = 8085,
) -> str:
    """Acquire an OAuth access token via Authorization Code + PKCE.

    Opens a browser for the user to authenticate with Duo SSO, captures the
    callback on a local HTTP server, then exchanges the code for a token.
    Always forces a fresh login prompt so the user can choose which account.

    Environment variables (used as fallbacks):
      - OAUTH_AUTHORIZE_URL: Duo SSO authorization endpoint
      - OAUTH_TOKEN_URL: Duo SSO token endpoint
      - OAUTH_CLIENT_ID: Client ID from the MCP OIDC integration
      - OAUTH_SCOPE: requested scopes (default: "openid")
      - OAUTH_REDIRECT_PORT: local callback port (default: 8085)
    """
    global _AUTH_RESULT
    _AUTH_RESULT = None

    auth_url = authorize_url or os.environ["OAUTH_AUTHORIZE_URL"]
    tok_url = token_url or os.environ["OAUTH_TOKEN_URL"]
    cid = client_id or os.environ["OAUTH_CLIENT_ID"]
    scope = os.environ.get("OAUTH_SCOPE", "openid")
    port = int(os.environ.get("OAUTH_REDIRECT_PORT", str(redirect_port)))

    redirect_uri = f"http://localhost:{port}/callback"
    verifier, challenge = _generate_pkce()
    state = secrets.token_urlsafe(32)

    # Build authorization URL
    resource = os.environ.get("GATEWAY_URL", "")
    params = {
        "response_type": "code",
        "client_id": cid,
        "redirect_uri": redirect_uri,
        "scope": scope,
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    if resource:
        params["resource"] = resource
    params["prompt"] = "login"
    full_auth_url = f"{auth_url}?{urllib.parse.urlencode(params)}"

    # Kill any stale process on the callback port
    subprocess.run(f"lsof -ti :{port} | xargs kill 2>/dev/null", shell=True)

    # Start local callback server — serve until we get the auth code
    server = http.server.HTTPServer(("localhost", port), _CallbackHandler)
    server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.timeout = 120

    def serve_until_result():
        while _AUTH_RESULT is None:
            server.handle_request()

    server_thread = threading.Thread(target=serve_until_result, daemon=True)
    server_thread.start()

    # Open browser
    print(f"\n  Opening browser for Duo SSO authentication...")
    print(f"  If it doesn't open, visit:\n  {full_auth_url}\n")
    webbrowser.open(full_auth_url)

    # Wait for callback
    server_thread.join(timeout=120)
    server.server_close()

    if _AUTH_RESULT is None:
        raise TimeoutError("Authentication timed out — no callback received within 120s")

    if "error" in _AUTH_RESULT:
        raise ValueError(f"Auth error: {_AUTH_RESULT['error']} - {_AUTH_RESULT.get('description', '')}")

    auth_code = _AUTH_RESULT["code"]

    # Exchange code for token
    client_secret = os.environ.get("OAUTH_CLIENT_SECRET", "")
    token_data = {
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": redirect_uri,
        "client_id": cid,
        "code_verifier": verifier,
    }
    if client_secret:
        token_data["client_secret"] = client_secret
    if resource:
        token_data["resource"] = resource

    async with httpx.AsyncClient() as client:
        resp = await client.post(tok_url, data=token_data)
        resp.raise_for_status()
        result = resp.json()

    access_token = result.get("access_token")
    if not access_token:
        raise ValueError(f"No access_token in response: {result}")

    return access_token

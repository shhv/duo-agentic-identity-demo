# Cloudflare Tunnel Setup

The Cloudflare Tunnel provides a public HTTPS endpoint for agents to reach the agentgateway without exposing ports on your host machine.

## Prerequisites

- Cloudflare account (free tier works)
- A domain managed by Cloudflare (or use `*.cfargotunnel.com`)
- `cloudflared` CLI installed locally for initial setup

## Step 1: Create the Tunnel

```bash
cloudflared tunnel login
cloudflared tunnel create duo-agent-demo
```

Note the **Tunnel ID** from the output.

## Step 2: Configure DNS (optional)

If using a custom domain:

```bash
cloudflared tunnel route dns duo-agent-demo demo-agents.yourdomain.com
```

Otherwise, use the default `<tunnel-id>.cfargotunnel.com` URL.

## Step 3: Get the Tunnel Token

```bash
cloudflared tunnel token duo-agent-demo
```

Copy the token — this goes into `.env` as `CLOUDFLARE_TUNNEL_TOKEN`.

## Step 4: Configure Routing

The tunnel routes traffic to `http://agentgateway:3000` inside the Docker network. This is handled automatically by the `cloudflared` container in `docker-compose.yml`.

If you need to customize routing, create `~/.cloudflared/config.yml`:

```yaml
tunnel: <your-tunnel-id>
credentials-file: ~/.cloudflared/<tunnel-id>.json

ingress:
  - hostname: demo-agents.yourdomain.com
    service: http://agentgateway:3000
  - service: http_status:404
```

## Step 5: Verify

After `make up`:

```bash
# Check tunnel status in Cloudflare dashboard
# Or test directly:
curl https://your-tunnel-url/health
```

## Troubleshooting

- **Tunnel shows "inactive"**: Check `docker logs cloudflared` for auth errors
- **502 Bad Gateway**: The agentgateway container isn't ready yet — wait for health check
- **DNS not resolving**: Allow 1-2 minutes for DNS propagation after `tunnel route dns`

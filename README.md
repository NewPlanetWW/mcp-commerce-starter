# MCP Commerce Server Starter

Clone-and-deploy boilerplate for a commerce MCP server. Live on Vercel in five minutes. Reachable by Claude, ChatGPT, Gemini, Cursor, and every other MCP-compatible client.

**Full build guide (with the why behind every line):** [How to Build an MCP Server in 2026](https://30daypivot.com/agentmall_spoke_mcp)

---

## What you get

- **Product catalog Resource** — agents read the full catalog before acting
- **`search_products` Tool** — keyword + category + max-price filter
- **`initiate_checkout` Tool** — returns order summary + checkout URL
- **Optional API-key auth** — `X-API-Key` header, toggle with `REQUIRE_AUTH=true`
- **Health endpoint** at `/health`
- **Vercel-ready** — one command deploy, free Hobby tier

Stack: Python · FastMCP · FastAPI · Vercel

---

## Quick start (local)

```bash
git clone https://github.com/NewPlanetWW/mcp-commerce-starter
cd mcp-commerce-starter

python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python server.py
# Server running at http://localhost:8000
# MCP endpoint: http://localhost:8000/mcp
# Health check: http://localhost:8000/health
```

Test the health endpoint:

```bash
curl http://localhost:8000/health
# {"status":"ok","server":"Commerce MCP Server","version":"1.0.0"}
```

---

## Deploy to Vercel (free)

Requires Node 18+ for the Vercel CLI. No GitHub required — the CLI uploads directly.

```bash
npm i -g vercel
vercel login
vercel --prod
```

The CLI prints your production URL. Your MCP endpoint is at:

```
https://your-project.vercel.app/mcp
```

Set environment variables in the Vercel dashboard (Settings → Environment Variables):

| Variable | Default | Notes |
|---|---|---|
| `API_KEY` | `dev-secret-key` | Change before going live |
| `REQUIRE_AUTH` | `false` | Set `true` to enforce the key |

---

## Wire into Claude Desktop

**Option A — Local stdio** (fast iteration while building):

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` on macOS (see [full guide](https://30daypivot.com/agentmall_spoke_mcp#test-with-claude) for Windows/Linux paths):

```json
{
  "mcpServers": {
    "commerce-catalog": {
      "command": "uvicorn",
      "args": ["server:app", "--host", "127.0.0.1", "--port", "8001"],
      "env": {
        "REQUIRE_AUTH": "false"
      },
      "cwd": "/path/to/mcp-commerce-starter"
    }
  }
}
```

**Option B — Remote (after Vercel deploy)** using `mcp-remote`:

```json
{
  "mcpServers": {
    "commerce-catalog-remote": {
      "command": "npx",
      "args": [
        "-y", "mcp-remote@latest",
        "https://your-project.vercel.app/mcp",
        "--header", "Authorization: Bearer ${MCP_API_KEY}"
      ],
      "env": { "MCP_API_KEY": "your-secret-key" }
    }
  }
}
```

Fully quit and relaunch Claude Desktop. Ask: *"What products do you have under $100?"* — Claude calls `search_products` and responds with your catalog.

---

## Customize

### Replace the sample products

Edit the `PRODUCTS` list in `server.py`. Each product needs: `sku`, `name`, `price`, `description`, `availability`, `category`, `image_url`.

For real inventory, replace the list with a database call:

```python
# server.py — swap PRODUCTS for a live query
import psycopg2  # or SQLAlchemy, Supabase, etc.

def get_products():
    # your DB query here
    return [...]

PRODUCTS = get_products()
```

### Add Stripe checkout

Replace the stub in `initiate_checkout` with a real Stripe session:

```python
import stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

session = stripe.checkout.Session.create(
    line_items=[{"price": price_id, "quantity": quantity}],
    mode="payment",
    success_url="https://yourstore.com/success",
    cancel_url="https://yourstore.com/cancel",
)
return {"success": True, "checkout_url": session.url, ...}
```

---

## The 5 errors you'll hit (and how to fix them)

Covered in the full guide: [30daypivot.com/agentmall_spoke_mcp](https://30daypivot.com/agentmall_spoke_mcp#five-errors)

1. `MCP error -32600` — initialization order violation
2. `422 Unprocessable Entity` — Pydantic model vs plain args mismatch
3. `405 Method Not Allowed` — missing DELETE in CORS allowed methods
4. `stateless_http not set` — serverless Vercel requires `stateless_http=True`
5. `ModuleNotFoundError: mcp` — wrong package name (`mcp[cli]`, not `fastmcp`)

---

## Project structure

```
mcp-commerce-starter/
├── server.py          # FastMCP app — resource, tools, middleware, FastAPI mount
├── requirements.txt   # Pinned dependencies
├── vercel.json        # Vercel deployment config
├── mcp.json           # MCP server manifest
├── .env.example       # Environment variable template
└── README.md
```

---

## Go deeper

This starter is the code companion to the AgentMall spoke series on **30DayPivot**:

- [MCP Server Build Guide](https://30daypivot.com/agentmall_spoke_mcp) — the full walkthrough behind this repo
- [Agent-Readable Product Data](https://30daypivot.com/agentmall_spoke_product_data) — Schema.org markup so agents find your products without calling the server
- [FastAPI Commerce API](https://30daypivot.com/agentmall_spoke_api) — REST layer that sits alongside your MCP server
- [Free-to-Paid / Stripe Metered Billing](https://30daypivot.com/agentmall_spoke_free_paid) — monetize the server you just built
- [The AgentMall Roadmap](https://30daypivot.com/agentmall_roadmap) — full picks-and-shovels map of agentic commerce infrastructure

---

## License

MIT

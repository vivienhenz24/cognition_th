#!/bin/bash
# Devin + Power Apps Starter Kit - install Microsoft's canvas-apps plugin into Devin,
# register the Canvas Authoring MCP server for this project, and smoke-test it.
#
# The MCP server does NOT talk to Power Apps until you give it a live Studio
# coauthoring session. That step happens inside Devin (the connect tool),
# because it needs an interactive Microsoft sign-in.
set -e
GREEN='\033[0;32m'; RED='\033[0;31m'; BLUE='\033[0;34m'; NC='\033[0m'
export DOTNET_ROOT="${DOTNET_ROOT:-$HOME/.dotnet}"
export PATH="$DOTNET_ROOT:$DOTNET_ROOT/tools:$PATH"
SMOKE_WAIT="${SMOKE_WAIT:-8}"   # seconds to wait for the server's tools/list reply
cd "$(dirname "$0")"

die() { echo -e "${RED}✗${NC} $1"; exit 1; }

command -v devin >/dev/null 2>&1 || die "Devin CLI not found. Run ./setup.sh first."
command -v dnx   >/dev/null 2>&1 || die "dnx not found. Run ./setup.sh first (needs .NET 10 SDK)."
DNX_PATH="$(command -v dnx)"

echo "📦 Installing microsoft/power-platform-skills → canvas-apps into Devin..."
if devin plugins list 2>/dev/null | grep -q canvas-apps; then
  echo -e "${GREEN}✓${NC} already installed"
else
  devin plugins install -y "microsoft/power-platform-skills#plugins/canvas-apps"
fi

echo
echo "🔗 Registering the canvas-authoring MCP server for this project (.devin/mcp_config.json)..."
# The plugin's own server entry runs a bare "dnx", which fails unless dnx is on
# Devin's PATH. Register a project-scoped entry with absolute paths instead.
devin mcp remove canvas-authoring --scope project >/dev/null 2>&1 || true
devin mcp add canvas-authoring --scope project \
  -e "DOTNET_ROOT=$DOTNET_ROOT" \
  -e "PATH=$DOTNET_ROOT:$DOTNET_ROOT/tools:/usr/local/bin:/usr/bin:/bin" \
  -- "$DNX_PATH" Microsoft.PowerApps.CanvasAuthoring.McpServer --yes --prerelease >/dev/null
echo -e "${GREEN}✓${NC} registered: $DNX_PATH Microsoft.PowerApps.CanvasAuthoring.McpServer"

echo
echo "⬇️  Fetching the Canvas Authoring MCP server from NuGet (first run only, can take a minute)..."
# Start it once with stdin closed so the package downloads; it exits on EOF.
dnx Microsoft.PowerApps.CanvasAuthoring.McpServer --yes --prerelease </dev/null >/dev/null 2>&1 || true

echo "🧪 Smoke-testing the server..."
TOOLS=$( (echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"starter-kit","version":"0"}}}';
          echo '{"jsonrpc":"2.0","method":"notifications/initialized"}';
          echo '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'; sleep "$SMOKE_WAIT") \
        | dnx Microsoft.PowerApps.CanvasAuthoring.McpServer --yes --prerelease 2>/dev/null \
        | grep -oE '"name": ?"[a-z_]+"' | sed -E 's/.*"([a-z_]+)"$/\1/' | sort -u | tr '\n' ' ')
if [ -n "$TOOLS" ]; then
  echo -e "${GREEN}✓${NC} MCP server boots. Tools: $TOOLS"
else
  echo -e "${RED}✗${NC} MCP server did not respond within ${SMOKE_WAIT}s."
  echo "   Try: SMOKE_WAIT=30 ./connect.sh   (slow network) or check: dotnet --list-sdks (needs 10.x)"
  exit 1
fi

printf "%b" "$(cat <<MSG

${BLUE}Next, in the browser (one-time, needs your Microsoft work/school account):${NC}
  1. Go to https://make.powerapps.com (free dev plan: https://aka.ms/PowerAppsDevPlan)
  2. Create → Blank canvas app (tablet). Save it (e.g. "KYC Review Queue").
  3. Settings → Updates → turn on "Coauthoring". Keep this tab open.
  4. Copy the environment ID and app ID from the address bar
     (https://make.powerapps.com/e/<ENVIRONMENT_ID>/canvas/?action=edit&app-id=<APP_ID>)
     and put them in kyc-example/PROMPT.md under "Connection values".
     Set WORKDIR there to $(pwd)/kyc-example/generated

${BLUE}Then hand the session to Devin (start it from a shell where dotnet is on PATH):${NC}
  devin --prompt-file kyc-example/PROMPT.md
MSG
)\n"

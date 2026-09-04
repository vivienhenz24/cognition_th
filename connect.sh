#!/bin/bash
# Devin + Power Apps Starter Kit - install Microsoft's canvas-apps plugin into Devin
# and smoke-test that the Canvas Authoring MCP server boots.
#
# The MCP server does NOT talk to Power Apps until you give it a live Studio
# coauthoring session. That step happens inside Devin (/configure-canvas-mcp),
# because it needs an interactive Microsoft sign-in.
set -e
GREEN='\033[0;32m'; BLUE='\033[0;34m'; NC='\033[0m'
export DOTNET_ROOT="${DOTNET_ROOT:-$HOME/.dotnet}"
export PATH="$DOTNET_ROOT:$DOTNET_ROOT/tools:$PATH"

echo "📦 Installing microsoft/power-platform-skills → canvas-apps into Devin..."
if devin plugins list 2>/dev/null | grep -q canvas-apps; then
  echo -e "${GREEN}✓${NC} already installed"
else
  devin plugins install -y "microsoft/power-platform-skills#plugins/canvas-apps"
fi

echo
echo "🧪 Smoke-testing the Canvas Authoring MCP server (first run downloads it from NuGet)..."
TOOLS=$( (echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"starter-kit","version":"0"}}}';
          echo '{"jsonrpc":"2.0","method":"notifications/initialized"}';
          echo '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'; sleep 5) \
        | dnx Microsoft.PowerApps.CanvasAuthoring.McpServer --yes --prerelease 2>/dev/null \
        | grep -o '"name":"[a-z_]*"' | cut -d'"' -f4 | sort -u | tr '\n' ' ')
if [ -n "$TOOLS" ]; then
  echo -e "${GREEN}✓${NC} MCP server boots. Tools: $TOOLS"
else
  echo "✗ MCP server did not respond. Check: dotnet --list-sdks (needs 10.x)"; exit 1
fi

printf "%b" "$(cat <<MSG

${BLUE}Next, in the browser (one-time, needs your Microsoft work/school account):${NC}
  1. Go to https://make.powerapps.com (free dev plan: https://aka.ms/PowerAppsDevPlan)
  2. Create → Blank canvas app (tablet). Save it (e.g. "KYC Review Queue").
  3. Settings → Updates → turn on "Coauthoring". Keep this tab open.
  4. Copy the environment ID and app ID from the address bar
     (https://make.powerapps.com/e/<ENVIRONMENT_ID>/canvas/?action=edit&app-id=<APP_ID>)
     and put them in kyc-example/PROMPT.md under "Connection values".

${BLUE}Then hand the session to Devin:${NC}
  devin --prompt-file kyc-example/PROMPT.md
MSG
)\n"

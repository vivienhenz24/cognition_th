#!/bin/bash
# Devin + Power Apps Starter Kit - install Microsoft's canvas-apps plugin into Devin,
# register the Canvas Authoring MCP server for this project, smoke-test it, and
# fill in the connection values of kyc-example/PROMPT.md.
#
#   ./connect.sh                            install + smoke test
#   ./connect.sh <ENVIRONMENT_ID> <APP_ID>  also write the IDs into PROMPT.md
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
REPO="$(pwd)"
PROMPT="$REPO/kyc-example/PROMPT.md"

die() { printf "${RED}✗${NC} %s\n" "$1"; exit 1; }
ok()  { printf "${GREEN}✓${NC} %s\n" "$1"; }

command -v devin >/dev/null 2>&1 || die "Devin CLI not found. Run ./setup.sh first."
command -v dnx   >/dev/null 2>&1 || die "dnx not found. Run ./setup.sh first (installs the .NET 10 SDK)."
devin auth status 2>/dev/null | grep -q "Logged in" || die "Devin is not logged in. Run: devin auth login"
DNX_PATH="$(command -v dnx)"

echo "📦 Installing microsoft/power-platform-skills → canvas-apps into Devin..."
if devin plugins list 2>/dev/null | grep -q canvas-apps; then
  ok "already installed"
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
ok "registered: $DNX_PATH Microsoft.PowerApps.CanvasAuthoring.McpServer"

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
  ok "MCP server boots. Tools: $TOOLS"
else
  printf "${RED}✗${NC} MCP server did not respond within %ss.\n" "$SMOKE_WAIT"
  echo "   Try: SMOKE_WAIT=30 ./connect.sh   (slow network) or check: dotnet --list-sdks (needs 10.x)"
  exit 1
fi

echo
echo "📝 Updating $PROMPT ..."
# Portable in-place edit (BSD and GNU sed differ on -i): write to a temp file.
set_value() {  # set_value KEY VALUE  -> rewrites the "- KEY: `...`" line
  awk -v k="$1" -v v="$2" '$0 ~ "^- "k": " { print "- "k": `"v"`"; next } { print }' "$PROMPT" > "$PROMPT.tmp" && mv "$PROMPT.tmp" "$PROMPT"
}
set_value WORKDIR "$REPO/kyc-example/generated"
ok "WORKDIR set to $REPO/kyc-example/generated"
if [ -n "$1" ] && [ -n "$2" ]; then
  set_value ENVIRONMENT_ID "$1"; set_value APP_ID "$2"
  ok "ENVIRONMENT_ID and APP_ID written"
fi
NEED_IDS=0; grep -qE '<ENVIRONMENT_ID>|<APP_ID>' "$PROMPT" && NEED_IDS=1

printf "%b" "$(cat <<MSG

${BLUE}Next, in the browser (one-time, needs your Microsoft work/school account):${NC}
  1. Go to https://make.powerapps.com (free dev plan: https://aka.ms/PowerAppsDevPlan)
  2. Create → Blank canvas app (tablet). Save it (e.g. "KYC Review Queue").
  3. Settings → Updates → turn on "Coauthoring". Keep this tab open.
  4. Copy the environment ID and app ID from the address bar
     (https://make.powerapps.com/e/<ENVIRONMENT_ID>/canvas/?action=edit&app-id=<APP_ID>)
MSG
)\n"
if [ "$NEED_IDS" = 1 ]; then
  echo "     then run:  ./connect.sh <ENVIRONMENT_ID> <APP_ID>   (writes them into kyc-example/PROMPT.md)"
else
  echo "     (already written into kyc-example/PROMPT.md)"
fi
printf "%b" "
${BLUE}Then hand the session to Devin, from a new terminal (so dotnet is on PATH), in this folder:${NC}
  devin --prompt-file kyc-example/PROMPT.md
"

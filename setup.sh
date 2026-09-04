#!/bin/bash
# Devin + Power Apps Starter Kit - prerequisite checker
# Checks the real requirements for the Canvas Authoring MCP server.
# Ref: https://learn.microsoft.com/en-us/power-apps/maker/canvas-apps/create-canvas-external-tools

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✓${NC} $1"; }
warn() { echo -e "${YELLOW}⚠${NC} $1"; }
fail() { echo -e "${RED}✗${NC} $1"; FAILED=1; }

# .NET installed by dotnet-install.sh lands in ~/.dotnet
export DOTNET_ROOT="${DOTNET_ROOT:-$HOME/.dotnet}"
export PATH="$DOTNET_ROOT:$DOTNET_ROOT/tools:$PATH"

echo "🔍 Checking prerequisites..."

# 1. .NET 10 SDK (the MCP server is a .NET tool run through dnx)
if command -v dotnet >/dev/null 2>&1 && dotnet --list-sdks | grep -qE '^(1[0-9]|[2-9][0-9])\.'; then
  ok ".NET 10+ SDK ($(dotnet --list-sdks | grep -E '^(1[0-9]|[2-9][0-9])\.' | tail -1 | cut -d' ' -f1))"
else
  fail ".NET 10 SDK not found. Install without sudo:"
  echo "     curl -sSL https://dot.net/v1/dotnet-install.sh | bash -s -- --channel 10.0 --install-dir \$HOME/.dotnet"
fi

if command -v dnx >/dev/null 2>&1; then ok "dnx available"; else fail "dnx not on PATH (ships with .NET 10 SDK)"; fi

# 2. Devin CLI, logged in
if command -v devin >/dev/null 2>&1; then
  ok "Devin CLI ($(devin version 2>/dev/null | head -1))"
  if devin auth status 2>/dev/null | grep -q "Logged in"; then ok "Devin logged in"; else fail "Devin not logged in. Run: devin auth login"; fi
else
  fail "Devin CLI not found. Install from https://devin.ai/"
fi

# 3. Microsoft canvas-apps plugin installed in Devin
if devin plugins list 2>/dev/null | grep -q "canvas-apps"; then
  ok "canvas-apps plugin installed ($(devin plugins list 2>/dev/null | grep canvas-apps | sed 's/.*canvas-apps //'))"
else
  warn "canvas-apps plugin not installed. Run: ./connect.sh"
fi

# 4. MCP server registered
if devin mcp list 2>/dev/null | grep -q "canvas-authoring"; then
  ok "canvas-authoring MCP server registered in Devin"
else
  warn "canvas-authoring MCP not registered (installed automatically by the plugin)"
fi

echo
if [ -n "$FAILED" ]; then
  echo "Fix the ✗ items above, then re-run ./setup.sh"; exit 1
fi
echo "Next: ./connect.sh"

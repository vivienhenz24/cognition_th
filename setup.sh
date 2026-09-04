#!/bin/bash
# Devin + Power Apps Starter Kit - prerequisite checker
# Checks the real requirements for the Canvas Authoring MCP server.
# Ref: https://learn.microsoft.com/en-us/power-apps/maker/canvas-apps/create-canvas-external-tools

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; NC='\033[0m'
ok()   { echo -e "${GREEN}✓${NC} $1"; }
warn() { echo -e "${YELLOW}⚠${NC} $1"; }
fail() { echo -e "${RED}✗${NC} $1"; FAILED=1; }

# Remember whether dotnet is reachable from a plain shell BEFORE we patch PATH.
# The canvas-apps plugin runs a "dotnet run" hook inside Devin, which only sees
# the PATH of the shell that launched Devin.
DOTNET_ON_PATH=0
command -v dotnet >/dev/null 2>&1 && DOTNET_ON_PATH=1

# .NET installed by dotnet-install.sh lands in ~/.dotnet
export DOTNET_ROOT="${DOTNET_ROOT:-$HOME/.dotnet}"
export PATH="$DOTNET_ROOT:$DOTNET_ROOT/tools:$PATH"

echo "🔍 Checking prerequisites..."

# 1. .NET 10 SDK (the MCP server is a .NET tool run through dnx)
if command -v dotnet >/dev/null 2>&1 && dotnet --list-sdks 2>/dev/null | grep -qE '^(1[0-9]|[2-9][0-9])\.'; then
  ok ".NET 10+ SDK ($(dotnet --list-sdks | grep -E '^(1[0-9]|[2-9][0-9])\.' | tail -1 | cut -d' ' -f1))"
  if [ "$DOTNET_ON_PATH" = 0 ]; then
    warn "dotnet is installed but not on your shell PATH. Devin's plugin hook needs it. Add to ~/.zshrc or ~/.bashrc:"
    echo "     export DOTNET_ROOT=\"$DOTNET_ROOT\"; export PATH=\"\$DOTNET_ROOT:\$DOTNET_ROOT/tools:\$PATH\""
  fi
else
  fail ".NET 10 SDK not found. Install without sudo:"
  echo "     curl -sSL https://dot.net/v1/dotnet-install.sh | bash -s -- --channel 10.0 --install-dir \$HOME/.dotnet"
fi

if command -v dnx >/dev/null 2>&1; then ok "dnx available"; else fail "dnx not on PATH (ships with .NET 10 SDK)"; fi

# 2. Devin CLI, logged in
if command -v devin >/dev/null 2>&1; then
  ok "Devin CLI ($(devin version 2>/dev/null | head -1))"
  if devin auth status 2>/dev/null | grep -q "Logged in"; then ok "Devin logged in"; else fail "Devin not logged in. Run: devin auth login"; fi

  # 3. Microsoft canvas-apps plugin installed in Devin
  if devin plugins list 2>/dev/null | grep -q "canvas-apps"; then
    ok "canvas-apps plugin installed ($(devin plugins list 2>/dev/null | grep canvas-apps | sed 's/.*canvas-apps //'))"
  else
    warn "canvas-apps plugin not installed. Run: ./connect.sh"
  fi

  # 4. MCP server registered for this project with a working dnx path.
  #    Note: "devin mcp list" does not show project-scoped servers; use "get".
  MCP_CMD=$(devin mcp get canvas-authoring 2>/dev/null | grep -E '^\s*Command:' | awk '{print $2}')
  if [ -z "$MCP_CMD" ]; then
    warn "canvas-authoring MCP server not registered for this project. Run: ./connect.sh"
  elif [ -x "$MCP_CMD" ] || command -v "$MCP_CMD" >/dev/null 2>&1; then
    ok "canvas-authoring MCP server registered ($MCP_CMD)"
  else
    fail "canvas-authoring MCP points at a missing binary: $MCP_CMD. Run: ./connect.sh"
  fi
else
  fail "Devin CLI not found. Install from https://devin.ai/"
fi

echo
if [ -n "$FAILED" ]; then
  echo "Fix the ✗ items above, then re-run ./setup.sh"; exit 1
fi
echo "Next: ./connect.sh"

#!/bin/bash
# Devin + Power Apps Starter Kit - prerequisite checker and installer.
#
#   ./setup.sh          check everything, offer to fix what is missing
#   ./setup.sh --yes    same, but apply every fix without asking
#   ./setup.sh --runtime-only --yes
#                       install and verify only the cloud MCP runtime
#
# Works on macOS and Linux (Windows: run inside WSL).
# Ref: https://learn.microsoft.com/en-us/power-apps/maker/canvas-apps/create-canvas-external-tools

GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; NC='\033[0m'
ok()   { printf "${GREEN}✓${NC} %s\n" "$1"; }
warn() { printf "${YELLOW}⚠${NC} %s\n" "$1"; }
fail() { printf "${RED}✗${NC} %s\n" "$1"; FAILED=1; }
AUTO=0
RUNTIME_ONLY=0
for arg in "$@"; do
  case "$arg" in
    --yes|-y) AUTO=1 ;;
    --runtime-only) RUNTIME_ONLY=1 ;;
    *) fail "Unknown option: $arg"; exit 1 ;;
  esac
done
ask() {  # ask "question" -> returns 0 for yes
  [ "$AUTO" = 1 ] && return 0
  [ -t 0 ] || return 1
  printf "  %s [y/N] " "$1"; read -r a; [ "$a" = "y" ] || [ "$a" = "Y" ]
}

case "$(uname -s)" in
  Darwin|Linux) ;;
  *) fail "Unsupported OS: $(uname -s). On Windows, run this inside WSL."; exit 1 ;;
esac
command -v curl >/dev/null 2>&1 || { fail "curl is required. Install it with your package manager and re-run."; exit 1; }

# Was dotnet reachable from a plain shell BEFORE we patch PATH? Devin's plugin
# hook runs "dotnet run" and only sees the PATH of the shell that launched Devin.
DOTNET_ON_PATH=0; command -v dotnet >/dev/null 2>&1 && DOTNET_ON_PATH=1

export DOTNET_ROOT="${DOTNET_ROOT:-$HOME/.dotnet}"
export PATH="$DOTNET_ROOT:$DOTNET_ROOT/tools:$PATH"
PATH_LINE="export DOTNET_ROOT=\"\$HOME/.dotnet\"; export PATH=\"\$DOTNET_ROOT:\$DOTNET_ROOT/tools:\$PATH\""

has_dotnet10() { command -v dotnet >/dev/null 2>&1 && dotnet --list-sdks 2>/dev/null | grep -qE '^(1[0-9]|[2-9][0-9])\.'; }

echo "🔍 Checking prerequisites..."

# 1. .NET 10 SDK (the MCP server is a .NET tool run through dnx)
if ! has_dotnet10; then
  warn ".NET 10 SDK not found."
  if [ "$(uname -s)" = Linux ] && ! ldconfig -p 2>/dev/null | grep -q libicu; then
    warn ".NET on Linux needs libicu. Install it first, e.g.: sudo apt install libicu-dev   (or: sudo dnf install libicu)"
  fi
  if ask "Install .NET 10 SDK into $DOTNET_ROOT now (no sudo needed)?"; then
    curl -sSL https://dot.net/v1/dotnet-install.sh | bash -s -- --channel 10.0 --install-dir "$DOTNET_ROOT" \
      && hash -r
  else
    echo "     Manual install: curl -sSL https://dot.net/v1/dotnet-install.sh | bash -s -- --channel 10.0 --install-dir \$HOME/.dotnet"
  fi
fi
if has_dotnet10; then
  ok ".NET 10+ SDK ($(dotnet --list-sdks | grep -E '^(1[0-9]|[2-9][0-9])\.' | tail -1 | cut -d' ' -f1))"
else
  fail ".NET 10 SDK still missing."
fi
if command -v dnx >/dev/null 2>&1; then ok "dnx available"; else fail "dnx not found (ships with the .NET 10 SDK; check $DOTNET_ROOT/dnx exists)"; fi

if [ "$RUNTIME_ONLY" = 1 ]; then
  if [ -z "$FAILED" ]; then
    echo "⬇️  Fetching the Canvas Authoring MCP server from NuGet..."
    if dnx Microsoft.PowerApps.CanvasAuthoring.McpServer --yes --prerelease </dev/null >/dev/null 2>&1; then
      ok "Canvas Authoring MCP server available"
    else
      fail "Canvas Authoring MCP server could not be fetched or started."
    fi
  fi
  echo
  if [ -n "$FAILED" ]; then
    echo "Fix the ✗ items above, then re-run ./setup.sh --runtime-only --yes"; exit 1
  fi
  echo "Cloud MCP runtime ready."; exit 0
fi

# 2. dotnet on the login-shell PATH, so Devin's plugin hook can find it
if [ "$DOTNET_ON_PATH" = 1 ]; then
  ok "dotnet is on your shell PATH"
else
  case "$(basename "${SHELL:-bash}")" in zsh) PROFILE="$HOME/.zshrc" ;; *) PROFILE="$HOME/.bashrc" ;; esac
  if grep -qs 'DOTNET_ROOT' "$PROFILE"; then
    warn "dotnet is configured in $PROFILE but not active in this shell. Open a new terminal before running Devin."
  else
    warn "dotnet is not on your shell PATH. Devin's plugin hook needs it."
    if ask "Add it to $PROFILE now?"; then
      printf '\n# .NET SDK (added by devin-powerapps setup.sh)\n%s\n' "$PATH_LINE" >> "$PROFILE"
      ok "Added to $PROFILE. Open a new terminal before running Devin."
    else
      echo "     Add this line to $PROFILE yourself:"; echo "     $PATH_LINE"
    fi
  fi
fi

# 3. Devin CLI, logged in
if command -v devin >/dev/null 2>&1; then
  ok "Devin CLI ($(devin version 2>/dev/null | head -1))"
  if devin auth status 2>/dev/null | grep -q "Logged in"; then
    ok "Devin logged in"
  elif ask "Devin is not logged in. Log in now (opens a browser)?"; then
    devin auth login && ok "Devin logged in" || fail "Devin login failed. Run: devin auth login"
  else
    fail "Devin not logged in. Run: devin auth login"
  fi

  # 4. Microsoft canvas-apps plugin installed in Devin
  if devin plugins list 2>/dev/null | grep -q "canvas-apps"; then
    ok "canvas-apps plugin installed ($(devin plugins list 2>/dev/null | grep canvas-apps | sed 's/.*canvas-apps //'))"
  else
    warn "canvas-apps plugin not installed. ./connect.sh installs it."
  fi

  # 5. MCP server registered for this project with a working dnx path.
  #    Note: "devin mcp list" hides project-scoped servers; use "get".
  MCP_CMD=$(cd "$(dirname "$0")" && devin mcp get canvas-authoring 2>/dev/null | grep -E '^[[:space:]]*Command:' | awk '{print $2}')
  if [ -z "$MCP_CMD" ]; then
    warn "canvas-authoring MCP server not registered for this project. ./connect.sh does it."
  elif [ -x "$MCP_CMD" ] || command -v "$MCP_CMD" >/dev/null 2>&1; then
    ok "canvas-authoring MCP server registered ($MCP_CMD)"
  else
    warn "canvas-authoring MCP points at a missing binary ($MCP_CMD). ./connect.sh will fix it."
  fi
else
  fail "Devin CLI not found. Install it from https://devin.ai/ then run: devin auth login"
fi

echo
if [ -n "$FAILED" ]; then
  echo "Fix the ✗ items above, then re-run ./setup.sh"; exit 1
fi
echo "Next: ./connect.sh"

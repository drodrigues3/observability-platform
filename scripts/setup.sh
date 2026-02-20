#!/usr/bin/env bash
# ============================================================================
# Observability Platform — Local Environment Setup
# ============================================================================
# Checks and installs all dependencies required by the Makefile.
# Safe to run multiple times (idempotent).
#
# Supported: Ubuntu/Debian, WSL2, macOS (Homebrew)
# Usage:  ./scripts/setup.sh
# ============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

ok()   { echo -e "  ${GREEN}✔${NC} $1"; }
warn() { echo -e "  ${YELLOW}⚠${NC} $1"; }
fail() { echo -e "  ${RED}✖${NC} $1"; }

need_cmd() {
    command -v "$1" &>/dev/null
}

# Detect OS / package manager
detect_os() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        OS_ID="${ID:-linux}"
    elif [[ "$(uname)" == "Darwin" ]]; then
        OS_ID="macos"
    else
        OS_ID="unknown"
    fi
}

INSTALL_COUNT=0

# ---------------------------------------------------------------------------
# Python 3.11+
# ---------------------------------------------------------------------------
setup_python() {
    echo ""
    echo "--- Python 3.11+ ---"

    if need_cmd python3; then
        PY_VER=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        PY_MAJOR=$(echo "$PY_VER" | cut -d. -f1)
        PY_MINOR=$(echo "$PY_VER" | cut -d. -f2)

        if [[ "$PY_MAJOR" -ge 3 && "$PY_MINOR" -ge 11 ]]; then
            ok "Python $PY_VER found"
            return
        else
            warn "Python $PY_VER found, but 3.11+ is required"
        fi
    fi

    echo "  Installing Python 3.11 ..."
    case "$OS_ID" in
        ubuntu|debian)
            sudo apt-get update -qq
            sudo apt-get install -y -qq software-properties-common
            sudo add-apt-repository -y ppa:deadsnakes/deadsnakes
            sudo apt-get update -qq
            sudo apt-get install -y -qq python3.11 python3.11-venv python3.11-dev
            ;;
        macos)
            brew install python@3.11
            ;;
        *)
            fail "Cannot auto-install Python on $OS_ID. Install Python 3.11+ manually."
            return 1
            ;;
    esac
    ok "Python 3.11 installed"
    ((INSTALL_COUNT++))
}

# ---------------------------------------------------------------------------
# pip (needed to install Poetry)
# ---------------------------------------------------------------------------
setup_pip() {
    echo ""
    echo "--- pip ---"

    if python3 -m pip --version &>/dev/null; then
        ok "pip found"
        return
    fi

    echo "  Installing pip ..."
    case "$OS_ID" in
        ubuntu|debian)
            sudo apt-get install -y -qq python3-pip
            ;;
        macos)
            python3 -m ensurepip --upgrade
            ;;
        *)
            curl -sS https://bootstrap.pypa.io/get-pip.py | python3
            ;;
    esac
    ok "pip installed"
    ((INSTALL_COUNT++))
}

# ---------------------------------------------------------------------------
# Poetry
# ---------------------------------------------------------------------------
setup_poetry() {
    echo ""
    echo "--- Poetry ---"

    if need_cmd poetry; then
        ok "Poetry $(poetry --version 2>/dev/null | awk '{print $NF}') found"
        return
    fi

    echo "  Installing Poetry via official installer ..."
    curl -sSL https://install.python-poetry.org | python3 -

    # Ensure it's on PATH for the rest of this script
    export PATH="$HOME/.local/bin:$PATH"

    if need_cmd poetry; then
        ok "Poetry installed"
        ((INSTALL_COUNT++))
    else
        fail "Poetry installed but not on PATH. Add \$HOME/.local/bin to your PATH."
        return 1
    fi
}

# ---------------------------------------------------------------------------
# Docker
# ---------------------------------------------------------------------------
setup_docker() {
    echo ""
    echo "--- Docker ---"

    if need_cmd docker; then
        ok "Docker $(docker --version | awk '{print $3}' | tr -d ',') found"
        return
    fi

    echo "  Installing Docker Engine ..."
    case "$OS_ID" in
        ubuntu|debian)
            # Official Docker install script
            curl -fsSL https://get.docker.com | sudo sh
            sudo usermod -aG docker "$USER"
            warn "Added $USER to docker group. You may need to log out and back in."
            ;;
        macos)
            brew install --cask docker
            warn "Open Docker Desktop to finish setup."
            ;;
        *)
            fail "Cannot auto-install Docker on $OS_ID. Install manually: https://docs.docker.com/engine/install/"
            return 1
            ;;
    esac
    ok "Docker installed"
    ((INSTALL_COUNT++))
}

# ---------------------------------------------------------------------------
# kubectl
# ---------------------------------------------------------------------------
setup_kubectl() {
    echo ""
    echo "--- kubectl ---"

    if need_cmd kubectl; then
        ok "kubectl $(kubectl version --client -o yaml 2>/dev/null | grep gitVersion | awk '{print $2}') found"
        return
    fi

    echo "  Installing kubectl ..."
    case "$OS_ID" in
        ubuntu|debian)
            curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.31/deb/Release.key | sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg 2>/dev/null
            echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.31/deb/ /' | sudo tee /etc/apt/sources.list.d/kubernetes.list >/dev/null
            sudo apt-get update -qq
            sudo apt-get install -y -qq kubectl
            ;;
        macos)
            brew install kubectl
            ;;
        *)
            fail "Cannot auto-install kubectl on $OS_ID. Install manually."
            return 1
            ;;
    esac
    ok "kubectl installed"
    ((INSTALL_COUNT++))
}

# ---------------------------------------------------------------------------
# Helm
# ---------------------------------------------------------------------------
setup_helm() {
    echo ""
    echo "--- Helm ---"

    if need_cmd helm; then
        ok "Helm $(helm version --short 2>/dev/null) found"
        return
    fi

    echo "  Installing Helm ..."
    curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
    ok "Helm installed"
    ((INSTALL_COUNT++))
}

# ---------------------------------------------------------------------------
# kind
# ---------------------------------------------------------------------------
setup_kind() {
    echo ""
    echo "--- kind ---"

    if need_cmd kind; then
        ok "kind $(kind version 2>/dev/null) found"
        return
    fi

    echo "  Installing kind ..."
    case "$OS_ID" in
        ubuntu|debian)
            ARCH=$(dpkg --print-architecture)
            curl -fsSLo ./kind "https://kind.sigs.k8s.io/dl/v0.24.0/kind-linux-${ARCH}"
            chmod +x ./kind
            sudo mv ./kind /usr/local/bin/kind
            ;;
        macos)
            brew install kind
            ;;
        *)
            fail "Cannot auto-install kind on $OS_ID. Install manually: https://kind.sigs.k8s.io/"
            return 1
            ;;
    esac
    ok "kind installed"
    ((INSTALL_COUNT++))
}

# ---------------------------------------------------------------------------
# make (usually present, but just in case)
# ---------------------------------------------------------------------------
setup_make() {
    echo ""
    echo "--- make ---"

    if need_cmd make; then
        ok "make found"
        return
    fi

    echo "  Installing make ..."
    case "$OS_ID" in
        ubuntu|debian)
            sudo apt-get install -y -qq build-essential
            ;;
        macos)
            xcode-select --install 2>/dev/null || true
            ;;
    esac
    ok "make installed"
    ((INSTALL_COUNT++))
}

# ---------------------------------------------------------------------------
# Python app dependencies (poetry install per app)
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
APPS=(workload-simulator stream-processor metrics-bridge)

setup_app_deps() {
    echo ""
    echo "--- Python app dependencies ---"

    for app in "${APPS[@]}"; do
        APP_DIR="$PROJECT_ROOT/apps/$app"
        if [[ ! -f "$APP_DIR/pyproject.toml" ]]; then
            warn "No pyproject.toml in $app — skipping"
            continue
        fi

        echo "  Installing $app ..."
        (cd "$APP_DIR" && poetry install --no-interaction --quiet)
        ok "$app dependencies installed"
    done
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
main() {
    echo "============================================================================"
    echo " Observability Platform — Environment Setup"
    echo "============================================================================"

    detect_os
    echo "Detected OS: $OS_ID"

    setup_python
    setup_pip
    setup_poetry
    setup_docker
    setup_kubectl
    setup_helm
    setup_kind
    setup_make
    setup_app_deps

    echo ""
    echo "============================================================================"
    if [[ $INSTALL_COUNT -eq 0 ]]; then
        echo -e " ${GREEN}All tools already installed.${NC}"
    else
        echo -e " ${GREEN}Installed $INSTALL_COUNT system tool(s).${NC}"
    fi
    echo -e " ${GREEN}All Python app dependencies are up to date.${NC}"
    echo ""
    echo " Next steps:"
    echo "   make test       # Run unit tests"
    echo "   make run        # Full cluster setup + deploy"
    echo "============================================================================"
}

main "$@"

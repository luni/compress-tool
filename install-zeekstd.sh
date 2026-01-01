#!/usr/bin/env bash
set -euo pipefail

# You can override this when running:
#   ZEEKSTD_TAG=v0.4.3-cli ./install-zeekstd.sh
ZEEKSTD_TAG="${ZEEKSTD_TAG:-v0.4.3-cli}"
REPO_URL="https://github.com/rorosen/zeekstd"
MSRV="1.85.1"

need_cmd() { command -v "$1" >/dev/null 2>&1; }

echo "[1/4] Installing system build dependencies..."
sudo apt-get update
sudo apt-get install -y --no-install-recommends \
  ca-certificates curl git build-essential pkg-config

echo "[2/4] Ensuring Rust toolchain >= ${MSRV}..."
install_rustup() {
  echo "  -> Installing rustup (user-local)..."
  curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
  # shellcheck disable=SC1090
  source "${HOME}/.cargo/env"
}

get_rust_version() {
  rustc --version | awk '{print $2}'
}

version_ge() {
  # Debian-native version compare
  dpkg --compare-versions "$1" ge "$2"
}

if ! need_cmd rustc || ! need_cmd cargo; then
  install_rustup
else
  RUSTV="$(get_rust_version || true)"
  if [[ -z "${RUSTV}" ]] || ! version_ge "${RUSTV}" "${MSRV}"; then
    echo "  -> rustc ${RUSTV:-<unknown>} is older than ${MSRV}; updating via rustup..."
    if ! need_cmd rustup; then
      install_rustup
    else
      # shellcheck disable=SC1090
      source "${HOME}/.cargo/env" || true
    fi
    rustup toolchain install stable
    rustup default stable
  fi
fi

# Ensure cargo is on PATH in this shell
# shellcheck disable=SC1090
source "${HOME}/.cargo/env" 2>/dev/null || true

echo "[3/4] Installing zeekstd CLI from ${REPO_URL} (tag: ${ZEEKSTD_TAG})..."
# The CLI crate within the workspace is named "zeekstd_cli"
cargo install --locked --git "${REPO_URL}" --tag "${ZEEKSTD_TAG}" zeekstd_cli

echo "[4/4] Done."
echo "Binary should be at: ${HOME}/.cargo/bin/zeekstd"
echo "Test: ${HOME}/.cargo/bin/zeekstd --help"

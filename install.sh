#!/bin/sh
set -eu

REPO="benhalladay08/flop7"
BINARY_NAME="flop7"

# --- Detect platform --------------------------------------------------------

OS="$(uname -s)"
ARCH="$(uname -m)"

case "$OS" in
  Darwin) PLATFORM="macos" ;;
  Linux)  PLATFORM="linux" ;;
  *)      echo "Error: unsupported OS: $OS" >&2; exit 1 ;;
esac

case "$ARCH" in
  arm64|aarch64) ARCH_LABEL="arm64" ;;
  x86_64)        ARCH_LABEL="x86_64" ;;
  *)             echo "Error: unsupported architecture: $ARCH" >&2; exit 1 ;;
esac

ASSET="${BINARY_NAME}-${PLATFORM}-${ARCH_LABEL}.tar.gz"

# --- Fetch latest release tag ------------------------------------------------

TAG=$(curl -fsSL "https://api.github.com/repos/${REPO}/releases/latest" \
  | grep '"tag_name"' | head -1 | cut -d'"' -f4)

if [ -z "$TAG" ]; then
  echo "Error: could not determine latest release tag." >&2
  exit 1
fi

echo "Installing ${BINARY_NAME} ${TAG} (${PLATFORM}/${ARCH_LABEL})..."

# --- Download and extract ----------------------------------------------------

DOWNLOAD_URL="https://github.com/${REPO}/releases/download/${TAG}/${ASSET}"
TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

curl -fsSL "$DOWNLOAD_URL" -o "${TMP_DIR}/${ASSET}"
tar -xzf "${TMP_DIR}/${ASSET}" -C "$TMP_DIR"

# --- Install -----------------------------------------------------------------

if [ -w /usr/local/bin ]; then
  INSTALL_DIR="/usr/local/bin"
  install -m 755 "${TMP_DIR}/${BINARY_NAME}" "${INSTALL_DIR}/${BINARY_NAME}"
elif command -v sudo >/dev/null 2>&1; then
  INSTALL_DIR="/usr/local/bin"
  echo "Installing to ${INSTALL_DIR} (requires sudo)..."
  sudo install -m 755 "${TMP_DIR}/${BINARY_NAME}" "${INSTALL_DIR}/${BINARY_NAME}"
else
  INSTALL_DIR="${HOME}/.local/bin"
  mkdir -p "$INSTALL_DIR"
  install -m 755 "${TMP_DIR}/${BINARY_NAME}" "${INSTALL_DIR}/${BINARY_NAME}"
  case ":$PATH:" in
    *":${INSTALL_DIR}:"*) ;;
    *) echo "Warning: ${INSTALL_DIR} is not in your PATH. Add it with:"
       echo "  export PATH=\"${INSTALL_DIR}:\$PATH\""
       ;;
  esac
fi

echo "Installed ${BINARY_NAME} to ${INSTALL_DIR}/${BINARY_NAME}"

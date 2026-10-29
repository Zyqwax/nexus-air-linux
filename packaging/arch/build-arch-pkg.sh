#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
DIST_DIR="${ROOT_DIR}/dist"
ARCH_BUILD_DIR="${ROOT_DIR}/build/arch"

echo "==> Preparing Arch Linux / CachyOS package build..."
mkdir -p "${DIST_DIR}" "${ARCH_BUILD_DIR}"

VERSION="1.0.0"
TARBALL="nexus-air-${VERSION}.tar.gz"

# Create archive if not exists
if [ ! -f "${DIST_DIR}/${TARBALL}" ]; then
  echo "==> Creating source tarball ${TARBALL}..."
  (cd "${ROOT_DIR}" && git archive --format=tar.gz --prefix="nexus-air-${VERSION}/" HEAD > "${DIST_DIR}/${TARBALL}")
fi

cp "${DIST_DIR}/${TARBALL}" "${ARCH_BUILD_DIR}/"
cp "${SCRIPT_DIR}/PKGBUILD" "${ARCH_BUILD_DIR}/"

cd "${ARCH_BUILD_DIR}"
echo "==> Running makepkg..."
makepkg -f --nodeps

echo "==> Moving Arch package to ${DIST_DIR}..."
cp *.pkg.tar.zst "${DIST_DIR}/"
echo "==> Successfully created Arch Linux package:"
ls -lh "${DIST_DIR}"/*.pkg.tar.zst

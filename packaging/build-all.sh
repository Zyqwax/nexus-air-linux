#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

echo "============================================="
echo "  Nexus Air V1 — Universal Multi-Distro Build"
echo "============================================="

# 1. Clean dist
mkdir -p "${ROOT_DIR}/dist"

# 2. Build Python sdist and wheel
echo "==> [1/4] Building Python sdist & wheel..."
cd "${ROOT_DIR}"
if python3 -c "import build" >/dev/null 2>&1; then
    python3 -m build --sdist --wheel --outdir "${ROOT_DIR}/dist"
else
    echo "==> 'build' module not found, building standard source tarball via tar..."
    TAR_NAME="nexus-air-1.0.0.tar.gz"
    tar --exclude-vcs --exclude='./build' --exclude='./dist' -czf "${ROOT_DIR}/dist/${TAR_NAME}" .
fi

# 3. Build Debian / Ubuntu package (.deb)
echo "==> [2/4] Building Debian/Ubuntu (.deb) package..."
bash "${ROOT_DIR}/packaging/debian/build-deb.sh"

# 4. Build Portable Standalone Linux ZIP bundle
echo "==> [3/4] Building Portable Linux standalone ZIP archive..."
bash "${ROOT_DIR}/packaging/portable/build-portable-zip.sh"

# 5. Build AppImage (or AppDir)
echo "==> [4/5] Building AppImage / AppDir..."
bash "${ROOT_DIR}/packaging/appimage/build-appimage.sh"

# 6. Build Arch Linux / CachyOS package (.pkg.tar.zst)
if command -v makepkg >/dev/null 2>&1; then
    echo "==> [5/5] Building Arch Linux / CachyOS (.pkg.tar.zst) package..."
    bash "${ROOT_DIR}/packaging/arch/build-arch-pkg.sh"
else
    echo "==> Skipping Arch package (makepkg not found)."
fi

echo ""
echo "============================================="
echo "  Build Completed! Artifacts in dist/:"
echo "============================================="
ls -lh "${ROOT_DIR}/dist"

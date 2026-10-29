#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
PKG_NAME="nexus-air"
VERSION="1.0.0"
DEB_DIR="${ROOT_DIR}/build/deb-pkg"
OUTPUT_DIR="${ROOT_DIR}/dist"

echo "==> Preparing Debian/Ubuntu .deb package structure..."
rm -rf "${DEB_DIR}"
mkdir -p "${DEB_DIR}/DEBIAN"
mkdir -p "${DEB_DIR}/usr/bin"
mkdir -p "${DEB_DIR}/usr/lib/python3/dist-packages"
mkdir -p "${DEB_DIR}/usr/share/applications"
mkdir -p "${DEB_DIR}/usr/share/icons/hicolor/scalable/apps"
mkdir -p "${DEB_DIR}/usr/lib/udev/rules.d"
mkdir -p "${DEB_DIR}/usr/share/licenses/${PKG_NAME}"
mkdir -p "${OUTPUT_DIR}"

# Copy control file
cp "${ROOT_DIR}/packaging/debian/control" "${DEB_DIR}/DEBIAN/control"

# Add postinst script for udev reloading
cat > "${DEB_DIR}/DEBIAN/postinst" << 'EOF'
#!/bin/sh
set -e
if [ "$1" = "configure" ]; then
    if command -v udevadm >/dev/null 2>&1; then
        udevadm control --reload-rules || true
        udevadm trigger || true
    fi
fi
exit 0
EOF
chmod 755 "${DEB_DIR}/DEBIAN/postinst"

# Copy python sources
cp -r "${ROOT_DIR}/src/nexus_air" "${DEB_DIR}/usr/lib/python3/dist-packages/"

# Create /usr/bin scripts
cat > "${DEB_DIR}/usr/bin/nexus-air" << 'EOF'
#!/usr/bin/env python3
import sys
from nexus_air.cli import main
if __name__ == '__main__':
    main()
EOF
chmod 755 "${DEB_DIR}/usr/bin/nexus-air"

cat > "${DEB_DIR}/usr/bin/nexus-air-gui" << 'EOF'
#!/usr/bin/env python3
import sys
from nexus_air.gui import main
if __name__ == '__main__':
    main()
EOF
chmod 755 "${DEB_DIR}/usr/bin/nexus-air-gui"

# Copy desktop, icon, udev, and license
cp "${ROOT_DIR}/data/org.cachyos.NexusAirV1.desktop" "${DEB_DIR}/usr/share/applications/org.cachyos.NexusAirV1.desktop"
cp "${ROOT_DIR}/data/icons/nexus-air.svg" "${DEB_DIR}/usr/share/icons/hicolor/scalable/apps/nexus-air.svg"
cp "${ROOT_DIR}/data/99-nexus-air.rules" "${DEB_DIR}/usr/lib/udev/rules.d/99-nexus-air.rules"
cp "${ROOT_DIR}/LICENSE" "${DEB_DIR}/usr/share/licenses/${PKG_NAME}/LICENSE"

TARGET_DEB="${OUTPUT_DIR}/${PKG_NAME}_${VERSION}-1_all.deb"

if command -v dpkg-deb >/dev/null 2>&1; then
    echo "==> Building .deb package with dpkg-deb..."
    dpkg-deb --build --root-owner-group "${DEB_DIR}" "${TARGET_DEB}"
    echo "==> Created: ${TARGET_DEB}"
else
    # Build standard ar-archive debian package without dpkg-deb
    echo "==> dpkg-deb not found. Creating standard Debian .deb using tar and ar..."
    TMP_DIR="$(mktemp -d)"
    echo "2.0" > "${TMP_DIR}/debian-binary"
    (cd "${DEB_DIR}/DEBIAN" && tar --owner=0 --group=0 -czf "${TMP_DIR}/control.tar.gz" .)
    (cd "${DEB_DIR}" && tar --exclude='./DEBIAN' --owner=0 --group=0 -czf "${TMP_DIR}/data.tar.gz" .)
    ar rcs "${TARGET_DEB}" "${TMP_DIR}/debian-binary" "${TMP_DIR}/control.tar.gz" "${TMP_DIR}/data.tar.gz"
    rm -rf "${TMP_DIR}"
    echo "==> Successfully created: ${TARGET_DEB}"
fi

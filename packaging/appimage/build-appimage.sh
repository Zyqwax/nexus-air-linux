#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
APPDIR="${ROOT_DIR}/build/AppDir"
OUTPUT_DIR="${ROOT_DIR}/dist"

echo "==> Preparing AppDir at ${APPDIR}..."
rm -rf "${APPDIR}"
mkdir -p "${APPDIR}/usr/bin"
mkdir -p "${APPDIR}/usr/lib/python3/site-packages"
mkdir -p "${APPDIR}/usr/share/applications"
mkdir -p "${APPDIR}/usr/share/icons/hicolor/scalable/apps"
mkdir -p "${APPDIR}/usr/lib/udev/rules.d"
mkdir -p "${OUTPUT_DIR}"

# Copy source code
cp -r "${ROOT_DIR}/src/nexus_air" "${APPDIR}/usr/lib/python3/site-packages/"

# Create entrypoint binary
cat > "${APPDIR}/usr/bin/nexus-air" << 'EOF'
#!/usr/bin/env python3
import sys
from nexus_air.cli import main
if __name__ == '__main__':
    main()
EOF
chmod +x "${APPDIR}/usr/bin/nexus-air"

# Copy desktop and icon metadata
cp "${ROOT_DIR}/data/org.cachyos.NexusAirV1.desktop" "${APPDIR}/org.cachyos.NexusAirV1.desktop"
cp "${ROOT_DIR}/data/org.cachyos.NexusAirV1.desktop" "${APPDIR}/usr/share/applications/"
cp "${ROOT_DIR}/data/icons/nexus-air.svg" "${APPDIR}/nexus-air.svg"
cp "${ROOT_DIR}/data/icons/nexus-air.svg" "${APPDIR}/usr/share/icons/hicolor/scalable/apps/"
cp "${ROOT_DIR}/data/99-nexus-air.rules" "${APPDIR}/usr/lib/udev/rules.d/"

# Copy AppRun
cp "${SCRIPT_DIR}/AppRun" "${APPDIR}/AppRun"
chmod +x "${APPDIR}/AppRun"

echo "==> AppDir successfully generated at ${APPDIR}"

# Check for appimagetool
if command -v appimagetool >/dev/null 2>&1; then
    echo "==> Building AppImage with appimagetool..."
    ARCH="$(uname -m)" appimagetool "${APPDIR}" "${OUTPUT_DIR}/Nexus_Air_V1-x86_64.AppImage"
    echo "==> Output created: ${OUTPUT_DIR}/Nexus_Air_V1-x86_64.AppImage"
else
    echo "==> NOTE: 'appimagetool' not found locally. To package the final .AppImage:"
    echo "    wget https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage -O /tmp/appimagetool"
    echo "    chmod +x /tmp/appimagetool && /tmp/appimagetool ${APPDIR} ${OUTPUT_DIR}/Nexus_Air_V1-x86_64.AppImage"
fi

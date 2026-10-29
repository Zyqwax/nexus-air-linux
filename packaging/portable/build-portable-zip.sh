#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
PKG_NAME="nexus-air"
VERSION="1.0.0"
BUNDLE_DIR="${ROOT_DIR}/build/${PKG_NAME}-v${VERSION}-linux-portable"
OUTPUT_DIR="${ROOT_DIR}/dist"
ZIP_PATH="${OUTPUT_DIR}/${PKG_NAME}-v${VERSION}-linux-portable.zip"

echo "==> Preparing portable standalone Linux scripts bundle..."
rm -rf "${BUNDLE_DIR}" "${ZIP_PATH}"
mkdir -p "${BUNDLE_DIR}/bin"
mkdir -p "${BUNDLE_DIR}/lib"
mkdir -p "${BUNDLE_DIR}/data"
mkdir -p "${OUTPUT_DIR}"

# Copy python package
cp -r "${ROOT_DIR}/src/nexus_air" "${BUNDLE_DIR}/lib/"

# Copy assets
cp "${ROOT_DIR}/data/99-nexus-air.rules" "${BUNDLE_DIR}/data/"
cp "${ROOT_DIR}/data/icons/nexus-air.svg" "${BUNDLE_DIR}/data/"
cp "${ROOT_DIR}/data/org.cachyos.NexusAirV1.desktop" "${BUNDLE_DIR}/data/"
cp "${ROOT_DIR}/LICENSE" "${BUNDLE_DIR}/"
cp "${ROOT_DIR}/README.md" "${BUNDLE_DIR}/"

# Create root quick-launchers
cat > "${BUNDLE_DIR}/nexus-air" << 'EOF'
#!/usr/bin/env bash
HERE="$(dirname "$(readlink -f "${0}")")"
PYTHONPATH="${HERE}/lib:${PYTHONPATH:-}" exec python3 -m nexus_air.cli "$@"
EOF
chmod +x "${BUNDLE_DIR}/nexus-air"

cat > "${BUNDLE_DIR}/nexus-air-gui" << 'EOF'
#!/usr/bin/env bash
HERE="$(dirname "$(readlink -f "${0}")")"
PYTHONPATH="${HERE}/lib:${PYTHONPATH:-}" exec python3 -m nexus_air.gui "$@"
EOF
chmod +x "${BUNDLE_DIR}/nexus-air-gui"

# Create convenient install script
cat > "${BUNDLE_DIR}/install.sh" << 'EOF'
#!/usr/bin/env bash
set -euo pipefail
HERE="$(dirname "$(readlink -f "${0}")")"

echo "==> Nexus Air V1 — Linux Kurulum Betiği"

if [ "$(id -u)" -ne 0 ]; then
    echo "[-] Kurulum için root yetkisi gerekiyor. Lütfen sudo ile çalıştırın:"
    echo "    sudo ./install.sh"
    exit 1
fi

echo "[*] udev kuralı kuruluyor (/etc/udev/rules.d/99-nexus-air.rules)..."
install -Dm644 "${HERE}/data/99-nexus-air.rules" "/etc/udev/rules.d/99-nexus-air.rules"
udevadm control --reload-rules || true
udevadm trigger || true

echo "[*] Komutlar /usr/local/bin dizinine kuruluyor..."
install -d "/usr/local/share/nexus-air"
cp -r "${HERE}/lib/nexus_air" "/usr/local/share/nexus-air/"

cat > "/usr/local/bin/nexus-air" << 'EOSH'
#!/usr/bin/env bash
PYTHONPATH="/usr/local/share/nexus-air:${PYTHONPATH:-}" exec python3 -m nexus_air.cli "$@"
EOSH
chmod 755 "/usr/local/bin/nexus-air"

cat > "/usr/local/bin/nexus-air-gui" << 'EOSH'
#!/usr/bin/env bash
PYTHONPATH="/usr/local/share/nexus-air:${PYTHONPATH:-}" exec python3 -m nexus_air.gui "$@"
EOSH
chmod 755 "/usr/local/bin/nexus-air-gui"

echo "[*] Masaüstü kısayolu kuruluyor..."
install -Dm644 "${HERE}/data/icons/nexus-air.svg" "/usr/share/icons/hicolor/scalable/apps/nexus-air.svg"
sed 's|Exec=nexus-air gui|Exec=/usr/local/bin/nexus-air-gui|g' "${HERE}/data/org.cachyos.NexusAirV1.desktop" > "/usr/share/applications/org.cachyos.NexusAirV1.desktop"

echo "[+] Kurulum tamamlandı!"
echo "[+] Menüden 'Nexus Air V1' aratarak açabilir veya terminalden 'nexus-air' yazabilirsiniz."
EOF
chmod +x "${BUNDLE_DIR}/install.sh"

# Create uninstall script
cat > "${BUNDLE_DIR}/uninstall.sh" << 'EOF'
#!/usr/bin/env bash
set -euo pipefail

if [ "$(id -u)" -ne 0 ]; then
    echo "[-] Lütfen sudo ile çalıştırın: sudo ./uninstall.sh"
    exit 1
fi

echo "[*] Nexus Air V1 kaldırılıyor..."
rm -f "/usr/local/bin/nexus-air"
rm -f "/usr/local/bin/nexus-air-gui"
rm -rf "/usr/local/share/nexus-air"
rm -f "/usr/share/applications/org.cachyos.NexusAirV1.desktop"
rm -f "/usr/share/icons/hicolor/scalable/apps/nexus-air.svg"
rm -f "/etc/udev/rules.d/99-nexus-air.rules"
udevadm control --reload-rules || true
udevadm trigger || true
echo "[+] Başarıyla kaldırıldı."
EOF
chmod +x "${BUNDLE_DIR}/uninstall.sh"

echo "==> Creating ZIP archive at ${ZIP_PATH}..."
(cd "${ROOT_DIR}/build" && zip -r -q "${ZIP_PATH}" "${PKG_NAME}-v${VERSION}-linux-portable")
echo "==> Successfully generated standalone portable zip: ${ZIP_PATH}"
ls -lh "${ZIP_PATH}"

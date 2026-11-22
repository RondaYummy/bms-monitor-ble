#!/usr/bin/env bash
# certbot deploy hook: runs after every successful issue/renewal (installed by setup-certbot-dns.sh
# into /etc/letsencrypt/renewal-hooks/deploy/). certbot sets RENEWED_LINEAGE=/etc/letsencrypt/live/<domain>.
set -euo pipefail

LINEAGE="${RENEWED_LINEAGE:?RENEWED_LINEAGE is not set}"
# Mounted read-only into the backend container as /ssl (see docker-compose.yml).
PUBLISH_DIR="${BMS_SSL_PUBLISH_DIR:-/var/lib/bms-monitor/ssl}"

# Only the PUBLIC certificate chain is published for the status card; the private key stays in /etc/letsencrypt.
mkdir -p "$PUBLISH_DIR"
install -m 644 "$LINEAGE/fullchain.pem" "$PUBLISH_DIR/fullchain.pem.tmp"
mv -f "$PUBLISH_DIR/fullchain.pem.tmp" "$PUBLISH_DIR/fullchain.pem"

# Make nginx serve the new certificate (validate the config first).
if command -v nginx >/dev/null 2>&1; then
  nginx -t && systemctl reload nginx
fi

echo "✅ [$(date '+%F %T')] Certificate deployed from $LINEAGE"

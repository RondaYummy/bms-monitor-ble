#!/usr/bin/env bash
# Automatic Let's Encrypt certificates via the DNS-01 challenge (no open ports 80/443 needed).
#
# Usage (on the server, as root):
#   sudo ./scripts/ssl/setup-certbot-dns.sh <provider> <domain> [email]
#   e.g. sudo ./scripts/ssl/setup-certbot-dns.sh cloudflare solar.example.com me@example.com
#
# Providers: cloudflare (recommended, free), godaddy, digitalocean, route53, google, ovh
#
# What it does:
#   1. installs certbot + the DNS plugin into an isolated venv (/opt/certbot)
#   2. creates /etc/letsencrypt/dns-<provider>.ini (chmod 600) for your API credentials
#   3. issues/replaces the certificate with the DNS plugin (the renewal config remembers it)
#   4. installs a systemd timer that runs `certbot renew` twice a day
#   5. registers scripts/ssl/deploy-hook.sh: reloads nginx and publishes the PUBLIC certificate
#      for the backend's SSL status card (the private key is never copied)
set -euo pipefail

PROVIDER="${1:-}"
DOMAIN="${2:-}"
EMAIL="${3:-}"
CERTBOT_VENV=/opt/certbot
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOK_TARGET=/etc/letsencrypt/renewal-hooks/deploy/bms-monitor.sh

if [[ -z "$PROVIDER" || -z "$DOMAIN" ]]; then
  sed -n '2,20p' "$0"
  exit 1
fi
if [[ $EUID -ne 0 ]]; then
  echo "❌ Run as root (sudo)."
  exit 1
fi

case "$PROVIDER" in
  cloudflare)
    PACKAGE=certbot-dns-cloudflare
    CREDENTIALS_TEMPLATE='# API token with Zone:DNS:Edit permission for the zone
dns_cloudflare_api_token = <your-cloudflare-api-token>'
    ;;
  godaddy)
    # Third-party plugin. NOTE: GoDaddy restricts its DNS API for small accounts; if you get
    # "ACCESS_DENIED", move the DNS zone to Cloudflare (free) and use the cloudflare provider.
    PACKAGE=certbot-dns-godaddy
    CREDENTIALS_TEMPLATE='dns_godaddy_key = <your-godaddy-api-key>
dns_godaddy_secret = <your-godaddy-api-secret>'
    ;;
  digitalocean)
    PACKAGE=certbot-dns-digitalocean
    CREDENTIALS_TEMPLATE='dns_digitalocean_token = <your-digitalocean-token>'
    ;;
  route53)
    PACKAGE=certbot-dns-route53
    CREDENTIALS_TEMPLATE='# route53 reads AWS credentials from ~/.aws/credentials or the environment; this file is unused'
    ;;
  google)
    PACKAGE=certbot-dns-google
    CREDENTIALS_TEMPLATE='# path to a service-account JSON is passed instead; see certbot-dns-google docs'
    ;;
  ovh)
    PACKAGE=certbot-dns-ovh
    CREDENTIALS_TEMPLATE='dns_ovh_endpoint = ovh-eu
dns_ovh_application_key = <key>
dns_ovh_application_secret = <secret>
dns_ovh_consumer_key = <consumer-key>'
    ;;
  *)
    echo "❌ Unknown provider: $PROVIDER"
    exit 1
    ;;
esac

echo "⏳ Installing certbot and $PACKAGE into $CERTBOT_VENV"
apt-get install -y python3-venv >/dev/null
python3 -m venv "$CERTBOT_VENV"
"$CERTBOT_VENV/bin/pip" install --quiet --upgrade pip
"$CERTBOT_VENV/bin/pip" install --quiet certbot "$PACKAGE"
ln -sf "$CERTBOT_VENV/bin/certbot" /usr/local/bin/certbot-dns

CREDENTIALS="/etc/letsencrypt/dns-$PROVIDER.ini"
mkdir -p /etc/letsencrypt
if [[ ! -f "$CREDENTIALS" ]]; then
  umask 077
  printf '%s\n' "$CREDENTIALS_TEMPLATE" > "$CREDENTIALS"
  chmod 600 "$CREDENTIALS"
  echo "✍️  Fill in your API credentials in $CREDENTIALS and run this script again."
  exit 2
fi
if grep -q '<your-\|<key>\|<secret>' "$CREDENTIALS"; then
  echo "✍️  $CREDENTIALS still contains placeholders. Fill them in and run again."
  exit 2
fi
chmod 600 "$CREDENTIALS"

echo "⏳ Installing the deploy hook"
mkdir -p "$(dirname "$HOOK_TARGET")"
install -m 755 "$SCRIPT_DIR/deploy-hook.sh" "$HOOK_TARGET"

CREDENTIAL_ARGS=()
if [[ "$PROVIDER" != "route53" && "$PROVIDER" != "google" ]]; then
  # route53/google read credentials from their own config and don't support propagation-seconds
  CREDENTIAL_ARGS=(--"dns-$PROVIDER-credentials" "$CREDENTIALS" --"dns-$PROVIDER-propagation-seconds" 60)
fi
EMAIL_ARGS=(--register-unsafely-without-email)
if [[ -n "$EMAIL" ]]; then
  EMAIL_ARGS=(--email "$EMAIL")
fi

echo "⏳ Requesting the certificate for $DOMAIN (an existing manual certificate will be replaced)"
/usr/local/bin/certbot-dns certonly \
  --authenticator "dns-$PROVIDER" \
  "${CREDENTIAL_ARGS[@]}" \
  --cert-name "$DOMAIN" -d "$DOMAIN" \
  "${EMAIL_ARGS[@]}"

# The distro certbot (apt) has no DNS plugin: its own timer would now fail on every renewal attempt.
if systemctl list-unit-files certbot.timer >/dev/null 2>&1 && systemctl is-enabled --quiet certbot.timer 2>/dev/null; then
  echo "ℹ️  Disabling the distro certbot.timer (renewals are handled by certbot-dns-renew.timer)"
  systemctl disable --now certbot.timer
fi

echo "⏳ Installing the renewal timer"
cat > /etc/systemd/system/certbot-dns-renew.service <<EOF
[Unit]
Description=Renew Let's Encrypt certificates (DNS challenge)

[Service]
Type=oneshot
ExecStart=/usr/local/bin/certbot-dns renew --quiet
EOF
cat > /etc/systemd/system/certbot-dns-renew.timer <<'EOF'
[Unit]
Description=Twice-daily certbot renewal check

[Timer]
OnCalendar=*-*-* 03,15:17:00
RandomizedDelaySec=1h
Persistent=true

[Install]
WantedBy=timers.target
EOF
systemctl daemon-reload
systemctl enable --now certbot-dns-renew.timer

# Publish the current certificate right away (the hook also runs after every renewal).
RENEWED_LINEAGE="/etc/letsencrypt/live/$DOMAIN" "$HOOK_TARGET"

echo "⏳ Testing renewal (dry run)"
/usr/local/bin/certbot-dns renew --dry-run --cert-name "$DOMAIN"

echo "✅ Done. Certificates now renew automatically. Timer status: systemctl list-timers certbot-dns-renew.timer"

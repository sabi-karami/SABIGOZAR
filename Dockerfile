# ───────────────────────────────────────────────────────────
#  SABIGOZAR Panel  ·  Telegram: @SAHEBKARAMI
#  Panel + Xray core + nginx in ONE Railway service
#  Based on PasarGuard (AGPL-3.0) and Xray-core (MPL-2.0)
# ───────────────────────────────────────────────────────────
ARG PANEL_VERSION=v5.4.1
ARG NODE_VERSION=v0.5.4

FROM pasarguard/node:${NODE_VERSION} AS node

FROM pasarguard/panel:${PANEL_VERSION}

RUN apt-get update \
 && apt-get install -y --no-install-recommends nginx openssl ca-certificates curl sqlite3 tzdata \
 && rm -rf /var/lib/apt/lists/* /etc/nginx/sites-enabled/default /etc/nginx/conf.d/default.conf

COPY --from=node /app/main /opt/pg-node/main
COPY --from=node /usr/local/bin/xray /usr/local/bin/xray
COPY --from=node /usr/local/share/xray /usr/local/share/xray

COPY branding/ /opt/sabigozar/branding/
COPY tools/ /opt/sabigozar/tools/
RUN python /opt/sabigozar/tools/rebrand.py /code /opt/sabigozar/branding

COPY nginx/ /etc/nginx/sabigozar/
COPY templates/ /opt/sabigozar/templates/
COPY static/ /opt/sabigozar/static/
COPY scripts/ /opt/sabigozar/scripts/
COPY entrypoint.sh /entrypoint.sh
RUN find /entrypoint.sh /opt/sabigozar /etc/nginx/sabigozar -type f \
      \( -name '*.sh' -o -name '*.py' -o -name '*.conf' -o -name '*.inc' -o -name '*.template' -o -name '*.html' \) \
      -exec sed -i 's/\r$//' {} + \
 && chmod +x /entrypoint.sh /opt/pg-node/main /usr/local/bin/xray \
 && find /opt/sabigozar/scripts -name '*.sh' -exec chmod +x {} + \
 && mkdir -p /var/lib/sabigozar /var/lib/pg-node/generated

ENV PORT=8080 \
    SABI_DATA=/var/lib/sabigozar \
    UVICORN_HOST=127.0.0.1 \
    UVICORN_PORT=8000 \
    UVICORN_PROXY_HEADERS=True \
    UVICORN_FORWARDED_ALLOW_IPS=127.0.0.1 \
    SQLALCHEMY_DATABASE_URL=sqlite+aiosqlite:////var/lib/sabigozar/db.sqlite3 \
    CUSTOM_TEMPLATES_DIRECTORY=/opt/sabigozar/templates/ \
    SUBSCRIPTION_PATH=sub \
    XRAY_EXECUTABLE_PATH=/usr/local/bin/xray \
    XRAY_ASSETS_PATH=/usr/local/share/xray \
    DOCS=False \
    TZ=Asia/Tehran

EXPOSE 8080 8443
HEALTHCHECK --interval=30s --timeout=6s --start-period=90s CMD /opt/sabigozar/scripts/healthcheck.sh || exit 1
ENTRYPOINT ["/entrypoint.sh"]

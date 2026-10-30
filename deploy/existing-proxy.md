# Einbindung in einen vorhandenen Reverse-Proxy

Ist Port 80/443 auf dem Server bereits belegt, läuft Caddy mit `HTTP_PORT=18080` (intern) und
der vorhandene Proxy reicht die Domain weiter.

nginx:

    server {
        server_name geo-demo.example.de;
        # TLS wie bei den übrigen Seiten (z. B. certbot)
        location / {
            proxy_pass http://127.0.0.1:18080;
            proxy_set_header Host $host;
            proxy_set_header X-Forwarded-For $remote_addr;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }

Caddy (vorhanden):

    geo-demo.example.de {
        reverse_proxy 127.0.0.1:18080
    }

In `.env` auf dem Server: `SITE_ADDRESS=:80`, `HTTP_PORT=18080`, `HTTPS_PORT=18443`, `COOKIE_SECURE=1`.

FROM python:3.11-slim as backend-builder

WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ /app/
RUN pip install --no-cache-dir gunicorn

FROM node:18-alpine as frontend-builder

WORKDIR /app
COPY frontend/package*.json ./
RUN npm install && npm install -g vite

COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim as final

COPY --from=backend-builder /app /
RUN pip install --no-cache-dir gunicorn

RUN apt-get update && apt-get install -y nginx && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /etc/nginx/ssl && openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/nginx/ssl/server.key -out /etc/nginx/ssl/server.crt \
    -subj "/C=CN/ST=Guangxi/L=Nanning/O=HBPC/OU=CustomerService/CN=schedule.hbpc.com"

COPY --from=frontend-builder /app/dist /usr/share/nginx/html

RUN echo '#!/bin/sh' > /entrypoint.sh && \
    echo 'cd /app' >> /entrypoint.sh && \
    echo 'python -c "import app.models.database; from app.models import *; app.models.database.Base.metadata.create_all(bind=app.models.database.engine)"' >> /entrypoint.sh && \
    echo 'gunicorn -w 4 -b 0.0.0.0:8000 app.main:app &' >> /entrypoint.sh && \
    echo 'nginx -g \"daemon off;\"' >> /entrypoint.sh && \
    chmod +x /entrypoint.sh

RUN echo 'server {' > /etc/nginx/conf.d/default.conf && \
    echo '    listen 80;' >> /etc/nginx/conf.d/default.conf && \
    echo '    server_name localhost;' >> /etc/nginx/conf.d/default.conf && \
    echo '    return 301 https://$host$request_uri;' >> /etc/nginx/conf.d/default.conf && \
    echo '}' >> /etc/nginx/conf.d/default.conf && \
    echo '' >> /etc/nginx/conf.d/default.conf && \
    echo 'server {' >> /etc/nginx/conf.d/default.conf && \
    echo '    listen 443 ssl http2;' >> /etc/nginx/conf.d/default.conf && \
    echo '    server_name localhost;' >> /etc/nginx/conf.d/default.conf && \
    echo '' >> /etc/nginx/conf.d/default.conf && \
    echo '    ssl_certificate /etc/nginx/ssl/server.crt;' >> /etc/nginx/conf.d/default.conf && \
    echo '    ssl_certificate_key /etc/nginx/ssl/server.key;' >> /etc/nginx/conf.d/default.conf && \
    echo '    ssl_session_timeout 1d;' >> /etc/nginx/conf.d/default.conf && \
    echo '    ssl_session_cache shared:SSL:10m;' >> /etc/nginx/conf.d/default.conf && \
    echo '    ssl_session_tickets off;' >> /etc/nginx/conf.d/default.conf && \
    echo '    ssl_protocols TLSv1.2 TLSv1.3;' >> /etc/nginx/conf.d/default.conf && \
    echo '    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;' >> /etc/nginx/conf.d/default.conf && \
    echo '    ssl_prefer_server_ciphers off;' >> /etc/nginx/conf.d/default.conf && \
    echo '' >> /etc/nginx/conf.d/default.conf && \
    echo '    location / {' >> /etc/nginx/conf.d/default.conf && \
    echo '        root /usr/share/nginx/html;' >> /etc/nginx/conf.d/default.conf && \
    echo '        index index.html index.htm;' >> /etc/nginx/conf.d/default.conf && \
    echo '        try_files $uri $uri/ /index.html;' >> /etc/nginx/conf.d/default.conf && \
    echo '    }' >> /etc/nginx/conf.d/default.conf && \
    echo '' >> /etc/nginx/conf.d/default.conf && \
    echo '    location /api {' >> /etc/nginx/conf.d/default.conf && \
    echo '        proxy_pass http://localhost:8000;' >> /etc/nginx/conf.d/default.conf && \
    echo '        proxy_set_header Host $host;' >> /etc/nginx/conf.d/default.conf && \
    echo '        proxy_set_header X-Real-IP $remote_addr;' >> /etc/nginx/conf.d/default.conf && \
    echo '        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;' >> /etc/nginx/conf.d/default.conf && \
    echo '        proxy_set_header X-Forwarded-Proto $scheme;' >> /etc/nginx/conf.d/default.conf && \
    echo '    }' >> /etc/nginx/conf.d/default.conf && \
    echo '}' >> /etc/nginx/conf.d/default.conf

EXPOSE 80 443

CMD /entrypoint.sh & nginx -g 'daemon off;'
ENTRYPOINT ["/entrypoint.sh"]
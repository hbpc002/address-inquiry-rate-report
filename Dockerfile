FROM python:3.11-slim as backend-builder

WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ /app/
RUN pip install --no-cache-dir gunicorn

FROM node:18-alpine as frontend-builder

WORKDIR /app
COPY frontend/package*.json ./
RUN npm install

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

RUN printf '#!/bin/sh\ncd /app\npython -c "import app.models.database; from app.models import *; app.models.database.Base.metadata.create_all(bind=app.models.database.engine)"\ngunicorn --bind 0.0.0.0:8000 --worker-class sync --workers 4 app.main:app &\nexec nginx -g daemon off;\n' > /entrypoint.sh && chmod +x /entrypoint.sh

RUN printf 'server {\n    listen 80;\n    server_name localhost;\n}\n\nserver {\n    listen 443 ssl http2;\n    server_name localhost;\n\n    ssl_certificate /etc/nginx/ssl/server.crt;\n    ssl_certificate_key /etc/nginx/ssl/server.key;\n    ssl_session_timeout 1d;\n    ssl_session_cache shared:SSL:10m;\n    ssl_session_tickets off;\n    ssl_protocols TLSv1.2 TLSv1.3;\n    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;\n    ssl_prefer_server_ciphers off;\n\n    location / {\n        root /usr/share/nginx/html;\n        index index.html index.htm;\n        try_files $uri $uri/ /index.html;\n    }\n\n    location /static {\n        proxy_pass http://localhost:8000;\n        proxy_set_header Host $host;\n        proxy_set_header X-Real-IP $remote_addr;\n        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n        proxy_set_header X-Forwarded-Proto $scheme;\n    }\n\n    location /api {\n        proxy_pass http://localhost:8000;\n        proxy_http_version 1.1;\n        proxy_set_header Connection "";\n        proxy_buffering off;\n        proxy_cache off;\n        proxy_read_timeout 3600s;\n        proxy_send_timeout 3600s;\n        proxy_set_header Host $host;\n        proxy_set_header X-Real-IP $remote_addr;\n        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n        proxy_set_header X-Forwarded-Proto $scheme;\n    }\n}\n' > /etc/nginx/conf.d/default.conf

EXPOSE 80 443

ENTRYPOINT ["/entrypoint.sh"]
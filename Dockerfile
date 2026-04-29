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

FROM nginx:alpine

COPY --from=backend-builder /app /app/backend
COPY --from=frontend-builder /app/dist /usr/share/nginx/html

RUN echo '#!/bin/sh\n\
cd /app/backend && \
python -c "import app.models.database; from app.models import *; app.models.database.Base.metadata.create_all(bind=app.models.database.engine)" && \
exec gunicorn -w 4 -b 0.0.0.0:8000 app.main:app' > /entrypoint.sh && \
chmod +x /entrypoint.sh

RUN cat > /etc/nginx/conf.d/default.conf << 'EOF'
server {
    listen 80;
    server_name localhost;

    location / {
        root /usr/share/nginx/html;
        index index.html index.htm;
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

EXPOSE 80

ENTRYPOINT ["/entrypoint.sh"]
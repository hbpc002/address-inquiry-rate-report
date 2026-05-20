#!/bin/bash

DATE=$(date +%Y%m%d)
COUNTER=0
REGISTRY="ghcr.io/hbpc002"

increment() {
  COUNTER=$((COUNTER + 1))
  echo "1.0.${DATE}.${COUNTER}"
}

# 构建后端镜像
VERSION=$(increment)
echo "Building backend version: $VERSION"
docker build -t ${REGISTRY}/address-inquiry-rate-report-backend:latest \
              -t ${REGISTRY}/address-inquiry-rate-report-backend:${VERSION} \
              -f backend/Dockerfile .

echo "Pushing backend..."
docker push ${REGISTRY}/address-inquiry-rate-report-backend:latest
docker push ${REGISTRY}/address-inquiry-rate-report-backend:${VERSION}

# 构建前端镜像
VERSION=$(increment)
echo "Building frontend version: $VERSION"
docker build -t ${REGISTRY}/address-inquiry-rate-report-frontend:latest \
              -t ${REGISTRY}/address-inquiry-rate-report-frontend:${VERSION} \
              -f frontend/Dockerfile .

echo "Pushing frontend..."
docker push ${REGISTRY}/address-inquiry-rate-report-frontend:latest
docker push ${REGISTRY}/address-inquiry-rate-report-frontend:${VERSION}

echo "Done!"
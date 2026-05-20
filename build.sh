#!/bin/bash

VERSION="1.0.$(date +%Y%m%d).$(date +%H%M%S)"
REGISTRY="ghcr.io/hbpc002"

echo "Building version: $VERSION"

# 构建后端镜像
echo "Building backend..."
docker build -t ${REGISTRY}/address-inquiry-rate-report-backend:latest \
              -t ${REGISTRY}/address-inquiry-rate-report-backend:${VERSION} \
              -f backend/Dockerfile .

echo "Pushing backend..."
docker push ${REGISTRY}/address-inquiry-rate-report-backend:latest
docker push ${REGISTRY}/address-inquiry-rate-report-backend:${VERSION}

# 构建前端镜像
echo "Building frontend..."
docker build -t ${REGISTRY}/address-inquiry-rate-report-frontend:latest \
              -t ${REGISTRY}/address-inquiry-rate-report-frontend:${VERSION} \
              -f frontend/Dockerfile .

echo "Pushing frontend..."
docker push ${REGISTRY}/address-inquiry-rate-report-frontend:latest
docker push ${REGISTRY}/address-inquiry-rate-report-frontend:${VERSION}

echo "Done! Version $VERSION pushed successfully."
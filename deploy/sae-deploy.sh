#!/bin/bash
cd backend
docker build -t registry.cn-guangzhou.aliyuncs.com/your-namespace/backend:latest .
docker push registry.cn-guangzhou.aliyuncs.com/your-namespace/backend:latest

#!/bin/bash
cd fc_worker
zip -r worker.zip .
aliyun fc function update \
  --service-name dataset-processor \
  --function-name process-yolo \
  --code worker.zip \
  --runtime python3.9 \
  --handler main.handler
rm worker.zip

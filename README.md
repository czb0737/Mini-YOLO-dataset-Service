# Ultralytics Dataset Importer — Full Stack Coding Challenge

[![Python](https://img.shields.io/badge/Python-3.11+-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-14-blueviolet)](https://nextjs.org/)
[![Ultralytics](https://img.shields.io/badge/Ultralytics-8.3+-orange)](https://ultralytics.com/)
[![Alibaba Cloud](https://img.shields.io/badge/Alibaba_Cloud-OSS%20%26%20FC-lightgrey)](https://www.alibabacloud.com/)

A production-grade solution for importing, validating, parsing, and visualizing **YOLO-formatted datasets** up to **100GB**. Built for the **[Ultralytics Full Stack Coding Challenge](https://ultralytics.com/)** with a focus on **senior-level engineering practices**.

---

## ✨ Features

- **Large File Upload**  
  Supports datasets up to 100GB via **OSS multipart upload** with **STS temporary credentials** for security.
- **YOLO Format Validation**  
  Uses `ultralytics.data.utils.check_det_dataset` to ensure dataset compliance.
- **Async Processing**  
  Decouples upload from parsing using **event-driven architecture** (local: direct call; cloud: OSS → Function Compute).
- **Secure Storage**  
  - **Images**: Stored in **Alibaba Cloud OSS**
  - **Annotations & Metadata**: Stored in **MongoDB**
- **Frontend Visualization**  
  - Lists all datasets
  - Shows images with **overlayed YOLO bounding boxes and class labels**
  - Limits display to **10 images** for performance
- **Cloud-Agnostic Design**  
  Easily portable to GCP/AWS (Ultralytics explicitly allows cloud provider substitution).

---

## 🏗️ Architecture

```mermaid
graph LR
  A[Next.js Frontend] -->|1. Get STS Token| B(FastAPI Backend)
  B -->|2. Return Temp Credentials| A
  A -->|3. Multipart Upload| C[Alibaba Cloud OSS]
  A -->|4. Notify Complete| B
  B -->|5. Trigger Process| D[fc_worker]
  D -->|6. Download ZIP| C
  D -->|7. Validate + Parse| D
  D -->|8. Store Metadata| E[MongoDB]
  D -->|9. (Optional) Re-upload Images| C
  A -->|10. Fetch Datasets/Images| B
  B -->|11. Return Signed URLs| A
  A -->|12. Render Canvas + Labels| A

---

## 🚀 Local Development
### Prerequisites
- **Docker & Docker Compose**
- **Node.js v18+**
- **Python 3.11+**
- **Alibaba Cloud account** (for OSS/STS)**

### Setup
1. Clone the repo
```
git clone https://github.com/yourname/ultralytics-dataset-importer.git
cd ultralytics-dataset-importer
```

2. Configure environment
```
# Backend
cp .env.example .env
# Fill in ALIYUN_ACCESS_KEY_ID, ALIYUN_ACCESS_KEY_SECRET, etc.

# Frontend
cp frontend/.env.local.example frontend/.env.local
```
3. Start service
```
# Backend + MongoDB
docker-compose up --build

# Frontend
cd frontend && npm install && npm run dev
```
4. Access the application
- **Upload: http://localhost:3000/upload**
- **Datasets: http://localhost:3000/datasets**

---

## ☁️ Cloud Deployment (Alibaba Cloud)
### Create Resources
- **OSS Bucket (ultralytics-test)**
- **ApsaraDB for MongoDB**
- **RAM User + Role with STS/OSS permissions**
- **MNS Topic + Function Compute service**
### Deploy Backend
- **Build Docker image → Push to ACR**
- **Deploy to Serverless App Engine (SAE)**
### Deploy Worker
- **Package fc_worker/ → Deploy to Function Compute**
- **Configure OSS Event → MNS Topic → FC Trigger**
### Deploy Frontend
- **npm run build && npm run export**
- **Upload out/ to OSS Static Website**
> Note: In production, /api/upload/complete is not called — processing is triggered automatically by OSS events.

---

## 🧪 Testing
### Valid Dataset
- **Use the official COCO128 dataset (5MB):**
```
wget https://ultralytics.com/assets/coco128.zip
```
Structure:
```
coco128/
├── data.yaml
├── images/train2017/
├── images/val2017/
├── labels/train2017/
└── labels/val2017/
```
### Validation
```
from ultralytics.data.utils import check_det_dataset
check_det_dataset("coco128")  # Returns dataset info
```

---

## 🧠 Engineering Trade-offs
| DECISION | RATIONALE |
|---------|---------|
| Local: Direct `process_dataset` call | Simplifies debugging; avoids mocking FC |
| Cloud: OSS Event → FC | Event-driven, scalable, no backend coupling |
| Pre-signed URLs for Images | Secure access to private OSS without public exposure |
| Canvas-based Label Rendering | No external dependencies; full control over visualization |
| Limit to 10 Images | Prevents UI freeze on large datasets |
| Separate `fc_worker` module | Clear boundary between API and processing logic |

> ✅ Focus on quality over quantity: Core challenges (large upload, async, validation) are solved with production-grade patterns. 

## 📦 Repository Structure
```
ultralytics-dataset-importer/
├── frontend/          # Next.js UI (upload, dataset list, image viewer)
├── backend/           # FastAPI (STS, API, MongoDB)
├── fc_worker/         # Core logic (OSS download, YOLO parse, DB write)
├── docker-compose.yml # Local dev environment
└── README.md
```
## 📄 License
This project is for educational and assessment purposes only as part of the Ultralytics Coding Challenge. Not for production use without proper security review.

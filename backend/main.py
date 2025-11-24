from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
from bson import ObjectId
import json, uuid, os
from aliyunsdkcore.client import AcsClient
from aliyunsdksts.request.v20150401 import AssumeRoleRequest
from motor.motor_asyncio import AsyncIOMotorClient

# Initialize FastAPI (only once)
app = FastAPI(title="Ultralytics Dataset Importer")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
ALIYUN_ACCESS_KEY_ID = os.getenv("ALIYUN_ACCESS_KEY_ID")
ALIYUN_ACCESS_KEY_SECRET = os.getenv("ALIYUN_ACCESS_KEY_SECRET")
ALIYUN_ROLE_ARN = os.getenv("ALIYUN_ROLE_ARN")
OSS_REGION = os.getenv("OSS_REGION", "cn-guangzhou")
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")

# Clients
acs_client = AcsClient(ALIYUN_ACCESS_KEY_ID, ALIYUN_ACCESS_KEY_SECRET, OSS_REGION)
mongo_client = AsyncIOMotorClient(MONGO_URI)
db = mongo_client.yolo_datasets


# Pydantic Models (solve ObjectId serialization issue)
class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            return v
        return ObjectId(v)


class DatasetModel(BaseModel):
    id: str = Field(alias="_id")
    name: str
    status: str
    nc: Optional[int] = None
    names: Optional[List[str]] = None
    splits: Optional[List[str]] = None

    class Config:
        allow_population_by_field_name = True


class ImageModel(BaseModel):
    dataset_id: str
    filename: str
    split: str
    width: int
    height: int
    annotations: List[dict]


# Request Models
class AuthRequest(BaseModel):
    filename: str
    size: int


class CompleteRequest(BaseModel):
    objectKey: str
    filename: str


# === API Endpoints ===


@app.post("/api/oss/auth")
def get_oss_sts_token(req: AuthRequest):
    """Get OSS temporary upload credentials (Aliyun STS)"""
    try:
        request = AssumeRoleRequest.AssumeRoleRequest()
        request.set_RoleArn(ALIYUN_ROLE_ARN)
        request.set_RoleSessionName(f"upload-{uuid.uuid4().hex[:8]}")
        request.set_DurationSeconds(3600)
        response = acs_client.do_action_with_exception(request)
        creds = json.loads(response)["Credentials"]
        object_key = f"uploads/{uuid.uuid4()}/{req.filename}"
        return {"credentials": creds, "objectKey": object_key}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"STS error: {str(e)}")


@app.post("/api/upload/complete")
async def upload_complete(req: CompleteRequest):
    """
    Frontend notification of upload completion, triggers dataset processing.
    Local development: directly call fc_worker.process_dataset
    Cloud deployment: should be triggered by OSS event to FC, this can be simplified to log recording
    """
    try:
        # from fc_worker.main import process_dataset

        # result = await process_dataset(req.objectKey, req.filename)
        # return {"status": "processing_started", "result": result}
        return {"status": "upload_received", "object_key": req.objectKey}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


@app.get("/api/datasets", response_model=List[DatasetModel])
async def list_datasets():
    """Return list of all datasets (for frontend display)"""
    datasets = await db.datasets.find().to_list(None)
    return datasets


@app.get("/api/datasets/{dataset_id}/images", response_model=List[ImageModel])
async def list_images(dataset_id: str):
    """Return all images and annotations for the specified dataset"""
    images = await db.images.find({"dataset_id": dataset_id}).to_list(None)
    return images


@app.get("/api/datasets/{dataset_id}/images-signed")
async def get_signed_image_urls(dataset_id: str):
    """Return list of signed image URLs (valid for 1 hour)"""
    import oss2

    auth = oss2.Auth(
        access_key_id=os.getenv("ALIYUN_ACCESS_KEY_ID"),
        access_key_secret=os.getenv("ALIYUN_ACCESS_KEY_SECRET"),
    )
    bucket = oss2.Bucket(
        auth,
        endpoint=f"https://oss-{os.getenv('OSS_REGION')}.aliyuncs.com",
        bucket_name=os.getenv("OSS_BUCKET"),
    )

    # Get image list
    images = await db.images.find({"dataset_id": dataset_id}).to_list(10)
    signed_urls = []
    for img in images:
        oss_key = f"datasets/{dataset_id}/images/{img['filename']}"
        url = bucket.sign_url("GET", oss_key, 3600)  # Valid for 1 hour
        signed_urls.append(
            {
                "filename": img["filename"],
                "split": img["split"],
                "annotations": img["annotations"],
                "signed_url": url,
            }
        )
    return signed_urls


# ===== Local testing: Simulate upload completion (only for quick API layer verification) =====
@app.post("/api/test/upload-complete")
async def test_upload_complete():
    """For local testing: directly insert mock data (skip YOLO parsing)"""
    from datetime import datetime

    object_key = f"uploads/test-{int(datetime.now().timestamp())}/test-dataset.zip"
    dataset_id = object_key.split("/")[1]

    await db.datasets.insert_one(
        {
            "_id": dataset_id,
            "name": "test-dataset.zip",
            "status": "ready",
            "created_at": datetime.utcnow(),
            "splits": ["train", "val"],
            "nc": 3,
            "names": ["cat", "dog", "car"],
        }
    )

    for i in range(5):
        await db.images.insert_one(
            {
                "dataset_id": dataset_id,
                "filename": f"image_{i}.jpg",
                "split": "train",
                "width": 640,
                "height": 480,
                "annotations": [{"class_id": i % 3, "bbox": [0.5, 0.5, 0.2, 0.3]}],
            }
        )

    return {"status": "mock_processed", "dataset_id": dataset_id}

# fc_worker/main.py
from datetime import datetime
import json
import os
import oss2
import tempfile
import yaml
import zipfile
from pathlib import Path
from urllib.parse import urlparse
from motor.motor_asyncio import AsyncIOMotorClient
from ultralytics.data.utils import check_det_dataset
from PIL import Image  # 用于获取图像尺寸

# 从环境变量获取配置
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
OSS_BUCKET = os.getenv("OSS_BUCKET", "ultralytics-test")
OSS_ENDPOINT = os.getenv("OSS_ENDPOINT", "oss-cn-guangzhou-internal.aliyuncs.com")
OSS_REGION = os.getenv("OSS_REGION", "cn-guangzhou")


def get_oss_bucket():
    """获取 OSS Bucket 客户端（用于上传图像）"""
    auth = oss2.Auth(
        access_key_id=os.getenv("ALIYUN_ACCESS_KEY_ID"),
        access_key_secret=os.getenv("ALIYUN_ACCESS_KEY_SECRET"),
    )
    endpoint = f"https://oss-{OSS_REGION}.aliyuncs.com"
    return oss2.Bucket(auth, endpoint, OSS_BUCKET)


def download_from_oss(object_key: str, local_path: str):
    """从 OSS 下载 ZIP 文件"""
    bucket = get_oss_bucket()
    bucket.get_object_to_file(object_key, local_path)


def upload_image_to_oss(local_img_path: str, dataset_id: str, filename: str):
    """上传单张图像到 OSS 的 datasets/ 路径"""
    bucket = get_oss_bucket()
    oss_key = f"datasets/{dataset_id}/images/{filename}"
    # bucket.put_object_from_file(oss_key, local_img_path)
    # return oss_key
    try:
        print(f"📤 Uploading {local_img_path} to OSS key: {oss_key}")
        result = bucket.put_object_from_file(oss_key, local_img_path)
        if result.status == 200:
            print(f"✅ Upload successful! ETag: {result.etag}")
            return True
        else:
            print(f"⚠️ Upload failed with status: {result.status}")
            return False
    except oss2.exceptions.OssError as e:
        print(f"❌ OSS Error: {e.code} - {e.message}")
        return False
    except Exception as e:
        print(f"💥 Unexpected error: {e}")
        return False


from pathlib import Path


def find_dataset_root(extract_dir: str) -> str:
    """查找包含 data.yaml 的真实数据集根目录"""
    extract_path = Path(extract_dir)
    if (extract_path / "data.yaml").exists():
        return str(extract_path)
    for item in extract_path.iterdir():
        if item.is_dir() and (item / "data.yaml").exists():
            return str(item)
    raise FileNotFoundError(f"No data.yaml in {extract_dir}")


def validate_and_parse_dataset(root_dir: str, dataset_id: str, original_filename: str):
    """验证 YOLO 格式并解析图像/标注"""
    import yaml
    from PIL import Image

    root_path = Path(root_dir)
    data_yaml_path = root_path / "data.yaml"
    if not data_yaml_path.exists():
        raise FileNotFoundError("data.yaml not found")

    with open(data_yaml_path, "r", encoding="utf-8") as f:
        data_yaml = yaml.safe_load(f)

    # 构建 dataset 元数据
    dataset_doc = {
        "_id": dataset_id,
        "name": original_filename,
        "status": "ready",
        "nc": data_yaml.get("nc", 0),
        "names": data_yaml.get("names", []),
        "splits": [],
    }

    # 解析所有 split
    image_docs = []
    for split in ["train", "val", "test"]:
        if split not in data_yaml:
            continue

        dataset_doc["splits"].append(split)
        img_rel_path = data_yaml[split]
        img_dir = (
            root_path / img_rel_path
            if not Path(img_rel_path).is_absolute()
            else Path(img_rel_path)
        )
        label_dir = Path(str(img_dir).replace("images", "labels"))

        if not img_dir.exists():
            continue

        for img_path in img_dir.iterdir():
            if img_path.is_dir() or img_path.suffix.lower() not in [
                ".jpg",
                ".jpeg",
                ".png",
            ]:
                continue

            # 上传图像到 OSS
            upload_image_to_oss(str(img_path), dataset_id, img_path.name)

            # 解析标注
            label_path = label_dir / (img_path.stem + ".txt")
            annotations = []
            if label_path.exists():
                with open(label_path, "r", encoding="utf-8") as lf:
                    for line in lf:
                        parts = line.strip().split()
                        if len(parts) >= 5:
                            try:
                                cls_id = int(parts[0])
                                bbox = [float(x) for x in parts[1:5]]
                                annotations.append({"class_id": cls_id, "bbox": bbox})
                            except (ValueError, IndexError):
                                continue

            # 获取图像尺寸
            width, height = 0, 0
            try:
                with Image.open(img_path) as im:
                    width, height = im.size
            except Exception:
                pass

            image_docs.append(
                {
                    "dataset_id": dataset_id,
                    "filename": img_path.name,
                    "split": split,
                    "width": width,
                    "height": height,
                    "annotations": annotations,
                }
            )

    return dataset_doc, image_docs


async def process_dataset(object_key: str, original_filename: str):
    dataset_id = object_key.split("/")[1]
    client = AsyncIOMotorClient(MONGO_URI)
    db = client.yolo_datasets

    try:
        # 1. 初始化数据库记录（状态：processing）
        await db.datasets.insert_one(
            {
                "_id": dataset_id,
                "name": original_filename,
                "status": "processing",
                "created_at": datetime.utcnow(),
            }
        )

        # 2. 执行完整处理流程
        with tempfile.TemporaryDirectory() as tmp_dir:
            zip_path = os.path.join(tmp_dir, "dataset.zip")
            extract_dir = os.path.join(tmp_dir, "extracted")

            download_from_oss(object_key, zip_path)
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(extract_dir)

            actual_root = find_dataset_root(extract_dir)
            dataset_doc, image_docs = validate_and_parse_dataset(
                actual_root, dataset_id, original_filename
            )

            # 3. 更新状态为 ready + 写入数据
            await db.datasets.update_one(
                {"_id": dataset_id},
                {
                    "$set": {
                        "status": "ready",
                        "nc": dataset_doc["nc"],
                        "names": dataset_doc["names"],
                        "splits": dataset_doc["splits"],
                        "processed_at": datetime.utcnow(),
                    }
                },
            )
            if image_docs:
                await db.images.insert_many(image_docs)

        return {"status": "success"}

    except Exception as e:
        # 4. 捕获所有异常，更新状态为 failed
        error_msg = str(e)[:500]  # 限制长度
        await db.datasets.update_one(
            {"_id": dataset_id},
            {"$set": {"status": "failed", "error": error_msg}},
            upsert=True,  # 如果 insert_one 未执行，也创建记录
        )
        raise  # 可选：继续抛出异常供上层记录


# ========== 云上 FC 入口 ==========
def handler(event, context):
    """阿里云 Function Compute 入口"""
    evt = json.loads(event)
    object_key = evt["object_key"]
    filename = evt["filename"]
    result = process_dataset(object_key, filename)
    return json.dumps(result)


# ========== 本地调试入口 ==========
if __name__ == "__main__":
    import asyncio
    import sys

    if len(sys.argv) != 3:
        print("Usage: python main.py <object_key> <filename>")
        sys.exit(1)

    object_key = sys.argv[1]
    filename = sys.argv[2]

    result = asyncio.run(process_dataset(object_key, filename))
    print("Local test result:", result)

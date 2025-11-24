// frontend/pages/datasets/[id].tsx
import { useRouter } from 'next/router';
import { useEffect, useRef, useState } from 'react';

type Annotation = {
    class_id: number;
    bbox: [number, number, number, number]; // [x_center, y_center, w, h] normalized
};

type SignedImage = {
    filename: string;
    split: string;
    annotations: Annotation[];
    signed_url: string; // 预签名 OSS URL
};

export default function DatasetDetailPage() {
    const router = useRouter();
    const { id } = router.query;
    const [images, setImages] = useState<SignedImage[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [classNames, setClassNames] = useState<string[]>([]);

    useEffect(() => {
        if (!id) return;

        const fetchData = async () => {
            try {
                // 1. 获取数据集元信息（含类别名）
                const datasetRes = await fetch('http://localhost:8000/api/datasets');
                if (!datasetRes.ok) throw new Error('Failed to fetch datasets');
                const datasets = await datasetRes.json();
                const currentDataset = datasets.find((d: any) => d.id === id || d._id === id);
                if (currentDataset?.names) {
                    setClassNames(currentDataset.names);
                }

                // 2. 获取带签名 URL 的图像列表（最多10张）
                const imagesRes = await fetch(`http://localhost:8000/api/datasets/${id}/images-signed`);
                if (!imagesRes.ok) throw new Error('Failed to fetch signed image URLs');
                const allImages: SignedImage[] = await imagesRes.json();
                setImages(allImages.slice(0, 10)); // ⚡ 限制最多10张
            } catch (err: any) {
                setError(err.message || 'Unknown error');
                console.error('Fetch error:', err);
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, [id]);

    if (loading) return <div className="p-4">Loading dataset...</div>;
    if (error) return <div className="p-4 text-red-500">Error: {error}</div>;
    if (!images.length) return <div className="p-4">No images found in this dataset.</div>;

    return (
        <div className="p-4 max-w-6xl mx-auto">
            <h1 className="text-2xl font-bold mb-6">Dataset: {id}</h1>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {images.map((img) => (
                    <ImageWithAnnotations
                        key={img.filename}
                        image={img}
                        classNames={classNames}
                    />
                ))}
            </div>
        </div>
    );
}

// 单张图像 + 标注渲染组件
function ImageWithAnnotations({ image, classNames }: { image: SignedImage; classNames: string[] }) {
    const canvasRef = useRef<HTMLCanvasElement>(null);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        if (!ctx) return;

        const imgEl = new Image();
        imgEl.crossOrigin = 'anonymous';
        imgEl.src = image.signed_url; // 使用预签名 URL

        imgEl.onload = () => {
            // 设置 canvas 尺寸
            canvas.width = imgEl.width;
            canvas.height = imgEl.height;

            // 绘制图像
            ctx.drawImage(imgEl, 0, 0);

            // 绘制每个 YOLO 标注
            image.annotations.forEach((ann) => {
                const [x, y, w, h] = ann.bbox;
                const left = (x - w / 2) * imgEl.width;
                const top = (y - h / 2) * imgEl.height;
                const boxWidth = w * imgEl.width;
                const boxHeight = h * imgEl.height;

                // 边界框
                ctx.strokeStyle = '#FF0000';
                ctx.lineWidth = 2;
                ctx.strokeRect(left, top, boxWidth, boxHeight);

                // 类别标签
                const className = classNames[ann.class_id] || `Class ${ann.class_id}`;
                ctx.fillStyle = '#FF0000';
                ctx.font = '14px Arial';
                ctx.fillText(className, left, top - 4);
            });
        };

        imgEl.onerror = () => {
            ctx.fillStyle = '#999';
            ctx.font = '16px Arial';
            ctx.fillText('Failed to load image', 10, 30);
        };
    }, [image, classNames]);

    return (
        <div className="border rounded-lg p-3 shadow-sm">
            <h2 className="text-lg font-semibold truncate">{image.filename}</h2>
            <p className="text-sm text-gray-600 mb-2">Split: {image.split}</p>
            <div className="overflow-auto border rounded bg-gray-50">
                <canvas
                    ref={canvasRef}
                    className="w-full"
                    style={{ maxHeight: '500px', minHeight: '200px' }}
                />
            </div>
            {image.annotations.length === 0 && (
                <p className="text-gray-500 text-sm mt-1">No annotations</p>
            )}
        </div>
    );
}
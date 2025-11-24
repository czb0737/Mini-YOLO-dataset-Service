// frontend/pages/upload.tsx
import { useState, useCallback, useRef } from 'react';
import OSS from 'ali-oss';

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const fileRef = useRef<File | null>(null); // 用于 refreshSTSToken 内部访问

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0] || null;
    setFile(selectedFile);
    fileRef.current = selectedFile;
  };

  const handleUpload = async () => {
    const currentFile = fileRef.current;
    if (!currentFile) return;

    setUploading(true);
    setProgress(0);

    try {
      // Step 1: 获取 OSS 临时凭证（注意：这里直连后端）
      const authRes = await fetch('http://localhost:8000/api/oss/auth', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          filename: currentFile.name,
          size: currentFile.size,
        }),
      });

      // 调试：检查原始响应
      const rawText = await authRes.text();
      let authData;
      try {
        authData = JSON.parse(rawText);
      } catch (e) {
        console.error('Failed to parse auth response:', rawText);
        throw new Error('Invalid response from auth endpoint');
      }

      if (!authData.credentials) {
        throw new Error('No credentials in response: ' + JSON.stringify(authData));
      }

      const { credentials, objectKey } = authData;

      // Step 2: 初始化 OSS 客户端（含自动 Token 刷新）
      const client = new OSS({
        region: process.env.NEXT_PUBLIC_OSS_REGION!,
        accessKeyId: credentials.AccessKeyId,
        accessKeySecret: credentials.AccessKeySecret,
        stsToken: credentials.SecurityToken,
        bucket: process.env.NEXT_PUBLIC_OSS_BUCKET!,

        // 自动刷新 STS Token（用于大文件长时间上传）
        async refreshSTSToken() {
          const f = fileRef.current;
          if (!f) throw new Error('File lost during upload');
          const res = await fetch('http://localhost:8000/api/oss/auth', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename: f.name, size: f.size }),
          });
          const data = await res.json();
          if (!data.credentials) {
            throw new Error('Failed to refresh STS token');
          }
          return {
            accessKeyId: data.credentials.AccessKeyId,
            accessKeySecret: data.credentials.AccessKeySecret,
            stsToken: data.credentials.SecurityToken,
          };
        },
        refreshSTSTokenInterval: 840000, // 14 分钟（STS 默认 15 分钟过期）
      });

      // Step 3: 执行分片上传
      await client.multipartUpload(objectKey, currentFile, {
        progress: (p) => setProgress(Math.round(p * 100)),
      });

      // Step 4: 通知后端上传完成（可选，云上用 OSS 事件触发）
      await fetch('http://localhost:8000/api/upload/complete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ objectKey, filename: currentFile.name }),
      });

      alert('✅ Upload completed! Processing started.');
    } catch (err: any) {
      console.error('Upload failed:', err);
      alert(`❌ Upload failed: ${err.message || err}`);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div style={{ padding: '2rem', maxWidth: '600px', margin: '0 auto' }}>
      <h1>Upload YOLO Dataset</h1>
      <input
        type="file"
        accept=".zip,.tar,.tar.gz"
        onChange={handleFileChange}
        disabled={uploading}
      />
      {file && (
        <p>
          Selected: {file.name} ({(file.size / 1e6).toFixed(2)} MB)
        </p>
      )}
      {uploading && <p>Uploading... {progress}%</p>}
      <button onClick={handleUpload} disabled={!file || uploading}>
        {uploading ? 'Uploading...' : 'Start Upload'}
      </button>
    </div>
  );
}
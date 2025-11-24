// frontend/pages/datasets.tsx
import { useEffect, useState } from 'react';
import Link from 'next/link';

// Type definitions (consistent with backend DatasetModel)
type Dataset = {
  id?: string;     // Pydantic alias _id -> id
  _id?: string;    // Original MongoDB _id (compatibility)
  name: string;
  status: string;
};

export default function DatasetsListPage() {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchDatasets = async () => {
      try {
        // Call FastAPI backend (CORS must be configured)
        const res = await fetch('http://localhost:8000/api/datasets');
        if (!res.ok) throw new Error('Failed to fetch datasets');
        const data = await res.json();
        setDatasets(data);
      } catch (err: any) {
        console.error('Fetch error:', err);
        setError(err.message || 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    fetchDatasets();
  }, []);

  if (loading) return <div className="p-4">Loading datasets...</div>;
  if (error) return <div className="p-4 text-red-500">Error: {error}</div>;

  return (
    <div className="p-4 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">My Datasets</h1>
      {datasets.length === 0 ? (
        <p className="text-gray-500">No datasets uploaded yet.</p>
      ) : (
        <ul className="space-y-4">
          {datasets.map((ds) => {
            const id = ds.id || ds._id; // Compatible with both field names
            return (
              <li
                key={id}
                className="border rounded-lg p-4 hover:shadow-md transition"
              >
                <Link href={`/datasets/${id}`} className="block">
                  <h2 className="text-xl font-semibold text-blue-600 hover:underline">
                    {ds.name}
                  </h2>
                  <p className="text-gray-600">Status: <span className="font-mono">{ds.status}</span></p>
                </Link>
              </li>
            );
          })}
        </ul>
      )}
      <div className="mt-6">
        <Link href="/upload" className="text-blue-500 hover:underline">
          ← Back to Upload
        </Link>
      </div>
    </div>
  );
}
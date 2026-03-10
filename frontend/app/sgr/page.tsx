"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { listSgr } from "@/lib/api";

interface SgrItem {
  id: string;
  numb_doc: string;
  date_doc?: string;
  name_prod?: string;
  firmget_name?: string;
  status?: string;
  created_at: string;
}

export default function SgrListPage() {
  const [items, setItems] = useState<SgrItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listSgr()
      .then((data) => setItems(data.items))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b">
        <div className="max-w-4xl mx-auto px-4 py-6 flex items-center justify-between">
          <div>
            <Link href="/" className="text-2xl font-bold hover:underline">
              LabelCheck
            </Link>
            <p className="text-gray-500 text-sm mt-1">База СГР</p>
          </div>
          <Link
            href="/"
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700"
          >
            Загрузить СГР
          </Link>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-8">
        {loading && <p className="text-gray-500 text-center py-12">Загрузка...</p>}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
            {error}
          </div>
        )}

        {!loading && items.length === 0 && !error && (
          <div className="text-center py-12 text-gray-400">
            <p className="text-4xl mb-4">📋</p>
            <p>Нет загруженных СГР</p>
            <Link href="/" className="text-blue-600 hover:underline text-sm mt-2 inline-block">
              Загрузить первый СГР
            </Link>
          </div>
        )}

        {items.length > 0 && (
          <div className="space-y-3">
            {items.map((sgr) => (
              <Link
                key={sgr.id}
                href={`/sgr/${sgr.id}`}
                className="block bg-white border rounded-lg p-4 hover:border-blue-300 transition-colors"
              >
                <div className="flex justify-between items-start">
                  <div>
                    <div className="font-mono text-sm font-medium">{sgr.numb_doc}</div>
                    <div className="text-sm text-gray-600 mt-1">
                      {sgr.name_prod || "Продукция не указана"}
                    </div>
                    <div className="text-xs text-gray-400 mt-1">
                      {sgr.firmget_name}
                    </div>
                  </div>
                  <div className="text-right">
                    <span
                      className={`text-xs px-2 py-1 rounded-full ${
                        sgr.status === "подписан и действует"
                          ? "bg-green-100 text-green-700"
                          : "bg-red-100 text-red-700"
                      }`}
                    >
                      {sgr.status || "н/д"}
                    </span>
                    {sgr.date_doc && (
                      <div className="text-xs text-gray-400 mt-2">{sgr.date_doc}</div>
                    )}
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { listReports, deleteReport } from "@/lib/api";

interface ReportItem {
  id: string;
  overall_status: string;
  score: number;
  created_at: string;
  sgr_record_id?: string;
}

const STATUS_LABEL: Record<string, { text: string; color: string }> = {
  pass: { text: "Соответствует", color: "bg-green-100 text-green-700" },
  fail: { text: "Не соответствует", color: "bg-red-100 text-red-700" },
  warning: { text: "Замечания", color: "bg-yellow-100 text-yellow-700" },
};

export default function ReportsListPage() {
  const [items, setItems] = useState<ReportItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listReports()
      .then((data) => setItems(data.items))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!confirm("Удалить этот отчёт?")) return;
    try {
      await deleteReport(id);
      setItems((prev) => prev.filter((r) => r.id !== id));
    } catch (err: any) {
      alert(err.message);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b">
        <div className="max-w-4xl mx-auto px-4 py-6 flex items-center justify-between">
          <div>
            <Link href="/" className="text-2xl font-bold hover:underline">
              LabelCheck
            </Link>
            <p className="text-gray-500 text-sm mt-1">История проверок</p>
          </div>
          <Link
            href="/"
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700"
          >
            Проверить этикетку
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
            <p className="text-4xl mb-4">📊</p>
            <p>Нет отчётов о проверке</p>
            <Link href="/" className="text-blue-600 hover:underline text-sm mt-2 inline-block">
              Проверить первую этикетку
            </Link>
          </div>
        )}

        {items.length > 0 && (
          <div className="space-y-3">
            {items.map((report) => {
              const st = STATUS_LABEL[report.overall_status] || STATUS_LABEL.warning;
              return (
                <Link
                  key={report.id}
                  href={`/reports/${report.id}`}
                  className="block bg-white border rounded-lg p-4 hover:border-blue-300 transition-colors"
                >
                  <div className="flex justify-between items-center">
                    <div className="flex items-center gap-4">
                      <div className="text-2xl font-bold">{report.score}/100</div>
                      <span className={`text-xs px-2 py-1 rounded-full ${st.color}`}>
                        {st.text}
                      </span>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="text-xs text-gray-400">
                        {new Date(report.created_at).toLocaleString("ru-RU")}
                      </div>
                      <button
                        onClick={(e) => handleDelete(report.id, e)}
                        className="text-gray-400 hover:text-red-600 text-sm px-2 py-1 rounded hover:bg-red-50 transition-colors"
                        title="Удалить отчёт"
                      >
                        ✕
                      </button>
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </main>
    </div>
  );
}

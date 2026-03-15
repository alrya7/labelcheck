"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { getReport } from "@/lib/api";
import VerificationReport from "@/components/VerificationReport";
import LabelImageViewer from "@/components/LabelImageViewer";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "https://labelcheck-api.onrender.com/api/v1";
const BACKEND_ORIGIN = API_BASE.replace(/\/api\/v1\/?$/, "");

interface ReportDetail {
  id: string;
  name?: string;
  overall_status: string;
  score: number;
  checks: any[];
  spelling_errors?: any[];
  therapeutic_claims?: any[];
  pictograms?: any;
  ai_analysis?: string;
  extracted_label_text?: string;
  label_file_url?: string | null;
  created_at: string;
}

export default function ReportDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [report, setReport] = useState<ReportDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    getReport(id)
      .then(setReport)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  const labelImageUrl = report?.id
    ? `${API_BASE}/reports/${report.id}/image`
    : null;

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b">
        <div className="max-w-6xl mx-auto px-4 py-6">
          <Link href="/reports" className="text-sm text-blue-600 hover:underline">
            &larr; Все отчёты
          </Link>
          <h1 className="text-2xl font-bold mt-2">
            {report?.name || "Отчёт о проверке"}
          </h1>
          {report && (
            <p className="text-gray-500 text-sm mt-1">
              {new Date(report.created_at).toLocaleString("ru-RU")}
            </p>
          )}
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-8">
        {loading && <p className="text-gray-500 text-center py-12">Загрузка...</p>}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
            {error}
          </div>
        )}

        {report && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Left: label image */}
            <div className="space-y-6">
              {labelImageUrl && <LabelImageViewer src={labelImageUrl} />}

              {report.extracted_label_text && (
                <div className="bg-white border rounded-lg p-6">
                  <h3 className="font-semibold mb-3">Извлечённый текст этикетки</h3>
                  <pre className="text-sm bg-gray-50 rounded p-4 whitespace-pre-wrap max-h-96 overflow-y-auto">
                    {report.extracted_label_text}
                  </pre>
                </div>
              )}
            </div>

            {/* Right: checks */}
            <div>
              <VerificationReport
                score={report.score}
                overallStatus={report.overall_status}
                checks={report.checks}
                spellingErrors={report.spelling_errors}
                therapeuticClaims={report.therapeutic_claims}
                pictograms={report.pictograms}
                hideNotApplicable={true}
              />
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

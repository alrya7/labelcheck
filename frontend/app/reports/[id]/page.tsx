"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { getReport } from "@/lib/api";
import VerificationReport from "@/components/VerificationReport";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
const BACKEND_ORIGIN = API_BASE.replace(/\/api\/v1\/?$/, "");

interface ReportDetail {
  id: string;
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

function LabelImageViewer({ src }: { src: string }) {
  const [scale, setScale] = useState(1);
  const [dragging, setDragging] = useState(false);
  const [pos, setPos] = useState({ x: 0, y: 0 });
  const dragStart = useRef({ x: 0, y: 0 });
  const posStart = useRef({ x: 0, y: 0 });
  const containerRef = useRef<HTMLDivElement>(null);

  const handleWheel = useCallback((e: WheelEvent) => {
    e.preventDefault();
    setScale((s) => Math.max(0.5, Math.min(5, s - e.deltaY * 0.002)));
  }, []);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    el.addEventListener("wheel", handleWheel, { passive: false });
    return () => el.removeEventListener("wheel", handleWheel);
  }, [handleWheel]);

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      if (scale <= 1) return;
      setDragging(true);
      dragStart.current = { x: e.clientX, y: e.clientY };
      posStart.current = { ...pos };
    },
    [scale, pos]
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (!dragging) return;
      setPos({
        x: posStart.current.x + e.clientX - dragStart.current.x,
        y: posStart.current.y + e.clientY - dragStart.current.y,
      });
    },
    [dragging]
  );

  const handleMouseUp = useCallback(() => setDragging(false), []);

  const resetView = useCallback(() => {
    setScale(1);
    setPos({ x: 0, y: 0 });
  }, []);

  return (
    <div className="border rounded-lg overflow-hidden bg-white">
      <div className="bg-gray-50 px-4 py-3 flex justify-between items-center">
        <h3 className="font-semibold">Макет этикетки</h3>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setScale((s) => Math.max(0.5, s - 0.25))}
            className="px-2 py-1 text-sm bg-gray-200 rounded hover:bg-gray-300"
          >
            -
          </button>
          <span className="text-sm text-gray-600 w-14 text-center">
            {Math.round(scale * 100)}%
          </span>
          <button
            onClick={() => setScale((s) => Math.min(5, s + 0.25))}
            className="px-2 py-1 text-sm bg-gray-200 rounded hover:bg-gray-300"
          >
            +
          </button>
          <button
            onClick={resetView}
            className="px-2 py-1 text-sm bg-gray-200 rounded hover:bg-gray-300"
          >
            Сброс
          </button>
        </div>
      </div>
      <div
        ref={containerRef}
        className="relative overflow-hidden bg-gray-100 flex items-center justify-center"
        style={{ height: "600px", cursor: scale > 1 ? (dragging ? "grabbing" : "grab") : "default" }}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        <img
          src={src}
          alt="Этикетка"
          draggable={false}
          className="select-none max-w-full max-h-full"
          style={{
            transform: `translate(${pos.x}px, ${pos.y}px) scale(${scale})`,
            transformOrigin: "center center",
            objectFit: "contain",
          }}
        />
      </div>
      <div className="bg-gray-50 px-4 py-2 text-xs text-gray-500 text-center">
        Колёсико мыши — масштаб. Перетаскивание при увеличении.
      </div>
    </div>
  );
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

  const labelImageUrl = report?.label_file_url
    ? `${BACKEND_ORIGIN}${report.label_file_url}`
    : null;

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b">
        <div className="max-w-6xl mx-auto px-4 py-6">
          <Link href="/reports" className="text-sm text-blue-600 hover:underline">
            &larr; Все отчёты
          </Link>
          <h1 className="text-2xl font-bold mt-2">Отчёт о проверке</h1>
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

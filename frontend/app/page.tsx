"use client";

import { useState } from "react";
import Link from "next/link";
import FileUpload from "@/components/FileUpload";
import VerificationReport from "@/components/VerificationReport";
import { checkLabel, uploadSgr } from "@/lib/api";

type Tab = "check" | "sgr";

export default function Home() {
  const [tab, setTab] = useState<Tab>("check");
  const [loading, setLoading] = useState(false);
  const [report, setReport] = useState<any>(null);
  const [sgrResult, setSgrResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  const handleCheckLabel = async (file: File) => {
    setLoading(true);
    setError(null);
    setReport(null);
    try {
      const result = await checkLabel(file);
      setReport(result);
    } catch (e: any) {
      if (e.name === "AbortError") {
        setError("Превышено время ожидания (5 мин). Попробуйте загрузить изображение вместо PDF или PDF с меньшим числом страниц.");
      } else if (e.message === "Failed to fetch") {
        setError("Не удалось подключиться к серверу. Убедитесь что бэкенд запущен на localhost:8000");
      } else {
        setError(e.message);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleUploadSgr = async (file: File) => {
    setLoading(true);
    setError(null);
    setSgrResult(null);
    try {
      const result = await uploadSgr(file);
      setSgrResult(result);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b">
        <div className="max-w-4xl mx-auto px-4 py-6 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">LabelCheck</h1>
            <p className="text-gray-500 text-sm mt-1">
              Проверка этикеток БАД на соответствие ТР ТС 022/2011, ТР ТС 021/2011, СанПиН
            </p>
          </div>
          <nav className="flex gap-4 text-sm">
            <Link href="/sgr" className="text-gray-600 hover:text-blue-600">
              База СГР
            </Link>
            <Link href="/reports" className="text-gray-600 hover:text-blue-600">
              Отчёты
            </Link>
          </nav>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-8">
        {/* Tabs */}
        <div className="flex gap-2 mb-6">
          <button
            onClick={() => { setTab("check"); setReport(null); setError(null); }}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              tab === "check"
                ? "bg-blue-600 text-white"
                : "bg-white text-gray-600 hover:bg-gray-100"
            }`}
          >
            🏷 Проверить этикетку
          </button>
          <button
            onClick={() => { setTab("sgr"); setSgrResult(null); setError(null); }}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              tab === "sgr"
                ? "bg-blue-600 text-white"
                : "bg-white text-gray-600 hover:bg-gray-100"
            }`}
          >
            📄 Загрузить СГР
          </button>
        </div>

        {/* Upload */}
        {tab === "check" && (
          <div className="space-y-6">
            <FileUpload
              onFileSelect={handleCheckLabel}
              label="Загрузите макет этикетки"
              description="PDF или изображение (JPG, PNG). Макет будет проанализирован на соответствие требованиям."
              loading={loading}
            />

            {error && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
                {error}
              </div>
            )}

            {report && (
              <VerificationReport
                score={report.score}
                overallStatus={report.overall_status}
                checks={report.checks}
                spellingErrors={report.spelling_errors}
                therapeuticClaims={report.therapeutic_claims}
                pictograms={report.pictograms}
              />
            )}
          </div>
        )}

        {tab === "sgr" && (
          <div className="space-y-6">
            <FileUpload
              onFileSelect={handleUploadSgr}
              label="Загрузите СГР"
              description="PDF свидетельства о государственной регистрации. Данные будут извлечены и сохранены."
              loading={loading}
            />

            {error && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
                {error}
              </div>
            )}

            {sgrResult && (
              <div className="bg-white border rounded-lg p-6 space-y-4">
                <div className="flex items-center gap-2">
                  <span className="text-2xl">✅</span>
                  <h2 className="text-lg font-semibold">{sgrResult.message}</h2>
                </div>

                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-500">Номер:</span>
                    <p className="font-mono">{sgrResult.sgr.numb_doc}</p>
                  </div>
                  <div>
                    <span className="text-gray-500">Дата:</span>
                    <p>{sgrResult.sgr.date_doc}</p>
                  </div>
                  <div className="col-span-2">
                    <span className="text-gray-500">Продукция:</span>
                    <p>{sgrResult.sgr.name_prod}</p>
                  </div>
                  <div>
                    <span className="text-gray-500">Изготовитель:</span>
                    <p>{sgrResult.sgr.firmget_name}</p>
                  </div>
                  <div>
                    <span className="text-gray-500">Статус:</span>
                    <p className={
                      sgrResult.sgr.status === "подписан и действует"
                        ? "text-green-600 font-medium"
                        : "text-red-600 font-medium"
                    }>
                      {sgrResult.sgr.status || "н/д"}
                    </p>
                  </div>
                </div>

                {sgrResult.registry_discrepancies?.length > 0 && (
                  <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                    <h3 className="font-semibold text-yellow-700 mb-2">
                      ⚠️ Расхождения с реестром ЕАЭС
                    </h3>
                    {sgrResult.registry_discrepancies.map((d: any, i: number) => (
                      <div key={i} className="text-sm mb-1">
                        <span className="font-medium">{d.field}:</span>{" "}
                        {d.details || `Извлечено: "${d.extracted}", В реестре: "${d.registry}"`}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </main>

      <footer className="border-t bg-white mt-12">
        <div className="max-w-4xl mx-auto px-4 py-4 text-center text-xs text-gray-400">
          LabelCheck v0.1 | ТР ТС 022/2011 | ТР ТС 021/2011 | СанПиН 2.3.2.1290-03 | API реестра nsi.eaeunion.org
        </div>
      </footer>
    </div>
  );
}

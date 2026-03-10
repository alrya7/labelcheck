"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { getSgr } from "@/lib/api";

interface SgrDetail {
  id: string;
  numb_doc: string;
  date_doc?: string;
  status?: string;
  name_prod?: string;
  prod_app?: string;
  firmget_name?: string;
  firmget_addr?: string;
  firmget_inn?: string;
  firmget_country?: string;
  firmmade_name?: string;
  firmmade_addr?: string;
  firmmade_country?: string;
  doc_norm?: string;
  doc_usearea?: string;
  doc_condition?: string;
  doc_label?: string;
  created_at: string;
}

export default function SgrDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [sgr, setSgr] = useState<SgrDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    getSgr(id)
      .then(setSgr)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  const Field = ({ label, value }: { label: string; value?: string | null }) => {
    if (!value) return null;
    return (
      <div>
        <span className="text-gray-500 text-sm">{label}</span>
        <p className="mt-0.5">{value}</p>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b">
        <div className="max-w-4xl mx-auto px-4 py-6">
          <Link href="/sgr" className="text-sm text-blue-600 hover:underline">
            &larr; Все СГР
          </Link>
          <h1 className="text-2xl font-bold mt-2">
            {sgr?.numb_doc || "Загрузка..."}
          </h1>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-8">
        {loading && <p className="text-gray-500 text-center py-12">Загрузка...</p>}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
            {error}
          </div>
        )}

        {sgr && (
          <div className="space-y-6">
            {/* Status badge */}
            <div className="flex items-center gap-3">
              <span
                className={`px-3 py-1 rounded-full text-sm font-medium ${
                  sgr.status === "подписан и действует"
                    ? "bg-green-100 text-green-700"
                    : "bg-red-100 text-red-700"
                }`}
              >
                {sgr.status || "Статус неизвестен"}
              </span>
              {sgr.date_doc && (
                <span className="text-sm text-gray-500">от {sgr.date_doc}</span>
              )}
            </div>

            {/* Product info */}
            <div className="bg-white border rounded-lg p-6 space-y-4">
              <h2 className="font-semibold text-lg">Продукция</h2>
              <Field label="Наименование" value={sgr.name_prod} />
              <Field label="Описание / применение" value={sgr.prod_app} />
              <Field label="Область применения" value={sgr.doc_usearea} />
            </div>

            {/* Applicant */}
            <div className="bg-white border rounded-lg p-6 space-y-4">
              <h2 className="font-semibold text-lg">Заявитель</h2>
              <Field label="Название" value={sgr.firmget_name} />
              <Field label="Адрес" value={sgr.firmget_addr} />
              <Field label="ИНН" value={sgr.firmget_inn} />
              <Field label="Страна" value={sgr.firmget_country} />
            </div>

            {/* Manufacturer */}
            <div className="bg-white border rounded-lg p-6 space-y-4">
              <h2 className="font-semibold text-lg">Изготовитель</h2>
              <Field label="Название" value={sgr.firmmade_name} />
              <Field label="Адрес" value={sgr.firmmade_addr} />
              <Field label="Страна" value={sgr.firmmade_country} />
            </div>

            {/* Documents */}
            <div className="bg-white border rounded-lg p-6 space-y-4">
              <h2 className="font-semibold text-lg">Документация</h2>
              <Field label="Нормативный документ" value={sgr.doc_norm} />
              <Field label="Условия хранения" value={sgr.doc_condition} />
              {sgr.doc_label && (
                <div>
                  <span className="text-gray-500 text-sm">Текст этикетки (из СГР)</span>
                  <pre className="mt-1 text-sm bg-gray-50 rounded p-3 whitespace-pre-wrap">
                    {sgr.doc_label}
                  </pre>
                </div>
              )}
            </div>

            <div className="text-xs text-gray-400">
              Загружен: {new Date(sgr.created_at).toLocaleString("ru-RU")}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

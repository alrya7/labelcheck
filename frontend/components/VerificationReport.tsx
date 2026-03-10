"use client";

interface Check {
  id: string;
  name: string;
  category: string;
  source?: string;
  required: boolean;
  status: string;
  details?: string;
  found_text?: string | null;
}

interface ReportProps {
  score: number;
  overallStatus: string;
  checks: Check[];
  spellingErrors?: { word: string; suggestion: string; context?: string }[];
  therapeuticClaims?: { text: string; reason: string }[];
  pictograms?: {
    eac?: boolean;
    mobius_loop?: boolean;
    barcode?: boolean;
    datamatrix?: boolean;
    glass_fork?: boolean;
  };
}

const STATUS_CONFIG: Record<string, { emoji: string; color: string; bg: string }> = {
  pass: { emoji: "✅", color: "text-green-700", bg: "bg-green-50" },
  fail: { emoji: "❌", color: "text-red-700", bg: "bg-red-50" },
  warning: { emoji: "⚠️", color: "text-yellow-700", bg: "bg-yellow-50" },
  not_applicable: { emoji: "➖", color: "text-gray-500", bg: "bg-gray-50" },
};

const CATEGORIES: Record<string, string> = {
  text: "Обязательные текстовые поля",
  pictogram: "Пиктограммы и знаки",
  prohibited: "Запрещённые элементы",
  registry: "Сверка с реестром ЕАЭС",
  quality: "Качество оформления",
};

export default function VerificationReport({
  score,
  overallStatus,
  checks,
  spellingErrors = [],
  therapeuticClaims = [],
}: ReportProps) {
  const overall = STATUS_CONFIG[overallStatus] || STATUS_CONFIG.warning;

  return (
    <div className="space-y-6">
      {/* Score header */}
      <div className={`${overall.bg} rounded-lg p-6 text-center`}>
        <div className="text-5xl font-bold mb-2">{score}/100</div>
        <div className={`text-lg font-medium ${overall.color}`}>
          {overall.emoji}{" "}
          {overallStatus === "pass"
            ? "Соответствует требованиям"
            : overallStatus === "warning"
            ? "Есть замечания"
            : "Не соответствует требованиям"}
        </div>
      </div>

      {/* Checks by category */}
      {Object.entries(CATEGORIES).map(([catId, catName]) => {
        const catChecks = checks.filter((c) => c.category === catId);
        if (catChecks.length === 0) return null;

        const passed = catChecks.filter((c) => c.status === "pass").length;
        const total = catChecks.filter((c) => c.status !== "not_applicable").length;

        return (
          <div key={catId} className="border rounded-lg overflow-hidden">
            <div className="bg-gray-50 px-4 py-3 flex justify-between items-center">
              <h3 className="font-semibold">{catName}</h3>
              <span className="text-sm text-gray-500">
                {passed}/{total}
              </span>
            </div>
            <div className="divide-y">
              {catChecks.map((check) => {
                const cfg = STATUS_CONFIG[check.status] || STATUS_CONFIG.warning;
                return (
                  <div
                    key={check.id}
                    className={`px-4 py-3 ${cfg.bg} bg-opacity-30`}
                  >
                    <div className="flex items-start gap-2">
                      <span className="mt-0.5">{cfg.emoji}</span>
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-sm">{check.name}</div>
                        {check.details && check.status !== "pass" && (
                          <div className={`text-xs mt-1 ${cfg.color}`}>
                            {check.details}
                          </div>
                        )}
                        {check.source && (
                          <div className="text-xs text-gray-400 mt-1">
                            {check.source}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}

      {/* Therapeutic claims */}
      {therapeuticClaims.length > 0 && (
        <div className="border border-red-300 rounded-lg overflow-hidden">
          <div className="bg-red-50 px-4 py-3">
            <h3 className="font-semibold text-red-700">
              🚨 Обнаружены лечебные заявления
            </h3>
          </div>
          <div className="divide-y">
            {therapeuticClaims.map((claim, i) => (
              <div key={i} className="px-4 py-3">
                <div className="font-medium text-sm text-red-700">
                  &laquo;{claim.text}&raquo;
                </div>
                <div className="text-xs text-red-500 mt-1">{claim.reason}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Spelling errors */}
      {spellingErrors.length > 0 && (
        <div className="border border-yellow-300 rounded-lg overflow-hidden">
          <div className="bg-yellow-50 px-4 py-3">
            <h3 className="font-semibold text-yellow-700">
              📝 Орфографические ошибки
            </h3>
          </div>
          <div className="divide-y">
            {spellingErrors.map((err, i) => (
              <div key={i} className="px-4 py-3 text-sm">
                <span className="text-red-600 line-through">{err.word}</span>
                {" → "}
                <span className="text-green-600 font-medium">
                  {err.suggestion}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

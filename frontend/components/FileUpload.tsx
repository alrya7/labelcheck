"use client";

import { useCallback, useEffect, useState } from "react";

interface FileUploadProps {
  onFileSelect: (file: File) => void;
  accept?: string;
  label?: string;
  description?: string;
  loading?: boolean;
  loadingMessage?: string;
}

const LOADING_STEPS = [
  { time: 0, text: "Загрузка файла..." },
  { time: 2, text: "Конвертация PDF в изображения..." },
  { time: 5, text: "AI анализирует этикетку..." },
  { time: 15, text: "AI распознаёт текст и пиктограммы..." },
  { time: 30, text: "AI проверяет обязательные поля..." },
  { time: 50, text: "Проверка номера СГР в реестре ЕАЭС..." },
  { time: 60, text: "Формирование отчёта..." },
  { time: 90, text: "Почти готово, ждём ответ от AI..." },
];

export default function FileUpload({
  onFileSelect,
  accept = ".pdf,.png,.jpg,.jpeg,.webp",
  label = "Загрузить файл",
  description = "PDF или изображение",
  loading = false,
  loadingMessage,
}: FileUploadProps) {
  const [dragActive, setDragActive] = useState(false);
  const [fileName, setFileName] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const [stepText, setStepText] = useState(LOADING_STEPS[0].text);

  useEffect(() => {
    if (!loading) {
      setElapsed(0);
      setStepText(LOADING_STEPS[0].text);
      return;
    }
    const start = Date.now();
    const interval = setInterval(() => {
      const sec = Math.floor((Date.now() - start) / 1000);
      setElapsed(sec);
      const step = [...LOADING_STEPS].reverse().find((s) => sec >= s.time);
      if (step) setStepText(step.text);
    }, 1000);
    return () => clearInterval(interval);
  }, [loading]);

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setDragActive(false);
      if (e.dataTransfer.files?.[0]) {
        const file = e.dataTransfer.files[0];
        setFileName(file.name);
        onFileSelect(file);
      }
    },
    [onFileSelect]
  );

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files?.[0]) {
        const file = e.target.files[0];
        setFileName(file.name);
        onFileSelect(file);
      }
    },
    [onFileSelect]
  );

  return (
    <div
      className={`relative border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
        dragActive
          ? "border-blue-500 bg-blue-50"
          : "border-gray-300 hover:border-gray-400"
      } ${loading ? "opacity-50 pointer-events-none" : ""}`}
      onDragEnter={handleDrag}
      onDragLeave={handleDrag}
      onDragOver={handleDrag}
      onDrop={handleDrop}
    >
      <input
        type="file"
        accept={accept}
        onChange={handleChange}
        className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
        disabled={loading}
      />
      <div className="space-y-2">
        {loading ? (
          <>
            <div className="flex justify-center">
              <div className="w-8 h-8 border-3 border-blue-600 border-t-transparent rounded-full animate-spin" />
            </div>
            <p className="text-lg font-medium text-blue-700">
              {loadingMessage || stepText}
            </p>
            <p className="text-sm text-gray-500 font-mono">{elapsed} сек</p>
            <div className="w-48 mx-auto bg-gray-200 rounded-full h-1.5 mt-2">
              <div
                className="bg-blue-600 h-1.5 rounded-full transition-all duration-1000"
                style={{ width: `${Math.min((elapsed / 90) * 100, 95)}%` }}
              />
            </div>
          </>
        ) : (
          <>
            <div className="text-4xl">{fileName ? "📄" : "📁"}</div>
            <p className="text-lg font-medium">{fileName || label}</p>
            <p className="text-sm text-gray-500">{description}</p>
          </>
        )}
      </div>
    </div>
  );
}

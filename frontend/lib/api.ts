const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

function fetchWithTimeout(url: string, options: RequestInit = {}, timeoutMs = 300000): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  return fetch(url, { ...options, signal: controller.signal }).finally(() => clearTimeout(timer));
}

export async function uploadSgr(file: File) {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetchWithTimeout(`${API_BASE}/sgr/upload`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || "Ошибка загрузки СГР");
  }

  return res.json();
}

export async function listSgr(offset = 0, limit = 50) {
  const res = await fetch(`${API_BASE}/sgr?offset=${offset}&limit=${limit}`);
  if (!res.ok) throw new Error("Ошибка загрузки списка СГР");
  return res.json();
}

export async function getSgr(id: string) {
  const res = await fetch(`${API_BASE}/sgr/${id}`);
  if (!res.ok) throw new Error("СГР не найден");
  return res.json();
}

export async function checkLabel(file: File, sgrRecordId?: string) {
  const formData = new FormData();
  formData.append("file", file);
  if (sgrRecordId) {
    formData.append("sgr_record_id", sgrRecordId);
  }

  const res = await fetchWithTimeout(`${API_BASE}/label/check`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || "Ошибка проверки этикетки");
  }

  return res.json();
}

export async function listReports(offset = 0, limit = 50) {
  const res = await fetch(`${API_BASE}/reports?offset=${offset}&limit=${limit}`);
  if (!res.ok) throw new Error("Ошибка загрузки отчётов");
  return res.json();
}

export async function getReport(id: string) {
  const res = await fetch(`${API_BASE}/reports/${id}`);
  if (!res.ok) throw new Error("Отчёт не найден");
  return res.json();
}

export async function deleteReport(id: string) {
  const res = await fetch(`${API_BASE}/reports/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Ошибка удаления отчёта");
  return res.json();
}

export async function searchRegistry(params: {
  numb_doc?: string;
  manufacturer?: string;
  product?: string;
}) {
  const query = new URLSearchParams(
    Object.entries(params).filter(([, v]) => v) as [string, string][]
  ).toString();
  const res = await fetch(`${API_BASE}/registry/search?${query}`);
  if (!res.ok) throw new Error("Ошибка поиска в реестре");
  return res.json();
}

// Thin fetch wrapper for the Python API (see docs/02-technical-requirements.md, section 5).
export const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE_URL}${path}`, init);
  } catch {
    throw new ApiError(0, "Cannot reach the server. Is the backend running?");
  }
  if (!res.ok) {
    let message = res.statusText;
    try {
      const body = await res.json();
      message = body.error ?? body.detail ?? message;
    } catch {
      /* response had no JSON body */
    }
    throw new ApiError(res.status, message);
  }
  return res.json() as Promise<T>;
}

/** JSON request body helper: apiFetch(path, json("PATCH", { status })). */
export function json(method: string, body: unknown): RequestInit {
  return { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
}

export function potholeImageUrl(potholeId: number): string {
  return `${BASE_URL}/potholes/${potholeId}/image`;
}

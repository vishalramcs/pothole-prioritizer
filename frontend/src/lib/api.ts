// Thin fetch wrapper for the Python API (see docs/02-technical-requirements.md, section 5).
const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, init);
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

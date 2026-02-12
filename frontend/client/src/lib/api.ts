/**
 * API Service: Gọi Backend Credit Underwriting Agent.
 * 
 * Khi chạy local:
 *   - Frontend dev server: http://localhost:5000
 *   - Backend FastAPI: http://localhost:8000
 *   - Vite proxy /api/* → http://localhost:8000
 * 
 * Khi deploy production:
 *   - VITE_API_URL = Cloud Run backend URL (e.g. https://credit-agent-backend-xxx.run.app/api/v1)
 */

export const API_BASE = import.meta.env.VITE_API_URL || "/api/v1";

export interface AssessmentRequest {
  customer_id: string;
  loan_amount: number;
  term_months: number;
}

export interface AssessmentResponse {
  success: boolean;
  thread_id: string;
  decision: string | null;
  report: string | null;
  reasoning_trail: ReasoningStep[];
  needs_human_review: boolean;
  error: string | null;
}

export interface ReasoningStep {
  step: number;
  action: string;
  result: string;
  policy_ref?: string;
  decision: string;
  detail: string;
}

export interface ChatResponse {
  success: boolean;
  thread_id: string;
  message: string;
  error: string | null;
}

export interface CustomerSummary {
  id: number;
  full_name: string;
  credit_sco: number;
  customer_segment: string;
}

/**
 * Chạy thẩm định tín dụng đầy đủ.
 */
export async function assessCredit(data: AssessmentRequest): Promise<AssessmentResponse> {
  const res = await fetch(`${API_BASE}/assess`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });

  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }

  return res.json();
}

/**
 * Chat tự do với agent.
 */
export async function chatWithAgent(message: string, threadId?: string): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, thread_id: threadId }),
  });

  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }

  return res.json();
}

/**
 * Submit human review decision.
 */
export async function submitReview(
  threadId: string,
  decision: "APPROVED" | "REJECTED",
  note: string = ""
): Promise<AssessmentResponse> {
  const res = await fetch(`${API_BASE}/review`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      thread_id: threadId,
      decision,
      reviewer_note: note,
    }),
  });

  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }

  return res.json();
}

/**
 * Lấy danh sách khách hàng.
 */
export async function getCustomers(): Promise<{ total: number; customers: CustomerSummary[] }> {
  const res = await fetch(`${API_BASE}/customers`);
  const data = await res.json();
  return data.data;
}

/**
 * Health check.
 */
export async function healthCheck(): Promise<boolean> {
  try {
    // In production, VITE_API_URL points to Cloud Run, strip /api/v1 for /health
    const baseUrl = import.meta.env.VITE_API_URL
      ? new URL(import.meta.env.VITE_API_URL).origin
      : "";
    const res = await fetch(`${baseUrl}/health`);
    return res.ok;
  } catch {
    return false;
  }
}

import type {
  ApiErrorResponse,
  AttachmentResponse,
  CartResult,
  ChatRequest,
  ChatResponse,
} from "@/lib/types";

export class ApiClientError extends Error {
  code: string;
  retryable: boolean;
  details?: Record<string, unknown>;

  constructor(payload: ApiErrorResponse, status: number) {
    super(payload.error.message);
    this.name = "ApiClientError";
    this.code = payload.error.code || `HTTP_${status}`;
    this.retryable = payload.error.retryable;
    this.details = payload.error.details;
  }
}

async function parseResponse<T>(response: Response): Promise<T> {
  const payload = (await response.json()) as T | ApiErrorResponse;
  if (!response.ok) {
    throw new ApiClientError(payload as ApiErrorResponse, response.status);
  }
  return payload as T;
}

export function sendChat(payload: ChatRequest): Promise<ChatResponse> {
  return fetch("/api/v1/chat/messages", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  }).then((response) => parseResponse<ChatResponse>(response));
}

export function uploadAttachment(file: File): Promise<AttachmentResponse> {
  const formData = new FormData();
  formData.append("file", file);
  return fetch("/api/v1/files", { method: "POST", body: formData }).then((response) =>
    parseResponse<AttachmentResponse>(response),
  );
}

export function confirmCart(
  proposalId: string,
  conversationId: string,
  idempotencyKey: string,
): Promise<CartResult> {
  return fetch(`/api/v1/cart/proposals/${proposalId}/confirm`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Idempotency-Key": idempotencyKey,
    },
    body: JSON.stringify({ conversation_id: conversationId }),
  }).then((response) => parseResponse<CartResult>(response));
}

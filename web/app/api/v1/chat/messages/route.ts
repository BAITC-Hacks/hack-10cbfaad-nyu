import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { randomUUID } from "node:crypto";
import { mockChatResponse } from "@/lib/server/mock-ai";
import { saveProposal } from "@/lib/server/proposals";
import { internalHeaders, requestId } from "@/lib/server/request";
import { aiServiceUrl, isRealAiMode } from "@/lib/server/ai-service";
import type { ChatRequest, ChatResponse } from "@/lib/types";

class AiServiceError extends Error {
  constructor(
    public readonly code: "LLM_UNAVAILABLE" | "LLM_TIMEOUT",
    message: string,
    public readonly status: 503 | 504,
    public readonly details: Record<string, unknown> = {},
  ) {
    super(message);
    this.name = "AiServiceError";
  }
}

function sessionId(): string {
  return cookies().get("ekt_session_id")?.value || randomUUID();
}

function isChatRequest(value: unknown): value is ChatRequest {
  if (!value || typeof value !== "object") return false;
  const candidate = value as Partial<ChatRequest>;
  return (
    (candidate.conversation_id === null || typeof candidate.conversation_id === "string") &&
    typeof candidate.message === "string" &&
    Array.isArray(candidate.attachment_ids) &&
    candidate.attachment_ids.every((id) => typeof id === "string") &&
    candidate.locale === "ru-RU"
  );
}

async function callAiService(payload: ChatRequest, id: string): Promise<ChatResponse> {
  if (!isRealAiMode()) return mockChatResponse(payload);

  const baseUrl = aiServiceUrl();
  if (!baseUrl) {
    throw new AiServiceError("LLM_UNAVAILABLE", "AI Service не настроен", 503);
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 30_000);

  try {
    let response: Response;
    try {
      response = await fetch(`${baseUrl}/internal/v1/chat/messages`, {
        method: "POST",
        headers: { ...internalHeaders(id), "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        cache: "no-store",
        signal: controller.signal,
      });
    } catch (error) {
      if (error instanceof Error && error.name === "AbortError") {
        throw new AiServiceError("LLM_TIMEOUT", "Сервис консультации не ответил вовремя. Попробуйте повторить запрос.", 504);
      }
      throw new AiServiceError("LLM_UNAVAILABLE", "Сервис консультации временно недоступен. Попробуйте повторить запрос.", 503);
    }

    if (!response.ok) {
      let upstream: unknown;
      try {
        upstream = await response.json();
      } catch {
        upstream = null;
      }

      const error = upstream && typeof upstream === "object" && "error" in upstream
        ? (upstream as { error?: Record<string, unknown> }).error
        : undefined;
      const code = error?.code === "LLM_TIMEOUT" || response.status === 504 ? "LLM_TIMEOUT" : "LLM_UNAVAILABLE";
      const status = code === "LLM_TIMEOUT" ? 504 : 503;
      const message = typeof error?.message === "string"
        ? error.message
        : code === "LLM_TIMEOUT"
          ? "Сервис консультации не ответил вовремя. Попробуйте повторить запрос."
          : "Сервис консультации временно недоступен. Попробуйте повторить запрос.";
      throw new AiServiceError(code, message, status, {
        ...(error?.details && typeof error.details === "object" ? error.details : {}),
      });
    }

    return (await response.json()) as ChatResponse;
  } finally {
    clearTimeout(timeout);
  }
}

export async function POST(request: Request) {
  const id = requestId(request);
  const activeSessionId = sessionId();

  let payload: unknown;
  try {
    payload = await request.json();
  } catch {
    return NextResponse.json(
      { error: { code: "INVALID_JSON", message: "Request body must be valid JSON", request_id: id, retryable: false } },
      { status: 400 },
    );
  }

  if (!isChatRequest(payload)) {
    return NextResponse.json(
      { error: { code: "INVALID_CHAT_REQUEST", message: "conversation_id, message, attachment_ids and locale are required", request_id: id, retryable: false } },
      { status: 400 },
    );
  }

  if (payload.message.length > 4000) {
    return NextResponse.json(
      { error: { code: "MESSAGE_TOO_LONG", message: "Message must not exceed 4000 characters", request_id: id, retryable: false } },
      { status: 400 },
    );
  }

  if (!payload.message.trim() && payload.attachment_ids.length === 0) {
    return NextResponse.json(
      { error: { code: "EMPTY_MESSAGE", message: "Message or attachment is required", request_id: id, retryable: false } },
      { status: 400 },
    );
  }

  try {
    const response = await callAiService(payload, id);
    for (const action of response.actions) {
      if (action.type === "PROPOSE_CART_ADD") {
        saveProposal(action, response.conversation_id, activeSessionId);
      }
    }

    const result = NextResponse.json(response, { status: 200, headers: { "X-Request-ID": id } });
    result.cookies.set("ekt_session_id", activeSessionId, {
      httpOnly: true,
      sameSite: "lax",
      secure: process.env.NODE_ENV === "production",
      maxAge: 60 * 60 * 24 * 30,
      path: "/",
    });
    return result;
  } catch (error) {
    const serviceError = error instanceof AiServiceError
      ? error
      : new AiServiceError("LLM_UNAVAILABLE", "Сервис консультации временно недоступен. Попробуйте повторить запрос.", 503);
    return NextResponse.json(
      {
        error: {
          code: serviceError.code,
          message: serviceError.message,
          request_id: id,
          retryable: true,
          details: serviceError.details,
        },
      },
      { status: serviceError.status, headers: { "X-Request-ID": id } },
    );
  }
}

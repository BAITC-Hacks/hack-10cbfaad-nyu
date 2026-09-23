import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { randomUUID } from "node:crypto";
import { mockChatResponse } from "@/lib/server/mock-ai";
import { saveProposal } from "@/lib/server/proposals";
import { internalHeaders, requestId } from "@/lib/server/request";
import type { ChatRequest, ChatResponse } from "@/lib/types";

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
  const baseUrl = process.env.AI_SERVICE_URL;
  if (!baseUrl) return mockChatResponse(payload);

  const response = await fetch(`${baseUrl}/internal/v1/chat/messages`, {
    method: "POST",
    headers: { ...internalHeaders(id), "Content-Type": "application/json" },
    body: JSON.stringify(payload),
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`AI service returned ${response.status}`);
  }

  return (await response.json()) as ChatResponse;
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
  } catch {
    return NextResponse.json(
      {
        error: {
          code: "AI_SERVICE_UNAVAILABLE",
          message: "Сервис консультации временно недоступен. Попробуйте повторить запрос.",
          request_id: id,
          retryable: true,
        },
      },
      { status: 503, headers: { "X-Request-ID": id } },
    );
  }
}

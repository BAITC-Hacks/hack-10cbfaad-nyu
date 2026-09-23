import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { randomUUID } from "node:crypto";
import { checkAvailability } from "@/lib/server/availability";
import { getCartAdapter } from "@/lib/server/cart-adapter";
import {
  getIdempotencyResult,
  getProposal,
  makeSessionId,
  markCompleted,
  saveIdempotencyResult,
} from "@/lib/server/proposals";
import { isUuidV4, requestId } from "@/lib/server/request";
import type { CartResult } from "@/lib/types";

interface RouteContext {
  params: { proposal_id: string };
}

function errorResponse(code: string, message: string, status: number, id: string, details: Record<string, unknown> = {}) {
  return NextResponse.json(
    { error: { code, message, request_id: id, retryable: false, details } },
    { status, headers: { "X-Request-ID": id } },
  );
}

export async function POST(request: Request, context: RouteContext) {
  const id = requestId(request);
  const idempotencyKey = request.headers.get("idempotency-key");
  if (!idempotencyKey || !isUuidV4(idempotencyKey)) {
    return errorResponse("INVALID_IDEMPOTENCY_KEY", "Idempotency-Key must be a UUID v4", 400, id);
  }

  const activeSessionId = cookies().get("ekt_session_id")?.value || makeSessionId();
  const previousResult = getIdempotencyResult(activeSessionId, idempotencyKey);
  if (previousResult) return NextResponse.json(previousResult, { status: 200, headers: { "X-Request-ID": id } });

  let payload: { conversation_id?: unknown };
  try {
    payload = (await request.json()) as { conversation_id?: unknown };
  } catch {
    return errorResponse("INVALID_JSON", "Request body must be valid JSON", 400, id);
  }

  if (typeof payload.conversation_id !== "string") {
    return errorResponse("INVALID_CART_REQUEST", "conversation_id is required", 400, id);
  }

  const proposal = getProposal(context.params.proposal_id, activeSessionId);
  if (!proposal) return errorResponse("CART_PROPOSAL_NOT_FOUND", "Cart proposal was not found", 404, id);
  if (proposal.conversation_id !== payload.conversation_id) {
    return errorResponse("CART_PROPOSAL_NOT_FOUND", "Cart proposal was not found", 404, id);
  }
  if (proposal.status === "EXPIRED") {
    return errorResponse("CART_PROPOSAL_EXPIRED", "Cart proposal has expired", 409, id);
  }
  if (proposal.status === "COMPLETED") {
    return errorResponse("CART_PROPOSAL_COMPLETED", "Cart proposal has already been completed", 409, id);
  }

  let availability;
  try {
    availability = await checkAvailability(proposal.product_id, request);
  } catch {
    return errorResponse("UPSTREAM_AVAILABILITY_UNAVAILABLE", "Не удалось проверить актуальный остаток", 503, id);
  }

  if (availability.quantity_total < proposal.quantity) {
    return errorResponse(
      "INSUFFICIENT_STOCK",
      "Requested quantity exceeds current stock",
      409,
      id,
      {
        product_id: proposal.product_id,
        requested_quantity: proposal.quantity,
        available_quantity: availability.quantity_total,
      },
    );
  }

  try {
    const adapterResult = await getCartAdapter().addItem({
      userSession: { session_id: activeSessionId },
      productId: proposal.product_id,
      quantity: proposal.quantity,
      idempotencyKey,
    });
    const result: CartResult = {
      status: "added",
      proposal_id: proposal.proposal_id,
      item: { product_id: proposal.product_id, quantity: proposal.quantity },
      cart_url: adapterResult.cartUrl,
      warnings: [],
    };
    saveIdempotencyResult(activeSessionId, idempotencyKey, result);
    markCompleted(proposal.proposal_id);
    return NextResponse.json(result, { status: 200, headers: { "X-Request-ID": id } });
  } catch {
    return errorResponse("CART_UNAVAILABLE", "Не удалось добавить товар в корзину", 503, id);
  }
}

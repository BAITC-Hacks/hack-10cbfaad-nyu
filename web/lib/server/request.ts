import { randomUUID } from "node:crypto";

export function requestId(request: Request): string {
  return request.headers.get("x-request-id") || randomUUID();
}

export function internalHeaders(id: string): HeadersInit {
  const headers: Record<string, string> = {
    Authorization: `Bearer ${process.env.INTERNAL_SERVICE_TOKEN || ""}`,
    "X-Request-ID": id,
  };

  return headers;
}

export function isUuidV4(value: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(value);
}

export function ttlSeconds(): number {
  const value = Number(process.env.CART_PROPOSAL_TTL_SECONDS || 900);
  return Number.isFinite(value) && value > 0 ? value : 900;
}

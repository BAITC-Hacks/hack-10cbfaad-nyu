import { internalHeaders, requestId } from "@/lib/server/request";

export interface AvailabilityCheck {
  quantity_total: number;
  verified_at: string;
}

export async function checkAvailability(productId: number, incomingRequest: Request): Promise<AvailabilityCheck> {
  const baseUrl = process.env.PRODUCT_SERVICE_URL;
  const mockMode = (process.env.CART_ADAPTER_MODE || "mock") === "mock";

  if (!baseUrl || mockMode) {
    return {
      quantity_total: productId === 515291 ? 23 : 0,
      verified_at: new Date().toISOString(),
    };
  }

  const response = await fetch(`${baseUrl}/internal/v1/products/${productId}/availability`, {
    headers: internalHeaders(requestId(incomingRequest)),
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`Product availability returned ${response.status}`);
  }

  return (await response.json()) as AvailabilityCheck;
}

export interface UserSession {
  session_id: string;
}

export interface AddItemInput {
  userSession: UserSession;
  productId: number;
  quantity: number;
  idempotencyKey: string;
}

export interface EktCartAdapter {
  addItem(input: AddItemInput): Promise<{ cartUrl: string }>;
}

export class MockEktCartAdapter implements EktCartAdapter {
  async addItem(_input: AddItemInput): Promise<{ cartUrl: string }> {
    return { cartUrl: process.env.EKT_CART_URL || "/mock-cart" };
  }
}

export function getCartAdapter(): EktCartAdapter {
  // The real ekt.kz Cart API is explicitly unverified in ARCHITECTURE.md.
  // Keeping the adapter boundary makes the browser contract stable.
  return new MockEktCartAdapter();
}

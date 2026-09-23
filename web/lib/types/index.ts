export interface Price {
  amount: number;
  currency: string;
  verified_at: string;
}

export interface Availability {
  quantity_total: number;
  verified_at: string;
}

export interface ChatProduct {
  id: number;
  article: string;
  name: string;
  price: Price;
  availability: Availability;
  image_url: string | null;
  product_url: string;
}

export interface ChatAction {
  type: "PROPOSE_CART_ADD";
  proposal_id: string;
  product_id: number;
  quantity: number;
  label: string;
}

export interface ChatError {
  code: string;
  message: string;
  retryable: boolean;
  source?: string;
}

export interface ChatResponse {
  conversation_id: string;
  message_id: string;
  text: string;
  products: ChatProduct[];
  actions: ChatAction[];
  errors: ChatError[];
}

export interface ChatRequest {
  conversation_id: string | null;
  message: string;
  attachment_ids: string[];
  locale: "ru-RU";
}

export interface AttachmentResponse {
  attachment_id: string;
  file_name: string;
  mime_type: string;
  size_bytes: number;
  status: "ready";
}

export interface CartResult {
  status: "added";
  proposal_id: string;
  item: {
    product_id: number;
    quantity: number;
  };
  cart_url: string;
  warnings: string[];
}

export interface ApiErrorResponse {
  error: {
    code: string;
    message: string;
    request_id?: string;
    retryable: boolean;
    details?: Record<string, unknown>;
  };
}

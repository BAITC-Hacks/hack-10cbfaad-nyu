import { randomUUID } from "node:crypto";
import type { ChatRequest, ChatResponse } from "@/lib/types";

const mockProduct = {
  id: 515291,
  article: "200300285_",
  name: "027228 АВ DRX250 MT 3ф 160А 18ka Legrand (1)",
  price: {
    amount: 64920,
    currency: "KZT",
    verified_at: "2026-09-23T08:30:00Z",
  },
  availability: {
    quantity_total: 23,
    verified_at: "2026-09-23T08:30:00Z",
  },
  image_url: "https://images.unsplash.com/photo-1621905251189-08b45d6a269e?auto=format&fit=crop&w=900&q=80",
  product_url: "https://ekt.kz/catalog/027228",
};

const quantityWords: Record<string, number> = {
  один: 1,
  одну: 1,
  одна: 1,
  два: 2,
  две: 2,
  три: 3,
  четыре: 4,
  пять: 5,
};

const cartQuantityPattern = "(?:\\d+|один|одну|одна|два|две|три|четыре|пять)";
const cartIntentPattern = new RegExp(
  `(?:^|[^\\p{L}])(?:добав(?:ь|ить|ьте)|хочу|возьми|положи|беру|можно|add)(?:[^\\p{L}\\p{N}]+мне)?[^\\p{L}\\p{N}]+(${cartQuantityPattern})(?=$|[^\\p{L}\\p{N}])`,
  "iu",
);

function parseQuantity(value: string): number {
  const parsed = /^\d+$/.test(value) ? Number(value) : quantityWords[value];
  return Number.isSafeInteger(parsed) && parsed >= 1 ? parsed : 0;
}

export function mockChatResponse(request: ChatRequest): ChatResponse {
  const conversationId = request.conversation_id || randomUUID();
  const message = request.message.trim();
  const lowerMessage = message.toLocaleLowerCase("ru-RU");
  const quantityMatch = lowerMessage.match(cartIntentPattern);
  const quantity = quantityMatch ? parseQuantity(quantityMatch[1]) : 0;

  if (lowerMessage.includes("недоступ") || lowerMessage.includes("ошибка каталога")) {
    return {
      conversation_id: conversationId,
      message_id: randomUUID(),
      text: "Сейчас не удалось проверить актуальную цену и наличие. Попробуйте повторить запрос позже.",
      products: [],
      actions: [],
      errors: [
        {
          code: "UPSTREAM_CATALOG_UNAVAILABLE",
          message: "Live catalog data is unavailable",
          retryable: true,
          source: "product-service",
        },
      ],
    };
  }

  if (quantity > 0) {
    return {
      conversation_id: conversationId,
      message_id: randomUUID(),
      text: `Готов добавить ${quantity} шт. Подтвердите добавление в корзину.`,
      products: [],
      actions: [
        {
          type: "PROPOSE_CART_ADD",
          proposal_id: randomUUID(),
          product_id: mockProduct.id,
          quantity,
          label: `Добавить ${quantity} шт. в корзину`,
        },
      ],
      errors: [],
    };
  }

  if (!message && request.attachment_ids.length > 0) {
    return {
      conversation_id: conversationId,
      message_id: randomUUID(),
      text: "Файл принят. Уточните, какой товар или характеристики нужно проверить.",
      products: [],
      actions: [],
      errors: [],
    };
  }

  return {
    conversation_id: conversationId,
    message_id: randomUUID(),
    text: "Нашёл подходящий товар. По актуальным данным доступно 23 шт. Цена — 64 920 KZT.",
    products: [mockProduct],
    actions: [],
    errors: [],
  };
}

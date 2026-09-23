import { CartConfirmation } from "@/components/cart/CartConfirmation";
import { ProductCard } from "@/components/products/ProductCard";
import type { ChatResponse } from "@/lib/types";

interface ChatMessageProps {
  role: "user" | "assistant";
  text: string;
  response?: ChatResponse;
  onRetry?: () => void;
}

export function ChatMessage({ role, text, response, onRetry }: ChatMessageProps) {
  const isUser = role === "user";
  const retryable = response?.errors.some((error) => error.retryable);

  return (
    <div className={`flex min-w-0 max-w-full ${isUser ? "justify-end" : "justify-start"}`}>
      <div className={`min-w-0 max-w-[94%] sm:max-w-[82%] ${isUser ? "items-end" : "items-start"}`}>
        <div
          className={`rounded-2xl px-4 py-3 text-sm leading-6 shadow-sm ${
            isUser ? "rounded-br-md bg-ink text-white" : "rounded-bl-md border border-slate-200 bg-white text-slate-700"
          }`}
        >
          <p className="break-words whitespace-pre-wrap">{text}</p>
        </div>

        {!isUser && response && (
          <div className="mt-3 min-w-0 max-w-full space-y-3">
            {response.products.length > 0 && (
              <div className="grid min-w-0 gap-3 sm:grid-cols-2">
                {response.products.map((product) => <ProductCard key={product.id} product={product} />)}
              </div>
            )}
            {response.actions.map((action) => (
              <CartConfirmation key={action.proposal_id} action={action} conversationId={response.conversation_id} />
            ))}
            {response.errors.map((error) => (
              <div key={`${error.code}-${error.message}`} className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
                <p className="font-semibold">{error.code}</p>
                <p className="mt-1">{error.message}</p>
              </div>
            ))}
            {retryable && onRetry && (
              <button type="button" className="text-sm font-semibold text-cyan-700 underline" onClick={onRetry}>
                Повторить
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

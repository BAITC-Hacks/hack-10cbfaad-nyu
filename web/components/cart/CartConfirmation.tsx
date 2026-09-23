"use client";

import { useState } from "react";
import { confirmCart } from "@/lib/api/client";
import type { ChatAction, CartResult } from "@/lib/types";

interface CartConfirmationProps {
  action: ChatAction;
  conversationId: string;
}

export function CartConfirmation({ action, conversationId }: CartConfirmationProps) {
  const [state, setState] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [result, setResult] = useState<CartResult | null>(null);
  const [error, setError] = useState("");
  const [cancelled, setCancelled] = useState(false);
  const [idempotencyKey] = useState(() => crypto.randomUUID());

  async function handleConfirm() {
    setState("loading");
    setError("");
    try {
      const response = await confirmCart(action.proposal_id, conversationId, idempotencyKey);
      setResult(response);
      setState("success");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Не удалось добавить товар в корзину");
      setState("error");
    }
  }

  if (cancelled) return null;

  if (state === "success" && result) {
    return (
      <div className="mt-3 rounded-2xl border border-emerald-200 bg-emerald-50 p-4">
        <p className="font-semibold text-emerald-800">Товар добавлен в корзину</p>
        <a className="mt-2 inline-flex text-sm font-semibold text-emerald-700 underline" href={result.cart_url}>
          Перейти в корзину →
        </a>
      </div>
    );
  }

  return (
    <div className="mt-3 rounded-2xl border border-cyan-200 bg-cyan-50/70 p-4">
      <div className="flex items-start gap-3">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-cyan-100 text-cyan-700">＋</div>
        <div className="min-w-0 flex-1">
          <p className="font-semibold text-slate-800">Добавить товар в корзину?</p>
          <p className="mt-1 text-sm text-slate-600">Количество: {action.quantity}</p>
          {state === "error" && <p className="mt-2 text-sm text-rose-700">{error}</p>}
          <div className="mt-4 flex flex-wrap gap-2">
            <button
              type="button"
              className="rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-600 transition hover:bg-slate-50"
              onClick={() => setCancelled(true)}
              disabled={state === "loading"}
            >
              Отмена
            </button>
            <button
              type="button"
              className="rounded-xl bg-ink px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:cursor-wait disabled:opacity-60"
              onClick={handleConfirm}
              disabled={state === "loading"}
            >
              {state === "loading" ? "Проверяем остаток…" : "Подтвердить"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

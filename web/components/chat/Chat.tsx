"use client";

import { useEffect, useRef, useState } from "react";
import { ApiClientError, sendChat, uploadAttachment } from "@/lib/api/client";
import type { ChatResponse } from "@/lib/types";
import { ChatInput, type PendingAttachment } from "@/components/chat/ChatInput";
import { ChatMessage } from "@/components/chat/ChatMessage";

interface UiMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  response?: ChatResponse;
  attachments?: string[];
}

export function Chat() {
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<UiMessage[]>([]);
  const [attachments, setAttachments] = useState<PendingAttachment[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [sending, setSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, sending]);

  async function handleUpload(file: File) {
    setUploading(true);
    setUploadError("");
    try {
      const uploaded = await uploadAttachment(file);
      setAttachments((current) => [
        ...current,
        { attachment_id: uploaded.attachment_id, file_name: uploaded.file_name },
      ]);
    } catch (error) {
      setUploadError(error instanceof Error ? error.message : "Не удалось загрузить файл");
    } finally {
      setUploading(false);
    }
  }

  async function sendMessage(message: string, retrying = false) {
    const attachmentIds = attachments.map((attachment) => attachment.attachment_id);
    const attachmentNames = attachments.map((attachment) => attachment.file_name);
    if (!retrying) {
      setMessages((current) => [
        ...current,
        { id: crypto.randomUUID(), role: "user", text: message || "Файл прикреплён", attachments: attachmentNames },
      ]);
    }
    setSending(true);
    try {
      const response = await sendChat({
        conversation_id: conversationId,
        message,
        attachment_ids: attachmentIds,
        locale: "ru-RU",
      });
      setConversationId(response.conversation_id);
      setMessages((current) => [...current, { id: response.message_id, role: "assistant", text: response.text, response }]);
      setAttachments([]);
    } catch (error) {
      const text = error instanceof ApiClientError ? error.message : "Не удалось отправить сообщение. Попробуйте ещё раз.";
      const errorResponse: ChatResponse = {
        conversation_id: conversationId || crypto.randomUUID(),
        message_id: crypto.randomUUID(),
        text,
        products: [],
        actions: [],
        errors: error instanceof ApiClientError
          ? [{ code: error.code, message: text, retryable: error.retryable, source: "web" }]
          : [{ code: "WEB_REQUEST_FAILED", message: text, retryable: true, source: "web" }],
      };
      setMessages((current) => [...current, { id: errorResponse.message_id, role: "assistant", text, response: errorResponse }]);
    } finally {
      setSending(false);
    }
  }

  async function retryMessage(message: UiMessage) {
    await sendMessage(message.text, true);
  }

  return (
    <main className="min-h-screen overflow-x-hidden px-3 py-4 sm:px-6 sm:py-8">
      <section className="mx-auto flex min-h-[calc(100vh-2rem)] min-w-0 max-w-6xl flex-col overflow-hidden rounded-[28px] border border-white/70 bg-white/75 shadow-soft backdrop-blur sm:min-h-[calc(100vh-4rem)]">
        <header className="flex items-center justify-between border-b border-slate-200/80 px-4 py-4 sm:px-7 sm:py-5">
          <div className="flex items-center gap-3">
            <div className="relative flex h-11 w-11 items-center justify-center rounded-2xl bg-ink text-lg font-bold text-white shadow-lg shadow-slate-300">
              E
              <span className="absolute -bottom-0.5 -right-0.5 h-3 w-3 rounded-full border-2 border-white bg-emerald-400" />
            </div>
            <div>
              <h1 className="text-base font-bold tracking-tight text-ink sm:text-lg">EKT AI</h1>
              <p className="text-xs text-slate-500 sm:text-sm">ИИ-консультант по электротоварам</p>
            </div>
          </div>
          <span className="hidden rounded-full bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-700 sm:inline-flex">Онлайн</span>
        </header>

        <div className="flex min-h-0 flex-1 flex-col">
          <div className="flex min-w-0 flex-1 space-y-5 overflow-x-hidden overflow-y-auto px-3 py-5 sm:px-7 sm:py-7">
            {messages.length === 0 ? (
              <div className="flex min-h-[46vh] items-center justify-center">
                <div className="max-w-md text-center">
                  <div className="mx-auto mb-5 flex h-16 w-16 items-center justify-center rounded-3xl bg-cyan-50 text-3xl">✦</div>
                  <h2 className="text-2xl font-bold tracking-tight text-ink">Чем могу помочь?</h2>
                  <p className="mt-3 text-sm leading-6 text-slate-500">Найдём товар, проверим наличие или разберём спецификацию из файла.</p>
                  <div className="mt-6 flex flex-wrap justify-center gap-2">
                    {["Найди Legrand DRX250", "Сколько есть в Алматы?", "Добавь 2"].map((prompt) => (
                      <button
                        type="button"
                        key={prompt}
                        className="rounded-full border border-slate-200 bg-white px-3.5 py-2 text-xs font-medium text-slate-600 transition hover:border-cyan-300 hover:text-cyan-700"
                        onClick={() => void sendMessage(prompt)}
                      >
                        {prompt}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              messages.map((message, index) => (
                <ChatMessage
                  key={message.id}
                  role={message.role}
                  text={message.attachments?.length ? `${message.text}\n📎 ${message.attachments.join(", ")}` : message.text}
                  response={message.response}
                  onRetry={message.response?.errors.some((error) => error.retryable) ? () => void retryMessage(messages[index - 1] || message) : undefined}
                />
              ))
            )}
            {sending && (
              <div className="flex items-center gap-2 text-sm text-slate-400">
                <span className="flex gap-1"><i className="h-1.5 w-1.5 animate-bounce rounded-full bg-cyan-500 [animation-delay:-0.2s]" /><i className="h-1.5 w-1.5 animate-bounce rounded-full bg-cyan-500 [animation-delay:-0.1s]" /><i className="h-1.5 w-1.5 animate-bounce rounded-full bg-cyan-500" /></span>
                Проверяю данные…
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
          <ChatInput
            attachments={attachments}
            disabled={sending}
            uploading={uploading}
            uploadError={uploadError}
            onUpload={handleUpload}
            onRemoveAttachment={(attachmentId) => setAttachments((current) => current.filter((item) => item.attachment_id !== attachmentId))}
            onSend={(message) => sendMessage(message)}
          />
        </div>
      </section>
    </main>
  );
}

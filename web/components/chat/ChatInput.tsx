"use client";

import { useState } from "react";
import { FileUpload } from "@/components/files/FileUpload";

export interface PendingAttachment {
  attachment_id: string;
  file_name: string;
}

interface ChatInputProps {
  attachments: PendingAttachment[];
  disabled?: boolean;
  uploading?: boolean;
  uploadError?: string;
  onUpload: (file: File) => Promise<void>;
  onRemoveAttachment: (attachmentId: string) => void;
  onSend: (message: string) => Promise<void>;
}

export function ChatInput({
  attachments,
  disabled = false,
  uploading = false,
  uploadError,
  onUpload,
  onRemoveAttachment,
  onSend,
}: ChatInputProps) {
  const [message, setMessage] = useState("");

  async function submit() {
    if ((!message.trim() && attachments.length === 0) || disabled) return;
    await onSend(message);
    setMessage("");
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void submit();
    }
  }

  return (
    <div className="border-t border-slate-200 bg-white/90 p-3 backdrop-blur max-[480px]:p-2 sm:p-4">
      {attachments.length > 0 && (
        <div className="mb-3 flex flex-wrap gap-2">
          {attachments.map((attachment) => (
            <span key={attachment.attachment_id} className="inline-flex min-w-0 max-w-full items-center gap-2 rounded-lg bg-slate-100 px-3 py-1.5 text-xs font-medium text-slate-600">
              <span className="min-w-0 truncate">{attachment.file_name}</span>
              <button
                type="button"
                className="text-slate-400 hover:text-rose-600"
                onClick={() => onRemoveAttachment(attachment.attachment_id)}
                aria-label={`Удалить ${attachment.file_name}`}
              >
                ×
              </button>
            </span>
          ))}
        </div>
      )}
      {uploadError && <p className="mb-2 text-xs font-medium text-rose-600">{uploadError}</p>}
      <div className="flex min-w-0 items-end gap-2 max-[480px]:gap-1.5">
        <FileUpload onUpload={onUpload} disabled={disabled || uploading} />
        <textarea
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          rows={1}
          placeholder={uploading ? "Загружаем файл…" : "Спросите о товаре или наличии…"}
          className="min-w-0 max-h-32 min-h-11 flex-1 resize-none rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-800 outline-none transition placeholder:text-slate-400 focus:border-cyan-400 focus:bg-white focus:ring-4 focus:ring-cyan-100 disabled:cursor-not-allowed disabled:opacity-60 max-[480px]:px-2.5 max-[480px]:text-xs"
        />
        <button
          type="button"
          onClick={() => void submit()}
          disabled={disabled || uploading || (!message.trim() && attachments.length === 0)}
          aria-label={disabled ? "Отправка сообщения" : "Отправить сообщение"}
          className="h-11 shrink-0 rounded-xl bg-ink px-4 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-40 max-[480px]:px-2.5 max-[480px]:text-xs sm:px-5"
        >
          {disabled ? "…" : <><span className="max-[480px]:hidden">Отправить</span><span className="hidden max-[480px]:inline">Отпр.</span></>}
        </button>
      </div>
      <p className="mt-2 hidden text-[11px] text-slate-400 sm:block">Enter — отправить · Shift + Enter — новая строка</p>
    </div>
  );
}

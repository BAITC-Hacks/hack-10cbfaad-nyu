"use client";

import { useRef } from "react";

interface FileUploadProps {
  onUpload: (file: File) => Promise<void>;
  disabled?: boolean;
}

export function FileUpload({ onUpload, disabled = false }: FileUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  async function handleChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (file) await onUpload(file);
  }

  return (
    <>
      <input
        ref={inputRef}
        className="hidden"
        type="file"
        accept=".pdf,.xlsx,.docx,.jpg,.jpeg,application/pdf,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.openxmlformats-officedocument.wordprocessingml.document,image/jpeg"
        onChange={handleChange}
        disabled={disabled}
      />
      <button
        type="button"
        aria-label="Прикрепить файл"
        title="PDF, XLSX, DOCX или JPEG до 15 MiB"
        className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-slate-200 bg-white text-xl text-slate-500 transition hover:border-cyan-300 hover:text-cyan-700 disabled:cursor-not-allowed disabled:opacity-50"
        onClick={() => inputRef.current?.click()}
        disabled={disabled}
      >
        ⌕
      </button>
    </>
  );
}

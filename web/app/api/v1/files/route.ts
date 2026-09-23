import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import { randomUUID } from "node:crypto";
import { internalHeaders, requestId } from "@/lib/server/request";
import type { AttachmentResponse } from "@/lib/types";

const MAX_FILE_SIZE = 15 * 1024 * 1024;
const ALLOWED_MIME_TYPES = new Set([
  "application/pdf",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "image/jpeg",
]);

function errorResponse(code: string, message: string, status: number, id: string) {
  return NextResponse.json(
    { error: { code, message, request_id: id, retryable: false } },
    { status, headers: { "X-Request-ID": id } },
  );
}

export async function POST(request: Request) {
  const id = requestId(request);
  let formData: FormData;
  try {
    formData = await request.formData();
  } catch {
    return errorResponse("FILE_PARSE_FAILED", "Не удалось прочитать загруженный файл", 422, id);
  }

  const file = formData.get("file");
  if (!(file instanceof File)) {
    return errorResponse("FILE_PARSE_FAILED", "Поле file обязательно", 422, id);
  }
  if (file.size > MAX_FILE_SIZE) {
    return errorResponse("FILE_TOO_LARGE", "Размер файла не должен превышать 15 MiB", 413, id);
  }
  if (!ALLOWED_MIME_TYPES.has(file.type)) {
    return errorResponse("UNSUPPORTED_FILE_TYPE", "Поддерживаются только PDF, XLSX, DOCX и JPEG", 415, id);
  }

  try {
    const serviceUrl = process.env.AI_SERVICE_URL;
    let attachment: AttachmentResponse;

    if (serviceUrl) {
      const upstreamForm = new FormData();
      upstreamForm.append("file", file, file.name);
      const upstreamResponse = await fetch(`${serviceUrl}/internal/v1/attachments`, {
        method: "POST",
        headers: internalHeaders(id),
        body: upstreamForm,
      });
      if (!upstreamResponse.ok) {
        return errorResponse("FILE_PARSE_FAILED", "AI Service не смог обработать файл", 422, id);
      }
      attachment = (await upstreamResponse.json()) as AttachmentResponse;
    } else {
      attachment = {
        attachment_id: randomUUID(),
        file_name: file.name,
        mime_type: file.type,
        size_bytes: file.size,
        status: "ready",
      };
    }

    const result = NextResponse.json(attachment, { status: 201, headers: { "X-Request-ID": id } });
    if (!cookies().get("ekt_session_id")) {
      result.cookies.set("ekt_session_id", randomUUID(), { httpOnly: true, sameSite: "lax", path: "/" });
    }
    return result;
  } catch {
    return errorResponse("FILE_PARSE_FAILED", "Не удалось обработать файл", 422, id);
  }
}

import "client-only";

import type {
  CollectionsResponse,
  PdfIngestResponse,
  UploadPdfRequest,
} from "@/types/rag";

async function getErrorMessage(
  response: Response,
): Promise<string> {
  try {
    const data = (await response.json()) as {
      detail?: string;
      message?: string;
    };

    return (
      data.detail ||
      data.message ||
      `请求失败，状态码：${response.status}`
    );
  } catch {
    return `请求失败，状态码：${response.status}`;
  }
}

export async function listCollections(
  signal?: AbortSignal,
): Promise<string[]> {
  const response = await fetch("/backend/rag/collections", {
    method: "GET",
    signal,
  });

  if (!response.ok) {
    throw new Error(await getErrorMessage(response));
  }

  const data = (await response.json()) as CollectionsResponse;

  return data.collections;
}

export async function uploadPdf(
  request: UploadPdfRequest,
  signal?: AbortSignal,
): Promise<PdfIngestResponse> {
  const formData = new FormData();

  formData.append("file", request.file);
  formData.append("collection_name", request.collectionName);

  const response = await fetch("/backend/rag/ingest/pdf", {
    method: "POST",
    body: formData,
    signal,
  });

  if (!response.ok) {
    throw new Error(await getErrorMessage(response));
  }

  return (await response.json()) as PdfIngestResponse;
}
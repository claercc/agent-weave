export interface CollectionsResponse {
  collections: string[];
}

export interface PdfIngestResponse {
  message: string;
  filename: string;
  collection_name: string;
  chunk_count: number;
}

export interface UploadPdfRequest {
  file: File;
  collectionName: string;
}
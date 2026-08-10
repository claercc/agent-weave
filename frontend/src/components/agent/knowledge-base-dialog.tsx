"use client";

import {
  ChangeEvent,
  useCallback,
  useRef,
  useState,
} from "react";
import {
  CheckCircle2,
  Database,
  FileUp,
  LoaderCircle,
  RefreshCw,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import {
  listCollections,
  uploadPdf,
} from "@/lib/rag-api";
import type { PdfIngestResponse } from "@/types/rag";

interface KnowledgeBaseDialogProps {
  value: string;
  onValueChange: (value: string) => void;
  disabled?: boolean;
}

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}

export function KnowledgeBaseDialog({
  value,
  onValueChange,
  disabled = false,
}: KnowledgeBaseDialogProps) {
  const [open, setOpen] = useState(false);
  const [collections, setCollections] = useState<string[]>([]);
  const [collectionName, setCollectionName] = useState(
    value || "project-demo",
  );
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] =
    useState<PdfIngestResponse | null>(null);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const loadAbortControllerRef = useRef<AbortController | null>(null);

  const loadCollections = useCallback(
    async (signal?: AbortSignal) => {
      setIsLoading(true);
      setError("");

      try {
        const collectionNames = await listCollections(signal);
        setCollections(collectionNames);
      } catch (requestError) {
        if (!isAbortError(requestError)) {
          setError(
            requestError instanceof Error
              ? requestError.message
              : "读取知识库失败。",
          );
        }
      } finally {
        setIsLoading(false);
      }
    },
    [],
  );

  function handleOpenChange(nextOpen: boolean) {
    setOpen(nextOpen);
    loadAbortControllerRef.current?.abort();
    loadAbortControllerRef.current = null;

    if (!nextOpen) {
      return;
    }

    setCollectionName(value || "project-demo");

    const abortController = new AbortController();
    loadAbortControllerRef.current = abortController;
    void loadCollections(abortController.signal);
  }

  function handleFileChange(
    event: ChangeEvent<HTMLInputElement>,
  ) {
    setFile(event.target.files?.[0] ?? null);
    setResult(null);
    setError("");
  }

  async function handleUpload() {
    const normalizedCollectionName = collectionName.trim();

    if (!normalizedCollectionName) {
      setError("请输入知识库名称。");
      return;
    }

    if (!file) {
      setError("请选择需要上传的 PDF 文件。");
      return;
    }

    setIsUploading(true);
    setError("");
    setResult(null);

    try {
      const uploadResult = await uploadPdf({
        file,
        collectionName: normalizedCollectionName,
      });

      setResult(uploadResult);
      onValueChange(uploadResult.collection_name);

      setCollections((currentCollections) => {
        if (
          currentCollections.includes(
            uploadResult.collection_name,
          )
        ) {
          return currentCollections;
        }

        return [
          ...currentCollections,
          uploadResult.collection_name,
        ].sort();
      });
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "PDF 上传失败。",
      );
    } finally {
      setIsUploading(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button
          type="button"
          variant="outline"
          disabled={disabled}
        >
          <Database />
          知识库
          {value && (
            <Badge variant="secondary" className="ml-1">
              {value}
            </Badge>
          )}
        </Button>
      </DialogTrigger>

      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>知识库管理</DialogTitle>
          <DialogDescription>
            选择已有知识库，或者上传 PDF 创建新的知识库。
          </DialogDescription>
        </DialogHeader>

        <section className="space-y-3">
          <div className="flex items-center justify-between">
            <Label>已有知识库</Label>

            <Button
              type="button"
              variant="ghost"
              size="icon-sm"
              onClick={() => void loadCollections()}
              disabled={isLoading}
              aria-label="刷新知识库"
            >
              <RefreshCw
                className={isLoading ? "animate-spin" : ""}
              />
            </Button>
          </div>

          {isLoading && collections.length === 0 ? (
            <div className="flex items-center gap-2 py-4 text-sm text-muted-foreground">
              <LoaderCircle className="size-4 animate-spin" />
              正在读取知识库
            </div>
          ) : collections.length === 0 ? (
            <p className="py-4 text-sm text-muted-foreground">
              当前还没有知识库，可以上传第一个 PDF。
            </p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {collections.map((collection) => (
                <Button
                  key={collection}
                  type="button"
                  size="sm"
                  variant={
                    value === collection
                      ? "default"
                      : "outline"
                  }
                  onClick={() => {
                    onValueChange(collection);
                    setCollectionName(collection);
                  }}
                >
                  <Database />
                  {collection}
                </Button>
              ))}
            </div>
          )}
        </section>

        <Separator />

        <section className="space-y-4">
          <div>
            <h3 className="text-sm font-medium">
              上传 PDF
            </h3>
            <p className="mt-1 text-xs text-muted-foreground">
              后端会自动解析、分块并写入向量数据库。
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="collection-name">
              知识库名称
            </Label>
            <Input
              id="collection-name"
              value={collectionName}
              onChange={(event) =>
                setCollectionName(event.target.value)
              }
              placeholder="例如：project-docs"
              disabled={isUploading}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="pdf-file">PDF 文件</Label>
            <Input
              id="pdf-file"
              type="file"
              accept="application/pdf,.pdf"
              onChange={handleFileChange}
              disabled={isUploading}
            />
          </div>

          <Button
            type="button"
            onClick={() => void handleUpload()}
            disabled={
              isUploading ||
              !file ||
              !collectionName.trim()
            }
          >
            {isUploading ? (
              <LoaderCircle className="animate-spin" />
            ) : (
              <FileUp />
            )}
            {isUploading ? "正在处理 PDF" : "上传并创建知识库"}
          </Button>

          {result && (
            <div className="flex items-start gap-3 rounded-2xl border border-emerald-500/20 bg-emerald-500/10 p-3">
              <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-emerald-600" />

              <div className="text-sm">
                <p className="font-medium">
                  {result.message}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {result.filename} · {result.chunk_count} 个分块
                </p>
              </div>
            </div>
          )}

          {error && (
            <p className="text-sm text-destructive">
              {error}
            </p>
          )}
        </section>
      </DialogContent>
    </Dialog>
  );
}

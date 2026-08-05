import { useRef, useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ExternalLink, FileText, Search, Trash2, Upload } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  askDocuments,
  deleteDocument,
  listDocuments,
  uploadDocument,
} from "@/lib/api";
import type { AskResult } from "@/lib/types";

interface StudyMaterialDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function StudyMaterialDialog({
  open,
  onOpenChange,
}: StudyMaterialDialogProps) {
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<AskResult | null>(null);
  // Native file input, kept hidden and driven by the button — no dropzone dependency.
  const fileInput = useRef<HTMLInputElement>(null);
  const queryClient = useQueryClient();

  const docsQuery = useQuery({
    queryKey: ["documents"],
    queryFn: listDocuments,
    enabled: open,
  });

  const refreshDocs = () =>
    queryClient.invalidateQueries({ queryKey: ["documents"] });

  const upload = useMutation({
    mutationFn: uploadDocument,
    onSuccess: (doc) => {
      toast.success(
        `Added "${doc.filename}" — ${doc.chunks} passages indexed.`,
      );
      refreshDocs();
    },
    onError: (err: Error) => toast.error(`Upload failed: ${err.message}`),
  });

  const remove = useMutation({
    mutationFn: deleteDocument,
    onSuccess: () => {
      toast.success("Document removed.");
      refreshDocs();
    },
    onError: (err: Error) => toast.error(`Delete failed: ${err.message}`),
  });

  const ask = useMutation({
    mutationFn: askDocuments,
    onSuccess: setResult,
    onError: (err: Error) => toast.error(`Search failed: ${err.message}`),
  });

  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) upload.mutate(file);
    e.target.value = ""; // let the same file be re-picked after a failure
  };

  const handleAsk = (e: FormEvent) => {
    e.preventDefault();
    if (!question.trim() || ask.isPending) return;
    setResult(null);
    ask.mutate(question.trim());
  };

  const docs = docsQuery.data ?? [];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Study material</DialogTitle>
          <DialogDescription>
            Upload PDFs you study from, then ask questions against them.
          </DialogDescription>
        </DialogHeader>

        <div className="flex max-h-[65vh] flex-col gap-4 overflow-y-auto pr-1">
          <div>
            <input
              ref={fileInput}
              type="file"
              accept="application/pdf"
              className="hidden"
              onChange={handleFile}
            />
            <Button
              variant="outline"
              size="sm"
              onClick={() => fileInput.current?.click()}
              disabled={upload.isPending}
            >
              <Upload className="h-3.5 w-3.5" />
              {upload.isPending ? "Processing…" : "Upload a PDF"}
            </Button>
            {upload.isPending && (
              <p className="mt-2 text-xs text-muted-foreground">
                Extracting text and building embeddings — this takes a moment.
              </p>
            )}
          </div>

          {docsQuery.isLoading && (
            <div className="py-4 text-center text-sm text-muted-foreground">
              Loading your material…
            </div>
          )}

          {!docsQuery.isLoading && docs.length === 0 && (
            <div className="rounded-lg border border-dashed border-border py-6 text-center text-sm text-muted-foreground">
              Nothing uploaded yet. Add a PDF to search it later.
            </div>
          )}

          {docs.length > 0 && (
            <div className="flex flex-col gap-2">
              {docs.map((d) => (
                <div
                  key={d.id}
                  className="flex items-center justify-between gap-3 rounded-lg border border-border px-3 py-2.5"
                >
                  <div className="flex min-w-0 items-center gap-2">
                    <FileText className="h-4 w-4 shrink-0 opacity-60" />
                    <div className="min-w-0">
                      <div className="truncate text-sm font-medium">
                        {d.filename}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {d.pages} {d.pages === 1 ? "page" : "pages"}
                      </div>
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="shrink-0"
                    aria-label={`Remove ${d.filename}`}
                    onClick={() => remove.mutate(d.id)}
                    disabled={remove.isPending}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              ))}
            </div>
          )}

          <form
            onSubmit={handleAsk}
            className="flex gap-2 border-t border-border pt-4"
          >
            <Input
              placeholder="Top 3 tips to get better at DP?"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              disabled={docs.length === 0}
            />
            <Button
              type="submit"
              size="sm"
              disabled={docs.length === 0 || ask.isPending || !question.trim()}
            >
              <Search className="h-3.5 w-3.5" />
              {ask.isPending ? "Searching…" : "Ask"}
            </Button>
          </form>

          {ask.isPending && (
            <p className="text-xs text-muted-foreground">
              Searching, grading passages, and writing the answer. This may take
              a few minutes…
            </p>
          )}

          {result && <AskAnswer result={result} />}
        </div>
      </DialogContent>
    </Dialog>
  );
}

function AskAnswer({ result }: { result: AskResult }) {
  const nothing =
    result.passages.length === 0 && result.web.length === 0 && !result.answer;

  if (nothing) {
    return (
      <div className="rounded-lg border border-border py-6 text-center text-sm text-muted-foreground">
        Nothing in your material covers that yet.
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {result.answer && (
        <div className="rounded-lg border border-border bg-muted/40 px-3 py-2.5">
          <p className="whitespace-pre-wrap text-sm">{result.answer}</p>
        </div>
      )}

      {result.passages.length > 0 && (
        <div className="flex flex-col gap-2">
          <div className="text-xs font-medium text-muted-foreground">
            {result.answer ? "Based on these passages" : "From your material"}
          </div>
          {/* Ordered by the cross-encoder; the raw logit is not user-meaningful,
              so rank and source are shown instead of a score. */}
          {result.passages.map((p, i) => (
            <div
              key={p.chunk_id}
              className="rounded-lg border border-border px-3 py-2.5"
            >
              <div className="mb-1 flex items-center gap-2">
                <Badge variant="outline" className="shrink-0">
                  {i === 0 ? "Best match" : `#${i + 1}`}
                </Badge>
                <span className="truncate text-xs text-muted-foreground">
                  {p.document}
                </span>
              </div>
              <p className="text-sm text-muted-foreground">{p.text}</p>
            </div>
          ))}
        </div>
      )}

      {result.web.length > 0 && (
        <div className="flex flex-col gap-2">
          <div className="text-xs font-medium text-muted-foreground">
            Your material didn't cover this — from the web
          </div>
          {result.web.map((w) => (
            <a
              key={w.url}
              href={w.url}
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-1.5 rounded-lg border border-border px-3 py-2 text-sm text-primary hover:underline"
            >
              <span className="truncate">{w.title || w.url}</span>
              <ExternalLink className="h-3 w-3 shrink-0 opacity-60" />
            </a>
          ))}
        </div>
      )}

      {result.trace.length > 0 && (
        <details className="text-xs text-muted-foreground">
          <summary className="cursor-pointer select-none">
            What the search did
          </summary>
          <ul className="mt-1.5 space-y-0.5 pl-4">
            {result.trace.map((t, i) => (
              <li key={i} className="list-disc">
                {t}
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}

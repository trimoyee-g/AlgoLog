import { useQuery } from "@tanstack/react-query";
import { ExternalLink } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { getSimilar } from "@/lib/api";
import { PLATFORM_LABELS, type Problem } from "@/lib/types";

interface SimilarDialogProps {
  problem: Problem | null;
  onOpenChange: (open: boolean) => void;
}

export function SimilarDialog({ problem, onOpenChange }: SimilarDialogProps) {
  const { data, isLoading } = useQuery({
    queryKey: ["similar", problem?.id],
    queryFn: () => getSimilar(problem!.id),
    enabled: !!problem,
  });

  return (
    <Dialog open={!!problem} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Similar to "{problem?.title}"</DialogTitle>
          <DialogDescription>
            Embedding-similarity matches from your own history.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-2">
          {isLoading && (
            <div className="py-6 text-center text-sm text-muted-foreground">
              Searching your history…
            </div>
          )}
          {!isLoading && data?.length === 0 && (
            <div className="py-6 text-center text-sm text-muted-foreground">
              No similar problems found yet.
            </div>
          )}
          {data?.map((r) => (
            <div
              key={r.id}
              className="flex items-center justify-between gap-3 rounded-lg border border-border px-3 py-2.5"
            >
              <div className="min-w-0">
                <a
                  href={r.url}
                  target="_blank"
                  rel="noreferrer"
                  className="flex min-w-0 items-center gap-1.5 text-sm font-medium text-primary hover:underline"
                >
                  <span className="truncate">{r.title}</span>
                  <ExternalLink className="h-3 w-3 shrink-0 opacity-60" />
                </a>
                <div className="mt-0.5 text-xs text-muted-foreground">
                  {PLATFORM_LABELS[r.platform]}
                  {r.latest_rating != null ? ` · you rated it ${r.latest_rating}/5` : ""}
                </div>
              </div>
              <Badge variant="outline" className="shrink-0">
                {Math.round(r.similarity * 100)}% match
              </Badge>
            </div>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  );
}

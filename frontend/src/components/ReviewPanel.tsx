import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Link } from "react-router-dom";
import { ExternalLink, Brain } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { getReviewQueue, addAttempt } from "@/lib/api";
import { PLATFORM_LABELS, reviewSignal, type ReviewItem } from "@/lib/types";

// SM-2 recall scale. quality < 3 resets the interval; 3-5 grow it.
const QUALITY_SCALE = [
  { q: 0, label: "Blackout", hint: "No idea", tone: "destructive" as const },
  { q: 1, label: "Wrong", hint: "Familiar but failed", tone: "destructive" as const },
  { q: 2, label: "Close", hint: "Wrong, nearly had it", tone: "destructive" as const },
  { q: 3, label: "Hard", hint: "Right, real effort", tone: "warning" as const },
  { q: 4, label: "Good", hint: "Right, a little effort", tone: "success" as const },
  { q: 5, label: "Easy", hint: "Instant recall", tone: "success" as const },
];

function dueLabel(item: ReviewItem): string {
  const days = Math.round((new Date(item.due).getTime() - Date.now()) / 86_400_000);
  if (days > 0) return `in ${days}d`;
  if (item.overdue_days <= 0) return "Due today";
  return `${item.overdue_days}d overdue`;
}

/** `full` = the /review page: whole schedule (due + upcoming). Default = dashboard widget: due only. */
export function ReviewPanel({ full = false }: { full?: boolean } = {}) {
  const [reviewing, setReviewing] = useState<ReviewItem | null>(null);
  const queryClient = useQueryClient();

  const queue = useQuery({
    queryKey: ["review", full],
    queryFn: () => getReviewQueue(!full),
  });

  const mutation = useMutation({
    mutationFn: (vars: { item: ReviewItem; quality: number }) =>
      addAttempt({
        url: vars.item.url,
        title: vars.item.title,
        platform: vars.item.platform,
        tags: vars.item.tags,
        ...reviewSignal(vars.quality),
      }),
    onSuccess: () => {
      toast.success("Recall logged — rescheduled.");
      setReviewing(null);
      queryClient.invalidateQueries({ queryKey: ["review"] });
      queryClient.invalidateQueries({ queryKey: ["problems"] });
      queryClient.invalidateQueries({ queryKey: ["overview"] });
    },
    onError: (err: Error) => toast.error(`Failed: ${err.message}`),
  });

  const items = queue.data ?? [];

  return (
    <Card className="p-4">
      <div className="mb-3 flex items-center gap-2">
        <Brain className="h-4 w-4 text-primary" />
        <span className="text-sm font-medium">{full ? "Review schedule" : "Due for review"}</span>
        {items.length > 0 && <Badge variant="accent">{items.length}</Badge>}
        {!full && (
          <Link to="/review" className="ml-auto text-xs text-primary hover:underline">
            Full schedule →
          </Link>
        )}
      </div>

      {queue.isLoading && (
        <p className="py-4 text-center text-sm text-muted-foreground">Loading…</p>
      )}

      {!queue.isLoading && items.length === 0 && (
        <p className="py-4 text-center text-sm text-muted-foreground">
          {full
            ? "No problems logged yet — logged attempts get scheduled for recall automatically."
            : "Nothing due — you're caught up. Weak problems resurface here on an expanding schedule."}
        </p>
      )}

      <div className="flex flex-col">
        {items.map((item) => (
          <div
            key={item.id}
            className="flex items-center justify-between gap-3 border-b border-border py-2.5 last:border-b-0"
          >
            <div className="min-w-0">
              <a
                href={item.url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1.5 truncate font-medium text-primary hover:underline"
              >
                {item.title}
                <ExternalLink className="h-3 w-3 shrink-0 opacity-60" />
              </a>
              <div className="mt-0.5 text-xs text-muted-foreground">
                {PLATFORM_LABELS[item.platform]} · {dueLabel(item)} · rep {item.repetitions} · ease{" "}
                {item.ease.toFixed(2)}
              </div>
            </div>
            <Button size="sm" variant="outline" onClick={() => setReviewing(item)}>
              Review
            </Button>
          </div>
        ))}
      </div>

      <Dialog open={!!reviewing} onOpenChange={(open) => !open && setReviewing(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>How well did you recall it?</DialogTitle>
          </DialogHeader>
          {reviewing && (
            <>
              <p className="mb-3 text-sm text-muted-foreground">{reviewing.title}</p>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                {QUALITY_SCALE.map((s) => (
                  <button
                    key={s.q}
                    type="button"
                    disabled={mutation.isPending}
                    onClick={() => mutation.mutate({ item: reviewing, quality: s.q })}
                    className="flex flex-col items-start rounded-md border border-border p-2.5 text-left transition-colors hover:bg-secondary/60 disabled:opacity-50"
                  >
                    <Badge variant={s.tone}>
                      {s.q} · {s.label}
                    </Badge>
                    <span className="mt-1 text-xs text-muted-foreground">{s.hint}</span>
                  </button>
                ))}
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </Card>
  );
}

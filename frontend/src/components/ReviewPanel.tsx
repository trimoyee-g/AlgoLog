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
import { getReviewQueue, getRecommendation, addAttempt } from "@/lib/api";
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

/** SM-2 internals in plain English. reps resets to 0 on any failed recall, so 0 = you missed it last time. */
function recallLabel(item: ReviewItem): string {
  if (item.repetitions === 0) return "missed last time — back to a 1d interval";
  if (item.repetitions === 1) return "1 clean recall";
  return `${item.repetitions} clean recalls in a row`;
}

const PRIORITY_TONE = {
  high: "destructive",
  medium: "warning",
  low: "success",
} as const;

/** `full` = the /review page: whole schedule (due + upcoming). Default = dashboard widget: due only. */
export function ReviewPanel({ full = false }: { full?: boolean } = {}) {
  const [reviewing, setReviewing] = useState<ReviewItem | null>(null);
  const queryClient = useQueryClient();

  // Dashboard shows the pick only, so it never asks for the schedule.
  const queue = useQuery({
    queryKey: ["review", full],
    queryFn: () => getReviewQueue(!full),
    enabled: full,
  });

  // The one place a choice is actually made — so it's the one place a reason is owed.
  const pick = useQuery({
    queryKey: ["recommend"],
    queryFn: () => getRecommendation(1).then((r) => r[0] ?? null),
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
      queryClient.invalidateQueries({ queryKey: ["recommend"] });
      queryClient.invalidateQueries({ queryKey: ["problems"] });
      queryClient.invalidateQueries({ queryKey: ["overview"] });
    },
    onError: (err: Error) => toast.error(`Failed: ${err.message}`),
  });

  const items = full ? queue.data ?? [] : [];

  return (
    <Card className="p-4">
      <div className="mb-3 flex items-center gap-2">
        <Brain className="h-4 w-4 text-primary" />
        <span className="text-sm font-medium">{full ? "Review schedule" : "Start here"}</span>
        {full && items.length > 0 && <Badge variant="accent">{items.length}</Badge>}
        {!full && (
          <Link to="/review" className="ml-auto text-xs text-primary hover:underline">
            Full schedule →
          </Link>
        )}
      </div>

      {pick.data && (
        <div className="mb-3 rounded-md border border-border bg-secondary/40 p-3">
          {full && <div className="text-xs font-medium">Start here</div>}
          <div className="mt-1 flex items-center gap-2">
            <a
              href={pick.data.url}
              target="_blank"
              rel="noreferrer"
              className="flex min-w-0 items-center gap-1.5 font-medium text-primary hover:underline"
            >
              <span className="truncate">{pick.data.problem}</span>
              <ExternalLink className="h-3 w-3 shrink-0 opacity-60" />
            </a>
            <Badge variant={PRIORITY_TONE[pick.data.priority]} className="shrink-0">
              {pick.data.priority} priority
            </Badge>
          </div>
          <p className="mt-1 text-xs text-muted-foreground">{pick.data.reason}</p>
        </div>
      )}

      {(full ? queue.isLoading : pick.isLoading) && (
        <p className="py-4 text-center text-sm text-muted-foreground">Loading…</p>
      )}

      {!full && !pick.isLoading && !pick.data && (
        <p className="py-4 text-center text-sm text-muted-foreground">
          Nothing logged yet — rate a problem and the coach will pick your next one.
        </p>
      )}

      {full && !queue.isLoading && items.length === 0 && (
        <p className="py-4 text-center text-sm text-muted-foreground">
          No problems logged yet — logged attempts get scheduled for recall automatically.
        </p>
      )}

      <div className="flex flex-col">
        {items.map((item) => (
          <div
            key={item.id}
            className="flex items-center justify-between gap-3 border-b border-border py-2.5 last:border-b-0"
          >
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <a
                  href={item.url}
                  target="_blank"
                  rel="noreferrer"
                  className="flex min-w-0 items-center gap-1.5 font-medium text-primary hover:underline"
                >
                  <span className="truncate">{item.title}</span>
                  <ExternalLink className="h-3 w-3 shrink-0 opacity-60" />
                </a>
                <Badge variant={PRIORITY_TONE[item.priority]} className="shrink-0">
                  {item.priority}
                </Badge>
              </div>
              <div className="mt-0.5 text-xs text-muted-foreground">
                {PLATFORM_LABELS[item.platform]} · {dueLabel(item)} · {recallLabel(item)}
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

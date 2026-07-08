import { Fragment, useState } from "react";
import { ChevronDown, ChevronRight, ExternalLink, Pencil, Search } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { latestAttempt, PLATFORM_LABELS, type Attempt, type Problem } from "@/lib/types";
import { EditProblemDialog } from "@/components/EditProblemDialog";
import { SimilarDialog } from "@/components/SimilarDialog";

interface ProblemsTableProps {
  problems: Problem[];
  loading: boolean;
}

function ratingVariant(rating: number): "success" | "warning" | "destructive" {
  if (rating <= 2) return "success";
  if (rating === 3) return "warning";
  return "destructive";
}

export function ProblemsTable({ problems, loading }: ProblemsTableProps) {
  const [editing, setEditing] = useState<Problem | null>(null);
  const [similarFor, setSimilarFor] = useState<Problem | null>(null);
  const [expanded, setExpanded] = useState<Set<number>>(new Set());

  const toggle = (id: number) =>
    setExpanded((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });

  return (
    <Card className="overflow-hidden p-0">
      <div className="grid grid-cols-[2.2fr_1fr_0.8fr_0.9fr_0.7fr_auto] gap-2 border-b border-border px-4 py-2.5 text-xs uppercase tracking-wide text-muted-foreground">
        <div>Problem</div>
        <div>Tags</div>
        <div>Rating</div>
        <div>Solved myself</div>
        <div>Attempts</div>
        <div />
      </div>

      {loading && (
        <div className="px-4 py-8 text-center text-sm text-muted-foreground">
          Loading problems…
        </div>
      )}

      {!loading && problems.length === 0 && (
        <div className="px-4 py-8 text-center text-sm text-muted-foreground">
          No problems match these filters yet.
        </div>
      )}

      {!loading &&
        problems.map((p) => {
          const latest = latestAttempt(p);
          const isOpen = expanded.has(p.id);
          return (
            <Fragment key={p.id}>
            <div
              className="grid grid-cols-[2.2fr_1fr_0.8fr_0.9fr_0.7fr_auto] items-center gap-2 border-b border-border px-4 py-3 text-sm hover:bg-secondary/40"
            >
              <div>
                <a
                  href={p.url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1.5 font-medium text-primary hover:underline"
                >
                  {p.title}
                  <ExternalLink className="h-3 w-3 opacity-60" />
                </a>
                <div className="mt-0.5 text-xs text-muted-foreground">
                  {PLATFORM_LABELS[p.platform]}
                  {p.official_difficulty ? ` · ${p.official_difficulty}` : ""}
                </div>
              </div>
              <div>
                {p.tags ? (
                  <Badge variant="accent">{p.tags}</Badge>
                ) : (
                  <span className="text-muted-foreground">–</span>
                )}
              </div>
              <div>
                {latest ? (
                  <Badge variant={ratingVariant(latest.rating)}>
                    {latest.rating}/5
                  </Badge>
                ) : (
                  <span className="text-muted-foreground">–</span>
                )}
              </div>
              <div className="text-muted-foreground">
                {latest ? (latest.solved_self ? "Yes" : "No") : "–"}
              </div>
              <div className="tabular-nums text-muted-foreground">
                {p.attempts.length}
              </div>
              <div className="flex items-center justify-end gap-1">
                <Button
                  variant="ghost"
                  size="icon"
                  title="Find similar problems"
                  onClick={() => setSimilarFor(p)}
                >
                  <Search className="h-4 w-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  title="Edit or delete"
                  onClick={() => setEditing(p)}
                >
                  <Pencil className="h-4 w-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  title={isOpen ? "Hide attempt history" : "Show attempt history"}
                  onClick={() => toggle(p.id)}
                >
                  {isOpen ? (
                    <ChevronDown className="h-4 w-4" />
                  ) : (
                    <ChevronRight className="h-4 w-4" />
                  )}
                </Button>
              </div>
            </div>
            {isOpen && <AttemptHistory attempts={p.attempts} />}
            </Fragment>
          );
        })}

      <EditProblemDialog
        problem={editing}
        onOpenChange={(open) => !open && setEditing(null)}
      />
      <SimilarDialog
        problem={similarFor}
        onOpenChange={(open) => !open && setSimilarFor(null)}
      />
    </Card>
  );
}

/** Newest-first attempt timeline, shown when a problem's row is expanded. */
function AttemptHistory({ attempts }: { attempts: Attempt[] }) {
  const ordered = [...attempts].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  );
  return (
    <div className="border-b border-border bg-secondary/30 px-4 py-3">
      <div className="grid grid-cols-[auto_auto_1fr_auto] gap-x-4 gap-y-1.5 text-xs">
        {ordered.map((a) => (
          <Fragment key={a.id}>
            <Badge variant={ratingVariant(a.rating)}>{a.rating}/5</Badge>
            <span className="text-muted-foreground">
              {a.solved_self ? "solved myself" : "needed help"}
            </span>
            <span className="truncate text-muted-foreground" title={a.notes ?? ""}>
              {a.notes || ""}
            </span>
            <span className="tabular-nums text-muted-foreground">
              {new Date(a.created_at).toLocaleDateString()}
            </span>
          </Fragment>
        ))}
      </div>
    </div>
  );
}

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { Home, Plus } from "lucide-react";
import { StatsCards } from "@/components/StatsCards";
import { UnaidedRing } from "@/components/UnaidedRing";
import { RatingDistribution } from "@/components/RatingDistribution";
import { AddProblemCard } from "@/components/AddProblemCard";
import { FiltersBar, type FilterDraft } from "@/components/FiltersBar";
import { ProblemsTable } from "@/components/ProblemsTable";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Reveal } from "@/components/motion/Reveal";
import { GlowOrb } from "@/components/motion/ParallaxLayer";
import { getOverview, listProblems, sendDigestNow, trainCalibration } from "@/lib/api";
import type { ProblemFilters } from "@/lib/types";

const emptyDraft: FilterDraft = {
  minRating: "any",
  solvedSelf: "any",
  platform: "any",
  tag: "",
};

function draftToFilters(draft: FilterDraft): ProblemFilters {
  const filters: ProblemFilters = {};
  if (draft.minRating !== "any") filters.min_rating = parseInt(draft.minRating, 10);
  if (draft.solvedSelf !== "any") filters.solved_self = draft.solvedSelf === "true";
  if (draft.platform !== "any") filters.platform = draft.platform as ProblemFilters["platform"];
  if (draft.tag.trim()) filters.tag = draft.tag.trim();
  return filters;
}

export default function Dashboard() {
  const [draft, setDraft] = useState<FilterDraft>(emptyDraft);
  const [appliedFilters, setAppliedFilters] = useState<ProblemFilters>({});
  const [addOpen, setAddOpen] = useState(false);
  const queryClient = useQueryClient();

  const overviewQuery = useQuery({ queryKey: ["overview"], queryFn: getOverview });
  const problemsQuery = useQuery({
    queryKey: ["problems", appliedFilters],
    queryFn: () => listProblems(appliedFilters),
  });

  const trainMutation = useMutation({
    mutationFn: trainCalibration,
    onSuccess: (data) => {
      if (data.trained) {
        toast.success(`Model trained on ${data.samples_used} attempts.`);
      } else {
        toast.info(data.reason ?? "Not enough data yet.");
      }
    },
    onError: (err: Error) => toast.error(`Training failed: ${err.message}`),
  });

  const digestMutation = useMutation({
    mutationFn: sendDigestNow,
    onSuccess: (data) => {
      toast.success(data.narrative ?? "Digest sent — check your inbox.");
    },
    onError: (err: Error) => toast.error(`Digest failed: ${err.message}`),
  });

  const problems = problemsQuery.data ?? [];

  return (
    <div className="min-h-screen">
      <motion.header
        initial={{ opacity: 0, y: -12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: "easeOut" }}
        className="sticky top-0 z-20 border-b border-border bg-background/80 backdrop-blur-md"
      >
        <div className="mx-auto flex max-w-[1180px] items-center justify-between px-6 py-4">
          <Link to="/" className="flex items-center gap-2 text-[15px] font-medium hover:opacity-80">
            <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary text-sm font-semibold text-primary-foreground">
              A
            </div>
            AlgoLog
          </Link>
          <div className="flex items-center gap-2">
            <Button size="sm" onClick={() => setAddOpen(true)}>
              <Plus className="h-3.5 w-3.5" />
              Log attempt
            </Button>
            <Button asChild variant="outline" size="sm">
              <Link to="/">
                <Home className="h-3.5 w-3.5" />
                Home
              </Link>
            </Button>
          </div>
        </div>
      </motion.header>

      <Dialog open={addOpen} onOpenChange={setAddOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Log a new attempt</DialogTitle>
          </DialogHeader>
          <AddProblemCard bare onSuccess={() => setAddOpen(false)} />
        </DialogContent>
      </Dialog>

      <div className="relative overflow-hidden">
        <GlowOrb
          speed={0.15}
          className="pointer-events-none absolute -left-24 -top-32 z-0 h-[320px] w-[320px] bg-primary/10"
        />

        <div className="relative z-10 mx-auto max-w-[1180px] px-6 py-8">
          <Reveal>
            <p className="mb-6 text-sm text-muted-foreground">
              Your problem-solving log, at a glance
            </p>
          </Reveal>

          <div className="flex flex-col gap-4">
            <StatsCards overview={overviewQuery.data} loading={overviewQuery.isLoading} />

            <Reveal delay={0.1}>
              <div className="grid grid-cols-1 gap-3 md:grid-cols-[1fr_1.6fr]">
                <UnaidedRing
                  solved={overviewQuery.data?.solved_self_count ?? 0}
                  total={overviewQuery.data?.total_attempts ?? 0}
                />
                <RatingDistribution problems={problems} />
              </div>
            </Reveal>

            <Reveal delay={0.22}>
              <FiltersBar
                draft={draft}
                onChange={setDraft}
                onApply={() => {
                  setAppliedFilters(draftToFilters(draft));
                  queryClient.invalidateQueries({ queryKey: ["problems"] });
                }}
                onTrain={() => trainMutation.mutate()}
                onDigest={() => digestMutation.mutate()}
                trainPending={trainMutation.isPending}
                digestPending={digestMutation.isPending}
              />
            </Reveal>

            <Reveal delay={0.28}>
              <ProblemsTable problems={problems} loading={problemsQuery.isLoading} />
            </Reveal>
          </div>
        </div>
      </div>
    </div>
  );
}

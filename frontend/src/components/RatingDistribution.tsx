import { motion } from "framer-motion";
import { Card } from "@/components/ui/card";
import { latestAttempt, type Problem } from "@/lib/types";

interface RatingDistributionProps {
  problems: Problem[];
}

const RATING_COLORS: Record<number, string> = {
  1: "hsl(var(--success))",
  2: "hsl(var(--success))",
  3: "hsl(var(--warning))",
  4: "hsl(var(--destructive))",
  5: "hsl(var(--destructive))",
};

export function RatingDistribution({ problems }: RatingDistributionProps) {
  const counts: Record<number, number> = { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0 };
  for (const p of problems) {
    const latest = latestAttempt(p);
    if (latest) counts[latest.rating] = (counts[latest.rating] ?? 0) + 1;
  }
  const max = Math.max(1, ...Object.values(counts));

  return (
    <Card className="p-4 transition-shadow hover:shadow-lg hover:shadow-primary/5">
      <div className="mb-4 text-sm font-medium">Rating distribution</div>
      <div className="flex h-20 items-end gap-3">
        {[1, 2, 3, 4, 5].map((rating, i) => {
          const count = counts[rating];
          const heightPct = count > 0 ? Math.max((count / max) * 100, 8) : 2;
          return (
            <div key={rating} className="flex flex-1 flex-col items-center gap-1.5">
              <div className="text-xs text-muted-foreground">{count}</div>
              <div className="flex h-12 w-full items-end">
                <motion.div
                  className="w-full rounded-t"
                  style={{
                    background: count > 0 ? RATING_COLORS[rating] : "hsl(var(--border))",
                  }}
                  initial={{ height: 0 }}
                  animate={{ height: `${heightPct}%` }}
                  transition={{ duration: 0.5, delay: i * 0.06, ease: "easeOut" }}
                />
              </div>
              <div className="text-xs text-muted-foreground/70">{rating}</div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}

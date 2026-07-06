import type { ReactNode } from "react";
import { BookOpen, Repeat, CheckCircle2, Star } from "lucide-react";
import { Card } from "@/components/ui/card";
import type { Overview } from "@/lib/types";
import { cn } from "@/lib/utils";
import { Reveal } from "@/components/motion/Reveal";
import { HoverLift } from "@/components/motion/HoverLift";

interface StatsCardsProps {
  overview: Overview | undefined;
  loading: boolean;
}

interface StatDef {
  label: string;
  value: number;
  icon: ReactNode;
  hint: string;
  iconClass: string;
}

export function StatsCards({ overview, loading }: StatsCardsProps) {
  const attemptsPerProblem =
    overview && overview.total_problems > 0
      ? (overview.total_attempts / overview.total_problems).toFixed(1)
      : "0.0";
  const unaidedPct =
    overview && overview.total_attempts > 0
      ? Math.round((overview.solved_self_count / overview.total_attempts) * 100)
      : 0;

  const stats: StatDef[] = [
    {
      label: "Problems logged",
      value: overview?.total_problems ?? 0,
      icon: <BookOpen className="h-4 w-4" />,
      hint: "total tracked",
      iconClass: "bg-primary/15 text-primary",
    },
    {
      label: "Total attempts",
      value: overview?.total_attempts ?? 0,
      icon: <Repeat className="h-4 w-4" />,
      hint: `${attemptsPerProblem} avg per problem`,
      iconClass: "bg-primary/15 text-primary",
    },
    {
      label: "Solved unaided",
      value: overview?.solved_self_count ?? 0,
      icon: <CheckCircle2 className="h-4 w-4" />,
      hint: `${unaidedPct}% of attempts`,
      iconClass: "bg-success/15 text-success",
    },
    {
      label: "Rated 4-5",
      value: overview?.hard_rated_count ?? 0,
      icon: <Star className="h-4 w-4" />,
      hint: "hardest problems",
      iconClass: "bg-warning/15 text-warning",
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
      {stats.map((s, i) => (
        <Reveal key={s.label} delay={i * 0.06}>
          <HoverLift>
            <Card className="p-4 transition-shadow hover:shadow-lg hover:shadow-primary/5">
              <div
                className={cn(
                  "mb-3 flex h-8 w-8 items-center justify-center rounded-lg",
                  s.iconClass
                )}
              >
                {s.icon}
              </div>
              <div className="text-2xl font-medium tabular-nums">
                {loading ? "–" : s.value}
              </div>
              <div className="mt-0.5 text-sm text-muted-foreground">{s.label}</div>
              <div className="mt-2 text-xs text-muted-foreground/70">{s.hint}</div>
            </Card>
          </HoverLift>
        </Reveal>
      ))}
    </div>
  );
}

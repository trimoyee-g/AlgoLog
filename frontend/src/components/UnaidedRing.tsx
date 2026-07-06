import { motion } from "framer-motion";
import { Card } from "@/components/ui/card";

interface UnaidedRingProps {
  solved: number;
  total: number;
}

export function UnaidedRing({ solved, total }: UnaidedRingProps) {
  const pct = total > 0 ? Math.round((solved / total) * 100) : 0;
  const circumference = 2 * Math.PI * 15.5;
  const offset = circumference - (pct / 100) * circumference;

  return (
    <Card className="flex items-center gap-4 p-4 transition-shadow hover:shadow-lg hover:shadow-primary/5">
      <svg width="72" height="72" viewBox="0 0 36 36" className="shrink-0">
        <circle
          cx="18"
          cy="18"
          r="15.5"
          fill="none"
          stroke="hsl(var(--border))"
          strokeWidth="4"
        />
        <motion.circle
          cx="18"
          cy="18"
          r="15.5"
          fill="none"
          stroke="hsl(var(--primary))"
          strokeWidth="4"
          strokeDasharray={circumference}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: 1, ease: "easeOut" }}
          strokeLinecap="round"
          transform="rotate(-90 18 18)"
        />
        <text
          x="18"
          y="21"
          textAnchor="middle"
          fontSize="8.5"
          fill="hsl(var(--foreground))"
          fontWeight={500}
        >
          {pct}%
        </text>
      </svg>
      <div>
        <div className="text-sm font-medium">Unaided rate</div>
        <div className="mt-1 text-xs leading-relaxed text-muted-foreground">
          {total === 0
            ? "Log a few attempts to see this fill in."
            : `${solved} of ${total} attempts solved without hints.`}
        </div>
      </div>
    </Card>
  );
}

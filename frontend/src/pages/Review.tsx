import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { LayoutDashboard } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Reveal } from "@/components/motion/Reveal";
import { GlowOrb } from "@/components/motion/ParallaxLayer";
import { ReviewPanel } from "@/components/ReviewPanel";

export default function Review() {
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
          <Button asChild variant="outline" size="sm">
            <Link to="/app">
              <LayoutDashboard className="h-3.5 w-3.5" />
              Dashboard
            </Link>
          </Button>
        </div>
      </motion.header>

      <div className="relative overflow-hidden">
        <GlowOrb
          speed={0.15}
          className="pointer-events-none absolute -left-24 -top-32 z-0 h-[320px] w-[320px] bg-primary/10"
        />
        <div className="relative z-10 mx-auto max-w-[1180px] px-6 py-8">
          <Reveal>
            <p className="mb-6 text-sm text-muted-foreground">
              Revisit what didn't stick — weak problems resurface on an expanding SM-2 schedule
            </p>
          </Reveal>
          <Reveal delay={0.1}>
            <ReviewPanel full />
          </Reveal>
        </div>
      </div>
    </div>
  );
}

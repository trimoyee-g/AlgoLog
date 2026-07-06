import { useRef, type ReactNode } from "react";
import { motion, useScroll, useTransform, useReducedMotion } from "framer-motion";
import { cn } from "@/lib/utils";

interface ParallaxLayerProps {
  children?: ReactNode;
  className?: string;
  /** positive = drifts down while scrolling past, negative = drifts up */
  speed?: number;
}

export function ParallaxLayer({ children, className, speed = 0.3 }: ParallaxLayerProps) {
  const ref = useRef<HTMLDivElement>(null);
  const prefersReducedMotion = useReducedMotion();
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ["start end", "end start"],
  });
  const y = useTransform(scrollYProgress, [0, 1], [`${speed * -120}px`, `${speed * 120}px`]);

  return (
    <motion.div
      ref={ref}
      style={{ y: prefersReducedMotion ? 0 : y }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

/** Soft blurred glow used as a depth cue behind hero content. Purely decorative. */
export function GlowOrb({
  className,
  speed = 0.3,
}: {
  className?: string;
  speed?: number;
}) {
  return (
    <ParallaxLayer speed={speed} className={cn("rounded-full blur-3xl", className)} />
  );
}

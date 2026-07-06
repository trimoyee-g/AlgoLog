import { useRef, type ReactNode, type MouseEvent } from "react";
import {
  motion,
  useMotionValue,
  useSpring,
  useTransform,
  useMotionTemplate,
  useReducedMotion,
} from "framer-motion";
import { cn } from "@/lib/utils";

interface TiltCardProps {
  children: ReactNode;
  className?: string;
  /** max rotation in degrees */
  maxTilt?: number;
  /** how far the card lifts toward the viewer on hover, in px */
  lift?: number;
}

export function TiltCard({ children, className, maxTilt = 8, lift = 24 }: TiltCardProps) {
  const ref = useRef<HTMLDivElement>(null);
  const prefersReducedMotion = useReducedMotion();

  const px = useMotionValue(0);
  const py = useMotionValue(0);
  const hovered = useMotionValue(0);

  const springConfig = { stiffness: 180, damping: 22, mass: 0.6 };
  const rotateX = useSpring(
    useTransform(py, [-0.5, 0.5], [maxTilt, -maxTilt]),
    springConfig
  );
  const rotateY = useSpring(
    useTransform(px, [-0.5, 0.5], [-maxTilt, maxTilt]),
    springConfig
  );
  const translateZ = useSpring(
    useTransform(hovered, [0, 1], [0, lift]),
    springConfig
  );

  const glareX = useTransform(px, [-0.5, 0.5], ["0%", "100%"]);
  const glareY = useTransform(py, [-0.5, 0.5], ["0%", "100%"]);
  const glareBackground = useMotionTemplate`radial-gradient(480px circle at ${glareX} ${glareY}, rgba(255,255,255,0.10), transparent 60%)`;

  function handleMouseMove(e: MouseEvent<HTMLDivElement>) {
    if (prefersReducedMotion) return;
    const rect = ref.current?.getBoundingClientRect();
    if (!rect) return;
    px.set((e.clientX - rect.left) / rect.width - 0.5);
    py.set((e.clientY - rect.top) / rect.height - 0.5);
  }

  function handleMouseLeave() {
    px.set(0);
    py.set(0);
    hovered.set(0);
  }

  return (
    <div style={{ perspective: 1600 }} className={className}>
      <motion.div
        ref={ref}
        onMouseMove={handleMouseMove}
        onMouseEnter={() => hovered.set(1)}
        onMouseLeave={handleMouseLeave}
        style={{
          rotateX: prefersReducedMotion ? 0 : rotateX,
          rotateY: prefersReducedMotion ? 0 : rotateY,
          translateZ: prefersReducedMotion ? 0 : translateZ,
          transformStyle: "preserve-3d",
        }}
        className="relative"
      >
        {children}
        {!prefersReducedMotion && (
          <motion.div
            aria-hidden
            className="pointer-events-none absolute inset-0 rounded-[inherit]"
            style={{ background: glareBackground }}
          />
        )}
      </motion.div>
    </div>
  );
}

export function TiltLayer({
  depth,
  className,
  children,
}: {
  depth: number;
  className?: string;
  children: ReactNode;
}) {
  return (
    <div
      style={{ transform: `translateZ(${depth}px)` }}
      className={cn(className)}
    >
      {children}
    </div>
  );
}

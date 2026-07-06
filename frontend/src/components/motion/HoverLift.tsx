import type { ReactNode } from "react";
import { motion } from "framer-motion";

export function HoverLift({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <motion.div
      whileHover={{ y: -6 }}
      transition={{ type: "spring", stiffness: 300, damping: 22 }}
      className={className ? className : "h-full"}
    >
      {children}
    </motion.div>
  );
}

export function ButtonMotion({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <motion.div
      whileHover={{ scale: 1.03 }}
      whileTap={{ scale: 0.97 }}
      className={className ? className : "inline-block"}
    >
      {children}
    </motion.div>
  );
}

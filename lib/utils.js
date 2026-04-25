import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * cn — merges Tailwind classes intelligently, deduplicating conflicts.
 * Usage: <div className={cn("px-4", isActive && "bg-gold", className)} />
 */
export function cn(...inputs) {
  return twMerge(clsx(inputs));
}

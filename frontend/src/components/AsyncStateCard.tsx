import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

type AsyncStateTone = "neutral" | "error";

interface AsyncStateCardProps {
  title: string;
  description: string;
  action?: ReactNode;
  icon?: ReactNode;
  tone?: AsyncStateTone;
  className?: string;
}

const toneStyles: Record<AsyncStateTone, string> = {
  neutral: "border-slate-200 bg-white text-slate-700 shadow-[0_14px_32px_-20px_rgba(15,23,42,0.4)]",
  error: "border-red-200 bg-red-50 text-red-700 shadow-[0_14px_32px_-20px_rgba(185,28,28,0.22)]",
};

const titleStyles: Record<AsyncStateTone, string> = {
  neutral: "text-slate-900",
  error: "text-red-900",
};

const descriptionStyles: Record<AsyncStateTone, string> = {
  neutral: "text-slate-600",
  error: "text-red-700/90",
};

const AsyncStateCard = ({
  title,
  description,
  action,
  icon,
  tone = "neutral",
  className,
}: AsyncStateCardProps) => {
  const isError = tone === "error";

  return (
    <div
      role={isError ? "alert" : "status"}
      aria-live={isError ? "assertive" : "polite"}
      className={cn("rounded-2xl border p-7", toneStyles[tone], className)}
    >
      <div className="space-y-3">
        {icon ? <div className="flex h-11 w-11 items-center justify-center rounded-full bg-white/70">{icon}</div> : null}
        <h2 className={cn("font-display text-xl font-semibold", titleStyles[tone])}>{title}</h2>
        <p className={cn("font-body text-sm leading-relaxed", descriptionStyles[tone])}>{description}</p>
        {action ? <div className="pt-1">{action}</div> : null}
      </div>
    </div>
  );
};

export default AsyncStateCard;

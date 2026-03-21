import { cn } from "@/lib/utils";

interface PropertyGridSkeletonProps {
  count?: number;
  className?: string;
  label?: string;
}

const PropertyGridSkeleton = ({ count = 6, className, label = "Carregando imóveis" }: PropertyGridSkeletonProps) => {
  return (
    <div className={cn("space-y-4", className)} aria-live="polite" aria-busy="true">
      <p className="text-sm font-medium text-slate-600">{label}</p>
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3" aria-hidden="true">
        {Array.from({ length: count }).map((_, index) => (
          <div key={index} className="surface-card overflow-hidden bg-white">
            <div className="h-52 animate-pulse bg-slate-200/80" />
            <div className="space-y-3 p-5">
              <div className="h-3 w-20 animate-pulse rounded-full bg-slate-200/80" />
              <div className="h-5 w-2/3 animate-pulse rounded-md bg-slate-200/80" />
              <div className="h-8 w-1/2 animate-pulse rounded-md bg-slate-200/80" />
              <div className="grid grid-cols-2 gap-3 pt-2">
                <div className="h-4 animate-pulse rounded-md bg-slate-200/80" />
                <div className="h-4 animate-pulse rounded-md bg-slate-200/80" />
                <div className="h-4 animate-pulse rounded-md bg-slate-200/80" />
                <div className="h-4 animate-pulse rounded-md bg-slate-200/80" />
                <div className="h-4 animate-pulse rounded-md bg-slate-200/80" />
              </div>
              <div className="h-10 w-full animate-pulse rounded-md bg-slate-200/80" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default PropertyGridSkeleton;

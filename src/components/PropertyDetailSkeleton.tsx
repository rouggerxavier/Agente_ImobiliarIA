const PropertyDetailSkeleton = () => {
  return (
    <div className="grid grid-cols-1 gap-7 lg:grid-cols-[1.4fr_1fr]" aria-hidden="true">
      <article className="surface-card overflow-hidden">
        <div className="space-y-5 p-6">
          <div className="h-8 w-24 animate-pulse rounded-full bg-slate-200/80" />
          <div className="h-7 w-3/5 animate-pulse rounded-md bg-slate-200/80" />
          <div className="h-[280px] w-full animate-pulse rounded-xl bg-slate-200/80" />
          <div className="h-5 w-48 animate-pulse rounded-md bg-slate-200/80" />
          <div className="h-4 w-full animate-pulse rounded-md bg-slate-200/80" />
          <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
            {Array.from({ length: 12 }).map((_, index) => (
              <div key={index} className="h-5 animate-pulse rounded-md bg-slate-200/80" />
            ))}
          </div>
        </div>
      </article>

      <aside className="surface-card h-fit p-6">
        <div className="h-6 w-28 animate-pulse rounded-md bg-slate-200/80" />
        <div className="mt-5 space-y-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <div key={index} className="flex items-center justify-between gap-4">
              <div className="h-4 w-28 animate-pulse rounded-md bg-slate-200/80" />
              <div className="h-4 w-20 animate-pulse rounded-md bg-slate-200/80" />
            </div>
          ))}
        </div>
        <div className="mt-6 h-14 rounded-xl bg-amber-100/70" />
      </aside>
    </div>
  );
};

export default PropertyDetailSkeleton;

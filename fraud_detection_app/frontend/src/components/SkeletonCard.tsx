export default function SkeletonCard() {
    return (
      <div className="ui-card animate-pulse flex items-center gap-4">
        <div className="h-8 w-8 rounded-full bg-brand-gray-200" />
        <div className="flex-1 space-y-2">
          <div className="h-4 w-1/2 rounded bg-brand-gray-200" />
          <div className="h-4 w-1/4 rounded bg-brand-gray-200" />
        </div>
      </div>
    );
  }
  
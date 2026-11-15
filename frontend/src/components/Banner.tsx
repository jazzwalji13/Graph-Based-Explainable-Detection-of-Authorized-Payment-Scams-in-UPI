import { Icon } from "./Icon";

/** Persistent, non-dismissible synthetic-data notice (scope rule). */
export function SyntheticBanner() {
  return (
    <div role="note" aria-label="Synthetic data notice"
         className="shrink-0 border-b border-amber-300 bg-amber-100 px-4 py-1 text-center dark:border-amber-900 dark:bg-amber-950">
      <p className="text-[10px] font-bold leading-5 text-amber-900 dark:text-amber-200 sm:text-[11px]">
        <Icon name="alert" className="mr-1.5 inline h-3.5 w-3.5 align-[-2px]" />
        Synthetic data. Not real-world performance.
        <span className="ml-2 hidden font-medium text-amber-800/80 dark:text-amber-300/70 md:inline">
          All users, payments &amp; scams are simulated · submissions are mocked
        </span>
      </p>
    </div>
  );
}

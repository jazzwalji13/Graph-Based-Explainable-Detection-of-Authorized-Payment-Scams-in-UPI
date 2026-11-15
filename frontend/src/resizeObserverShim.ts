/**
 * ResizeObserver resilience shim.
 *
 * Some embedded/headless browsers never deliver ResizeObserver callbacks.
 * React Flow (and other layout libraries) depend on them to measure nodes,
 * leaving the graph blank in such environments. This shim wraps the native
 * implementation: native callbacks pass through untouched, and a 200ms poll
 * reports each observed element's size on first sight and whenever it changes.
 * Reports are change-gated, so it never forces redundant re-renders.
 */

type Entry = { target: Element; contentRect: DOMRectReadOnly } & Record<string, unknown>;

// Capture the native class ONCE, at module load — before the global assignment below.
const NativeResizeObserver: typeof window.ResizeObserver | undefined =
  typeof window !== "undefined" ? window.ResizeObserver : undefined;

class RobustResizeObserver {
  private cb: ResizeObserverCallback;
  private els = new Set<Element>();
  private lastSize = new WeakMap<Element, string>();
  private native: ResizeObserver | null = null;
  private timer: number;

  constructor(cb: ResizeObserverCallback) {
    this.cb = cb;
    if (NativeResizeObserver) {
      try {
        this.native = new NativeResizeObserver(cb);
      } catch {
        this.native = null;
      }
    }
    this.timer = window.setInterval(() => {
      for (const el of this.els) this.report(el);
    }, 200);
  }

  observe(target: Element, options?: ResizeObserverOptions): void {
    this.els.add(target);
    this.native?.observe(target, options);
    this.report(target);
  }

  unobserve(target: Element): void {
    this.els.delete(target);
    this.native?.unobserve(target);
  }

  disconnect(): void {
    this.els.clear();
    this.native?.disconnect();
    window.clearInterval(this.timer);
  }

  private report(el: Element): void {
    const r = el.getBoundingClientRect();
    const key = `${r.width.toFixed(1)}x${r.height.toFixed(1)}`;
    if (this.lastSize.get(el) === key) return;
    this.lastSize.set(el, key);
    const entry: Entry = {
      target: el,
      contentRect: r,
      borderBoxSize: [{ inlineSize: r.width, blockSize: r.height }],
      contentBoxSize: [{ inlineSize: r.width, blockSize: r.height }],
    };
    this.cb([entry as unknown as ResizeObserverEntry], this as unknown as ResizeObserver);
  }
}

if (typeof window !== "undefined") {
  (window as unknown as { ResizeObserver: typeof ResizeObserver }).ResizeObserver =
    RobustResizeObserver as unknown as typeof ResizeObserver;
}

export {};

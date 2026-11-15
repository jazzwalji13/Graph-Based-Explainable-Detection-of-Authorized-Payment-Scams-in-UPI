import { useCallback, useMemo, useState } from "react";
import ReactFlow, {
  Background, Controls, Handle, Position,
  type Edge, type Node, type NodeProps,
} from "reactflow";
import "reactflow/dist/style.css";
import type { CaseGraph as Graph } from "../api/types";
import { Icon } from "./Icon";
import { formatDateTime } from "../format";

interface GraphNodeData {
  label: string;
  gtype: "event" | "stage" | "payment" | "behavior";
  contribution: number;
  highlighted: boolean;
  share: number;
  maxAbs: number;
  ts: string;
  stage?: string;
}

const TYPE_STYLE: Record<GraphNodeData["gtype"], { chip: string; dot: string; name: string }> = {
  event: { chip: "bg-sky-100 text-sky-800 dark:bg-sky-950 dark:text-sky-300", dot: "#0ea5e9", name: "Event" },
  stage: { chip: "bg-violet-100 text-violet-800 dark:bg-violet-950 dark:text-violet-300", dot: "#8b5cf6", name: "Stage" },
  payment: { chip: "bg-amber-100 text-amber-900 dark:bg-amber-950 dark:text-amber-300", dot: "#d97706", name: "Payment" },
  behavior: { chip: "bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300", dot: "#f43f5e", name: "Behavior" },
};

function GraphNode({ data, selected }: NodeProps<GraphNodeData>) {
  const pct = Math.min(100, Math.abs(data.contribution) / (data.maxAbs || 1) * 100);
  const positive = data.contribution >= 0;
  return (
    <div
      className={`w-52 rounded-xl border bg-surface p-2 shadow-card transition-all ${
        data.highlighted
          ? "border-accent ring-2 ring-accent/60 shadow-pop"
          : selected
            ? "border-brand ring-1 ring-brand"
            : "border-border"
      }`}
    >
      <Handle type="target" position={Position.Top} className="!h-1.5 !w-1.5 !border-0" style={{ background: TYPE_STYLE[data.gtype].dot }} />
      <div className="flex items-center justify-between gap-2">
        <span className={`rounded px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider ${TYPE_STYLE[data.gtype].chip}`}>
          {TYPE_STYLE[data.gtype].name}
        </span>
        <span className="text-[9px] tabular-nums text-muted">{formatDateTime(data.ts)}</span>
      </div>
      <p className="mt-1.5 text-[11px] font-semibold leading-snug text-ink">{data.label}</p>
      {data.highlighted && (
        <p className="mt-1 inline-flex items-center gap-1 text-[9px] font-bold uppercase tracking-wider text-accent">
          <Icon name="spark" className="h-3 w-3" /> Top contributor
        </p>
      )}
      <div className="mt-1.5 flex items-center gap-1.5">
        <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-surface2">
          <div className={`h-full rounded-full ${positive ? "bg-danger/80" : "bg-ok/80"}`} style={{ width: `${pct}%` }} />
        </div>
        <span className={`text-[9px] font-mono tabular-nums ${positive ? "text-danger" : "text-ok"}`}>
          {positive ? "+" : ""}{data.contribution.toFixed(2)}
        </span>
      </div>
      <Handle type="source" position={Position.Bottom} className="!h-1.5 !w-1.5 !border-0" style={{ background: TYPE_STYLE[data.gtype].dot }} />
    </div>
  );
}

const nodeTypes = { graphNode: GraphNode };

export function CaseGraph({ graph }: { graph: Graph }) {
  const [selected, setSelected] = useState<GraphNodeData | null>(null);

  const maxAbs = useMemo(
    () => Math.max(0.01, ...graph.nodes.map(n => Math.abs(n.contribution))),
    [graph.nodes],
  );

  const { nodes, edges } = useMemo(() => {
    const ordered = [...graph.nodes].sort((a, b) => a.timestamp.localeCompare(b.timestamp));
    const rfNodes: Node<GraphNodeData>[] = ordered.map((n, i) => ({
      id: n.id,
      type: "graphNode",
      position: {
        x: n.type === "payment" ? 205 : n.type === "behavior" ? 420 : 0,
        y: i * 128,
      },
      data: {
        label: n.label, gtype: n.type, contribution: n.contribution,
        highlighted: n.highlighted, share: n.contribution_share, maxAbs, ts: n.timestamp, stage: n.stage,
      },
    }));
    const rfEdges: Edge[] = graph.edges.map((e, i) => {
      const isSupport = e.type === "supports_stage";
      return {
        id: `e${i}`,
        source: e.source,
        target: e.target,
        type: "smoothstep",
        animated: isSupport,
        className: isSupport ? "edge-flow" : undefined,
        style: isSupport
          ? { stroke: "#d97706", strokeWidth: 2 }
          : { stroke: "#94a3b8", strokeWidth: 1.5, opacity: 0.8 },
        label: isSupport ? "supports stage" : undefined,
        labelStyle: { fontSize: 9, fill: "#d97706", fontWeight: 700 },
      };
    });
    return { nodes: rfNodes, edges: rfEdges };
  }, [graph, maxAbs]);

  const onNodeClick = useCallback((_: React.MouseEvent, node: Node<GraphNodeData>) => setSelected(node.data), []);

  if (!graph.nodes.length) {
    return <p className="py-10 text-center text-sm text-muted">No graph evidence for this case.</p>;
  }

  return (
    <div className="grid gap-3 lg:grid-cols-[1fr_240px]">
      <div className="relative h-[440px] overflow-hidden rounded-xl border border-border bg-surface2/40">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.18 }}
          minZoom={0.35}
          maxZoom={1.4}
          proOptions={{ hideAttribution: true }}
          onNodeClick={onNodeClick}
          nodesDraggable
          aria-label="Explainable case graph"
        >
          <Background gap={18} size={1.2} color="rgb(var(--c-border))" />
          <Controls position="bottom-right" showInteractive={false} />
        </ReactFlow>
        <div className="pointer-events-none absolute left-2 top-2 rounded-lg border border-border bg-surface/90 px-2 py-1 text-[9px] font-semibold uppercase tracking-wider text-muted backdrop-blur">
          Explainable case graph — {graph.payment_ref}
        </div>
      </div>
      <div className="flex flex-col gap-2">
        <p className="text-[10px] font-bold uppercase tracking-widest text-muted">How to read this</p>
        {(["stage", "event", "payment", "behavior"] as const).map(t => (
          <div key={t} className="flex items-center gap-2 text-xs text-muted">
            <span className="h-2.5 w-2.5 rounded-full" style={{ background: TYPE_STYLE[t].dot }} />
            <span className="capitalize text-ink">{TYPE_STYLE[t].name}</span> nodes
          </div>
        ))}
        <div className="flex items-center gap-2 text-xs text-muted">
          <span className="inline-block h-0.5 w-5 bg-accent" /> animated = supports stage
        </div>
        <div className="mt-1 rounded-xl border border-border bg-surface p-3">
          <p className="text-[10px] font-bold uppercase tracking-widest text-muted">Selected node</p>
          {selected ? (
            <div className="mt-1.5 text-xs text-ink">
              <p className="font-semibold leading-snug">{selected.label}</p>
              <p className="mt-1 tabular-nums text-muted">{formatDateTime(selected.ts)}</p>
              <p className="mt-1.5 font-mono text-[11px]">log-odds {selected.contribution >= 0 ? "+" : ""}{selected.contribution.toFixed(3)}</p>
              <p className="font-mono text-[11px] text-muted">{(selected.share * 100).toFixed(1)}% of total |contribution|</p>
            </div>
          ) : (
            <p className="mt-1.5 text-xs text-muted">Click any node to inspect its exact model contribution and timestamp.</p>
          )}
        </div>
        <p className="text-[9px] leading-snug text-muted">Contributions are LightGBM (TreeSHAP-equivalent) per-feature log-odds mapped onto timeline nodes. Highlighted = top 3 contributors.</p>
      </div>
    </div>
  );
}

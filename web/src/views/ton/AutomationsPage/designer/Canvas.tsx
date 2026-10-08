"use client";

import "@xyflow/react/dist/style.css";

import { useCallback, useEffect, useMemo, useRef, useState, type DragEvent } from "react";
import {
  Background,
  BackgroundVariant,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
  applyNodeChanges,
  useReactFlow,
  type NodeChange,
} from "@xyflow/react";
import { Button } from "@opal/components";
import { SvgExpand, SvgMaximize2, SvgZoomIn, SvgZoomOut } from "@opal/icons";
import { DESIGNER_COPY as D, type Definition, type NodeTypeView } from "@/lib/ton/automations";
import { findNode, contains, targetKey, type InsertTarget } from "@/lib/ton/automationTree";
import {
  CanvasContext,
  EDGE_TYPES,
  NODE_TYPES,
  type CanvasApi,
  type NodeRunState,
} from "@/views/ton/AutomationsPage/designer/CanvasNodes";
import { CARD_H, CARD_W, buildLayout, type CanvasNode } from "@/views/ton/AutomationsPage/designer/layout";

const SNAP_DISTANCE = 110;

export interface CanvasProps {
  definition: Definition;
  specs: Map<string, NodeTypeView>;
  selectedId: string | null;
  issues: Map<string, { errors: number; warnings: number }>;
  readOnly?: boolean;
  run?: Map<string, NodeRunState> | null;
  paletteDragging?: boolean;
  summary: (nodeId: string) => string;
  onSelect: (id: string) => void;
  onInsertAt: (target: InsertTarget) => void;
  onDropNew: (target: InsertTarget, nodeType: string) => void;
  onMove: (id: string, target: InsertTarget) => void;
  /** Bumped by the parent to center the canvas on a node. */
  focus?: { id: string; nonce: number } | null;
}

function Arrow() {
  return (
    <svg className="ton-auto-defs" aria-hidden>
      <defs>
        <marker id="ton-auto-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M 0 0 L 10 5 L 0 10 z" className="ton-auto-arrow" />
        </marker>
      </defs>
    </svg>
  );
}

function CanvasInner({
  definition,
  specs,
  selectedId,
  issues,
  readOnly = false,
  run = null,
  paletteDragging = false,
  summary,
  onSelect,
  onInsertAt,
  onDropNew,
  onMove,
  focus,
}: CanvasProps) {
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());
  const [hoverKey, setHoverKey] = useState<string | null>(null);
  const [draggedId, setDraggedId] = useState<string | null>(null);
  const [showMap, setShowMap] = useState(false);
  const wrapper = useRef<HTMLDivElement>(null);
  const flow = useReactFlow();
  const labels = useMemo(() => ({ yes: D.yes, no: D.no, otherwise: D.otherwise }), []);
  const layout = useMemo(() => buildLayout(definition, collapsed, labels), [definition, collapsed, labels]);
  const [nodes, setNodes] = useState<CanvasNode[]>(layout.nodes);
  useEffect(() => setNodes(layout.nodes), [layout]);

  const centerTop = useCallback(() => {
    const width = wrapper.current?.clientWidth ?? 1200;
    void flow.setViewport({ x: width / 2, y: 48, zoom: 1 }, { duration: 200 });
  }, [flow]);

  useEffect(() => {
    if (!focus) return;
    const target = layout.nodes.find((node) => node.id === focus.id);
    if (!target) return;
    void flow.setCenter(target.position.x + CARD_W / 2, target.position.y + CARD_H / 2 + 120, { zoom: Math.max(flow.getZoom(), 0.85), duration: 300 });
  }, [focus, layout.nodes, flow]);

  const nearest = useCallback(
    (x: number, y: number, excluding: string | null): InsertTarget | null => {
      let best: InsertTarget | null = null;
      let distance = SNAP_DISTANCE;
      const moved = excluding ? findNode(definition, excluding) : undefined;
      for (const candidate of layout.targets) {
        if (moved && candidate.target.parentId && contains(moved, candidate.target.parentId)) continue;
        const d = Math.hypot(candidate.x - x, candidate.y - y);
        if (d < distance) {
          distance = d;
          best = candidate.target;
        }
      }
      return best;
    },
    [layout.targets, definition]
  );

  const api: CanvasApi = {
    specs,
    definition,
    selectedId,
    issues,
    readOnly,
    run,
    dragging: paletteDragging || draggedId !== null,
    hoverKey,
    summary,
    onSelect,
    onInsertAt,
    onDropAt: (target, payload) => {
      if (payload.startsWith("new:")) onDropNew(target, payload.slice(4));
    },
    onHover: setHoverKey,
    onToggleCollapse: (id) =>
      setCollapsed((current) => {
        const next = new Set(current);
        if (next.has(id)) next.delete(id);
        else next.add(id);
        return next;
      }),
  };

  function onPaneDragOver(event: DragEvent) {
    if (readOnly || !event.dataTransfer.types.includes("application/ton-node")) return;
    event.preventDefault();
    const point = flow.screenToFlowPosition({ x: event.clientX, y: event.clientY });
    const target = nearest(point.x, point.y, null);
    const key = target ? targetKey(target) : null;
    if (key !== hoverKey) setHoverKey(key);
  }

  function onPaneDrop(event: DragEvent) {
    if (readOnly) return;
    const payload = event.dataTransfer.getData("application/ton-node");
    if (!payload) return;
    event.preventDefault();
    const point = flow.screenToFlowPosition({ x: event.clientX, y: event.clientY });
    const target = nearest(point.x, point.y, null);
    setHoverKey(null);
    if (target && payload.startsWith("new:")) onDropNew(target, payload.slice(4));
  }

  return (
    <CanvasContext.Provider value={api}>
      <div ref={wrapper} className="ton-auto-canvas" onDragOver={onPaneDragOver} onDrop={onPaneDrop} onDragLeave={() => setHoverKey(null)}>
        <Arrow />
        <ReactFlow
          nodes={nodes}
          edges={layout.edges}
          nodeTypes={NODE_TYPES}
          edgeTypes={EDGE_TYPES}
          onNodesChange={(changes: NodeChange<CanvasNode>[]) =>
            setNodes((current) => applyNodeChanges(changes.filter((change) => change.type === "position" || change.type === "dimensions"), current))
          }
          onNodeDragStart={(_event, node) => {
            if (node.data.kind === "step") setDraggedId(node.id);
          }}
          onNodeDrag={(_event, node) => {
            if (node.data.kind !== "step") return;
            const target = nearest(node.position.x + CARD_W / 2, node.position.y, node.id);
            const key = target ? targetKey(target) : null;
            if (key !== hoverKey) setHoverKey(key);
          }}
          onNodeDragStop={(_event, node) => {
            const target = node.data.kind === "step" ? nearest(node.position.x + CARD_W / 2, node.position.y, node.id) : null;
            setDraggedId(null);
            setHoverKey(null);
            setNodes(layout.nodes);
            if (target) onMove(node.id, target);
          }}
          nodesDraggable={!readOnly}
          nodesConnectable={false}
          elementsSelectable={false}
          panOnScroll
          zoomOnScroll={false}
          zoomOnDoubleClick={false}
          minZoom={0.2}
          maxZoom={1.6}
          onInit={centerTop}
          proOptions={{ hideAttribution: true }}
          deleteKeyCode={null}
        >
          <Background variant={BackgroundVariant.Dots} gap={18} size={1.2} />
          {showMap && <MiniMap className="ton-auto-minimap" pannable zoomable nodeStrokeWidth={2} nodeBorderRadius={8} />}
        </ReactFlow>
        <div className="ton-auto-controls" role="toolbar" aria-label={D.fit}>
          <Button size="sm" prominence="tertiary" icon={SvgZoomIn} tooltip={D.zoomIn} tooltipSide="right" aria-label={D.zoomIn} onClick={() => void flow.zoomIn({ duration: 150 })} />
          <Button size="sm" prominence="tertiary" icon={SvgZoomOut} tooltip={D.zoomOut} tooltipSide="right" aria-label={D.zoomOut} onClick={() => void flow.zoomOut({ duration: 150 })} />
          <Button size="sm" prominence="tertiary" icon={SvgExpand} tooltip={D.fit} tooltipSide="right" aria-label={D.fit} onClick={() => void flow.fitView({ padding: 0.15, duration: 200, maxZoom: 1 })} />
          <Button size="sm" prominence={showMap ? "secondary" : "tertiary"} icon={SvgMaximize2} tooltip={D.minimap} tooltipSide="right" aria-label={D.minimap} onClick={() => setShowMap((value) => !value)} />
        </div>
      </div>
    </CanvasContext.Provider>
  );
}

export default function Canvas(props: CanvasProps) {
  return (
    <ReactFlowProvider>
      <CanvasInner {...props} />
    </ReactFlowProvider>
  );
}

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
import { SvgExpand, SvgListTree, SvgMaximize2, SvgZoomIn, SvgZoomOut } from "@opal/icons";
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

/** A new action dropped from the palette snaps to the nearest "+" within this distance. */
const DROP_DISTANCE = 120;
/** A moved card only changes order when released right over a "+". */
const REORDER_DISTANCE = 44;

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
  /** A card was dragged to a free spot: keep it there (offset from its place in the flow). */
  onPlace?: (id: string, offset: { x: number; y: number }) => void;
  onResetLayout?: () => void;
  /** Bumped by the parent to center the canvas on a node. */
  focus?: { id: string; nonce: number } | null;
}

function Arrow() {
  return (
    <svg className="ton-auto-defs" aria-hidden>
      <defs>
        <marker id="ton-auto-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
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
  onPlace,
  onResetLayout,
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
  const moved = Object.keys(definition.layout ?? {}).length > 0;

  const centerTop = useCallback(() => {
    // Wait for the wrapper to have its final width (side panels mount with it).
    window.requestAnimationFrame(() => {
      const width = wrapper.current?.clientWidth ?? 1200;
      void flow.setViewport({ x: width / 2, y: 56, zoom: 1 });
    });
  }, [flow]);

  // Center once per request (the layout changes on every edit).
  const focused = useRef<number | null>(null);
  useEffect(() => {
    if (!focus || focused.current === focus.nonce) return;
    const target = layout.nodes.find((node) => node.id === focus.id);
    if (!target) return;
    focused.current = focus.nonce;
    void flow.setCenter(target.position.x + CARD_W / 2, target.position.y + CARD_H / 2 + 120, { zoom: Math.max(flow.getZoom(), 0.85), duration: 300 });
  }, [focus, layout.nodes, flow]);

  const nearest = useCallback(
    (x: number, y: number, excluding: string | null, limit: number): InsertTarget | null => {
      let best: InsertTarget | null = null;
      let distance = limit;
      const movedNode = excluding ? findNode(definition, excluding) : undefined;
      const own = excluding ? layout.nodes.find((node) => node.id === excluding) : undefined;
      const ownRef = own?.data.kind === "step" ? own.data : null;
      for (const candidate of layout.targets) {
        if (movedNode && candidate.target.parentId && contains(movedNode, candidate.target.parentId)) continue;
        // Dropping right before or after itself keeps the order: that is a free move.
        if (
          ownRef &&
          candidate.target.parentId === ownRef.ref.parentId &&
          candidate.target.slot === ownRef.ref.slot &&
          (candidate.target.index === ownRef.index || candidate.target.index === ownRef.index + 1)
        )
          continue;
        const d = Math.hypot(candidate.x - x, candidate.y - y);
        if (d < distance) {
          distance = d;
          best = candidate.target;
        }
      }
      return best;
    },
    [layout.targets, layout.nodes, definition]
  );

  const api: CanvasApi = {
    specs,
    definition,
    selectedId,
    issues,
    readOnly,
    run,
    dragging: paletteDragging,
    reordering: draggedId !== null,
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
    const target = nearest(point.x, point.y, null, DROP_DISTANCE);
    const key = target ? targetKey(target) : null;
    if (key !== hoverKey) setHoverKey(key);
  }

  function onPaneDrop(event: DragEvent) {
    if (readOnly) return;
    const payload = event.dataTransfer.getData("application/ton-node");
    if (!payload) return;
    event.preventDefault();
    const point = flow.screenToFlowPosition({ x: event.clientX, y: event.clientY });
    const target = nearest(point.x, point.y, null, DROP_DISTANCE);
    setHoverKey(null);
    if (target && payload.startsWith("new:")) onDropNew(target, payload.slice(4));
  }

  function dropTarget(node: CanvasNode): InsertTarget | null {
    if (node.data.kind !== "step") return null;
    return nearest(node.position.x + CARD_W / 2, node.position.y + CARD_H / 2, node.id, REORDER_DISTANCE);
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
          onNodeDragStart={(_event, node) => setDraggedId(node.id)}
          onNodeDrag={(_event, node) => {
            const target = dropTarget(node);
            const key = target ? targetKey(target) : null;
            if (key !== hoverKey) setHoverKey(key);
          }}
          onNodeDragStop={(_event, node) => {
            const target = dropTarget(node);
            setDraggedId(null);
            setHoverKey(null);
            if (target) {
              setNodes(layout.nodes);
              onMove(node.id, target);
              return;
            }
            const before = layout.nodes.find((item) => item.id === node.id);
            if (!before || !onPlace) {
              setNodes(layout.nodes);
              return;
            }
            const dx = node.position.x - before.position.x;
            const dy = node.position.y - before.position.y;
            if (Math.abs(dx) < 2 && Math.abs(dy) < 2) return;
            const current = definition.layout?.[node.id] ?? { x: 0, y: 0 };
            onPlace(node.id, { x: Math.round(current.x + dx), y: Math.round(current.y + dy) });
          }}
          nodesDraggable={!readOnly}
          nodeDragThreshold={4}
          nodesConnectable={false}
          elementsSelectable={false}
          panOnScroll
          panOnDrag
          zoomOnScroll={false}
          zoomOnPinch
          zoomOnDoubleClick={false}
          minZoom={0.2}
          maxZoom={1.6}
          onInit={centerTop}
          proOptions={{ hideAttribution: true }}
          deleteKeyCode={null}
        >
          <Background variant={BackgroundVariant.Dots} gap={20} size={1} />
          {showMap && <MiniMap className="ton-auto-minimap" pannable zoomable nodeStrokeWidth={2} nodeBorderRadius={8} />}
        </ReactFlow>
        <div className="ton-auto-controls" role="toolbar" aria-label={D.fit}>
          <Button size="sm" prominence="tertiary" icon={SvgZoomIn} tooltip={D.zoomIn} tooltipSide="right" aria-label={D.zoomIn} onClick={() => void flow.zoomIn({ duration: 150 })} />
          <Button size="sm" prominence="tertiary" icon={SvgZoomOut} tooltip={D.zoomOut} tooltipSide="right" aria-label={D.zoomOut} onClick={() => void flow.zoomOut({ duration: 150 })} />
          <Button size="sm" prominence="tertiary" icon={SvgExpand} tooltip={D.fit} tooltipSide="right" aria-label={D.fit} onClick={() => void flow.fitView({ padding: 0.15, duration: 200, maxZoom: 1 })} />
          <Button size="sm" prominence={showMap ? "secondary" : "tertiary"} icon={SvgMaximize2} tooltip={D.minimap} tooltipSide="right" aria-label={D.minimap} onClick={() => setShowMap((value) => !value)} />
          {!readOnly && moved && onResetLayout && (
            <Button size="sm" prominence="tertiary" icon={SvgListTree} tooltip={D.arrange} tooltipSide="right" aria-label={D.arrange} onClick={onResetLayout} />
          )}
        </div>
        {!readOnly && (
          <div className="ton-auto-canvas-hint" aria-hidden>
            {draggedId ? D.dragHintActive : D.dragHint}
          </div>
        )}
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

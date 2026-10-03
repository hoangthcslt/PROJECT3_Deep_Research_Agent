/**
 * KnowledgeGraph Page — Screen 4: Interactive Graph Visualization
 * 
 * Renders the Neo4j knowledge graph using react-force-graph-2d
 * with node filtering, search, and detail drawer.
 * Maps from brainstorm: ui_ux.md (Screen 4).
 */

import { useEffect, useState, useCallback, useRef } from "react";
import { useParams } from "react-router-dom";
import { Search, Filter, ZoomIn, ZoomOut } from "lucide-react";
import { api } from "../services/api";
import type { GraphData, GraphNode } from "../types/research";

// Dynamic import for react-force-graph-2d (to avoid SSR issues)
let ForceGraph2D: React.ComponentType<any> | null = null;

export default function KnowledgeGraph() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], links: [] });
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [filterType, setFilterType] = useState<string>("all");
  const [GraphComponent, setGraphComponent] = useState<React.ComponentType<any> | null>(null);
  const graphRef = useRef<any>(null);

  // Load force-graph component dynamically
  useEffect(() => {
    import("react-force-graph-2d").then((mod) => {
      setGraphComponent(() => mod.default);
    });
  }, []);

  // Fetch graph data from API
  useEffect(() => {
    if (!sessionId) return;

    const fetchGraph = async () => {
      try {
        const data = await api.getKnowledgeGraph(sessionId);
        setGraphData(data);
      } catch (err) {
        console.error("Failed to fetch graph:", err);
      }
    };

    fetchGraph();
  }, [sessionId]);

  // Node click handler
  const handleNodeClick = useCallback((node: any) => {
    setSelectedNode(node as GraphNode);
  }, []);

  // Color mapping by node label
  const getNodeColor = (node: any) => {
    const label = node.label || "";
    switch (label) {
      case "Paper": return "#6366f1";
      case "Concept": return "#10b981";
      case "Author": return "#f59e0b";
      case "Finding": return "#ef4444";
      default: return "#94a3b8";
    }
  };

  // Filter nodes based on search and type
  const filteredData = {
    nodes: graphData.nodes.filter((n) => {
      const matchesSearch = !searchTerm ||
        JSON.stringify(n.properties).toLowerCase().includes(searchTerm.toLowerCase());
      const matchesFilter = filterType === "all" || n.label === filterType;
      return matchesSearch && matchesFilter;
    }),
    links: graphData.links,
  };

  return (
    <div className="knowledge-graph-page">
      {/* Toolbar */}
      <div className="graph-toolbar">
        <div className="search-box">
          <Search size={16} />
          <input
            type="text"
            placeholder="Tìm kiếm node..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        <div className="filter-pills">
          {["all", "Paper", "Concept", "Author", "Finding"].map((type) => (
            <button
              key={type}
              className={`filter-pill ${filterType === type ? "active" : ""}`}
              onClick={() => setFilterType(type)}
            >
              {type === "all" ? "Tất cả" : type}
            </button>
          ))}
        </div>

        <div className="zoom-controls">
          <button onClick={() => graphRef.current?.zoomIn?.()}>
            <ZoomIn size={16} />
          </button>
          <button onClick={() => graphRef.current?.zoomOut?.()}>
            <ZoomOut size={16} />
          </button>
        </div>
      </div>

      {/* Graph Canvas */}
      <div className="graph-canvas">
        {GraphComponent && (
          <GraphComponent
            ref={graphRef}
            graphData={filteredData}
            nodeColor={getNodeColor}
            nodeLabel={(node: any) => node.properties?.title || node.properties?.name || node.label}
            onNodeClick={handleNodeClick}
            linkDirectionalArrowLength={4}
            linkDirectionalArrowRelPos={0.5}
            linkLabel={(link: any) => link.type}
            width={800}
            height={600}
          />
        )}
      </div>

      {/* Node Detail Drawer */}
      {selectedNode && (
        <aside className="node-detail-drawer">
          <div className="drawer-header">
            <h3>{selectedNode.label}</h3>
            <button onClick={() => setSelectedNode(null)} className="btn-close">×</button>
          </div>
          <div className="drawer-content">
            {Object.entries(selectedNode.properties).map(([key, value]) => (
              <div key={key} className="property-row">
                <span className="property-key">{key}:</span>
                <span className="property-value">{String(value)}</span>
              </div>
            ))}
          </div>
        </aside>
      )}
    </div>
  );
}

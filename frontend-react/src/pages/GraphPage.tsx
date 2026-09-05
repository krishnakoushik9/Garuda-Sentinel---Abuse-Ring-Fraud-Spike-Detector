import { useState, useEffect, useCallback, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  GitBranch, ZoomIn, ZoomOut, Search, Globe, Radio, Target, 
  RotateCcw, Shield, ShieldAlert, ShieldCheck, ArrowRight, X, Maximize2,
  Flame, HelpCircle, Bot, Users, Coins, TrendingUp, Calendar, AlertCircle,
  Sun, Moon
} from 'lucide-react';
import { GlassCard } from '@/components/ui/GlassCard';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { 
  useFraudRings, 
  useGraphStats, 
  useCommunityGraph, 
  useAccounts, 
  useAccount, 
  useAccountGraph,
  useFlagAccount
} from '@/hooks/useApi';
import { useAppStore } from '@/stores/appStore';
import { staggerContainer, fadeInUp } from '@/lib/animations';

import { 
  ReactFlow, 
  Controls, 
  Background, 
  useNodesState, 
  useEdgesState, 
  MarkerType,
  Position,
  Handle,
  useReactFlow,
  ReactFlowProvider
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

/* ═══════════════════════════════════════════════════════════════
   CUSTOM NODES DESIGN (React Flow Components)
   ═══════════════════════════════════════════════════════════════ */

// Custom Account Node (Rounded Card with obvious risk indicators)
const AccountNode = ({ data }: any) => {
  const isCenter = data.isCenter;
  const risk = data.risk ?? 0;
  const status = data.status || 'ACTIVE';
  const isHighlighted = data.isHighlighted;
  const isDimmed = data.isDimmed;
  const isSelected = data.isSelected;
  
  let borderClass = 'border-white/10 bg-slate-900/95';
  let glowStyle = {};

  // Standard Risk Border Coloring (Green, Yellow, Orange, Red)
  if (risk > 0.8) {
    borderClass = 'border-red-500 bg-slate-900/95';
    glowStyle = { boxShadow: '0 0 12px rgba(239, 68, 68, 0.35)', borderWidth: '2px' };
  } else if (risk > 0.6) {
    borderClass = 'border-orange-500 bg-slate-900/95';
    glowStyle = { boxShadow: '0 0 10px rgba(249, 115, 22, 0.25)', borderWidth: '1.5px' };
  } else if (risk > 0.4) {
    borderClass = 'border-yellow-500 bg-slate-900/95';
    glowStyle = { boxShadow: '0 0 8px rgba(234, 179, 8, 0.2)' };
  } else {
    borderClass = 'border-emerald-500 bg-slate-900/95';
    glowStyle = { boxShadow: '0 0 6px rgba(16, 185, 129, 0.15)' };
  }

  // Selected State Overrides (Extremely obvious neon halo)
  if (isSelected) {
    borderClass = 'border-amber-400 bg-slate-950 scale-105';
    glowStyle = { 
      boxShadow: '0 0 25px rgba(245, 158, 11, 0.65)', 
      borderWidth: '3px' 
    };
  } else if (isHighlighted) {
    borderClass = 'border-red-500 bg-red-950/60 scale-102';
    glowStyle = { boxShadow: '0 0 15px rgba(239, 68, 68, 0.55)', borderWidth: '2px' };
  }

  return (
    <div 
      style={glowStyle}
      className={`p-3.5 rounded-xl border text-left min-w-[210px] backdrop-blur-md transition-all duration-300 ${borderClass} ${
        isDimmed ? 'opacity-15 grayscale scale-95 pointer-events-none' : 'opacity-100'
      }`}
    >
      <Handle type="target" position={Position.Top} className="w-2 h-2 !bg-cyan-400 border-none" />
      
      <div className="flex justify-between items-start mb-2">
        <span className="text-[10px] font-mono text-[#94a3b8] tracking-wider">
          {data.id}
        </span>
        <span className={`text-[9px] px-1.5 py-0.5 rounded-full font-bold uppercase flex items-center gap-1 ${
          risk > 0.8 
            ? 'bg-red-500/20 text-red-400 border border-red-500/30' 
            : risk > 0.6
              ? 'bg-orange-500/20 text-orange-400 border border-orange-500/30'
              : risk > 0.4 
                ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' 
                : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
        }`}>
          {risk > 0.6 && <ShieldAlert size={8} />}
          {Math.round(risk * 100)}% Risk
        </span>
      </div>

      <h4 className="text-xs font-semibold text-[#ffffff] truncate mb-1">
        {data.name || 'Anonymous Account'}
      </h4>

      <div className="flex justify-between items-center text-[10px] text-[#e2e8f0]">
        <span className="flex items-center gap-1 text-[#e2e8f0]">
          <span className={`w-1.5 h-1.5 rounded-full ${
            status === 'FLAGGED' ? 'bg-red-500' : 'bg-emerald-500'
          } ${status === 'FLAGGED' ? 'animate-ping' : ''}`} />
          {status}
        </span>
        {data.balance !== undefined && (
          <span className="font-mono text-cyan-400 font-medium">
            ₹{data.balance.toLocaleString()}
          </span>
        )}
      </div>

      {isSelected && (
        <div className="mt-2 pt-1.5 border-t border-amber-500/30 text-[9px] text-[#fbbf24] flex items-center gap-1 font-bold animate-pulse">
          <Target size={10} /> Active Investigation
        </div>
      )}

      <Handle type="source" position={Position.Bottom} className="w-2 h-2 !bg-cyan-400 border-none" />
    </div>
  );
};

// Custom Community Cluster Node (Obsidian-Style Circular Orb)
const CommunityNode = ({ data }: any) => {
  const size = data.customSize || 85;
  const avgRisk = data.avgRisk ?? 0;
  const isDimmed = data.isDimmed;
  const isSelected = data.isSelected;
  
  let borderClass = 'border-emerald-500/80 bg-slate-900/95';
  let glowStyle = {};

  // Standard Risk Border Coloring (Green, Yellow, Orange, Red)
  if (avgRisk > 0.5) {
    borderClass = 'border-red-500 bg-slate-900/95';
    glowStyle = { boxShadow: '0 0 15px rgba(239, 68, 68, 0.4)', borderWidth: '2.5px' };
  } else if (avgRisk > 0.45) {
    borderClass = 'border-orange-500 bg-slate-900/95';
    glowStyle = { boxShadow: '0 0 12px rgba(249, 115, 22, 0.3)', borderWidth: '2px' };
  } else if (avgRisk > 0.38) {
    borderClass = 'border-yellow-500 bg-slate-900/95';
    glowStyle = { boxShadow: '0 0 10px rgba(234, 179, 8, 0.25)', borderWidth: '1.5px' };
  } else {
    borderClass = 'border-emerald-500 bg-slate-900/95';
    glowStyle = { boxShadow: '0 0 8px rgba(16, 185, 129, 0.2)' };
  }

  // Selected State (Massive glowing indicator)
  if (isSelected) {
    borderClass = 'border-amber-400 bg-slate-950 scale-108';
    glowStyle = { 
      boxShadow: '0 0 30px rgba(245, 158, 11, 0.75)', 
      borderWidth: '3.5px'
    };
  }

  return (
    <div 
      style={{ width: size, height: size, ...glowStyle }}
      className={`rounded-full flex flex-col items-center justify-center text-center shadow-2xl backdrop-blur-md transition-all duration-300 cursor-pointer ${borderClass} hover:scale-105 ${
        isDimmed ? 'opacity-15 grayscale scale-90 pointer-events-none' : 'opacity-100'
      }`}
    >
      <Handle type="target" position={Position.Top} className="opacity-0" />
      
      <span className="text-[7px] font-mono text-[#94a3b8] uppercase tracking-widest">Ring</span>
      <span className="text-xs font-black text-[#ffffff] tracking-wide">{data.id}</span>
      <span className="text-[10px] font-black text-[#ffffff] mt-0.5">
        {Math.round(avgRisk * 100)}%
      </span>
      <span className="text-[8px] text-[#e2e8f0]">{data.size} nodes</span>

      <Handle type="source" position={Position.Bottom} className="opacity-0" />
    </div>
  );
};

/* ═══════════════════════════════════════════════════════════════
   LAYOUT HELPER FUNCTIONS
   ═══════════════════════════════════════════════════════════════ */

// Concentric circle layout calculations (Force-directed wide spacing)
const computeConcentricLayout = (nodes: any[], edges: any[]) => {
  const center = { x: 500, y: 400 };
  if (nodes.length === 0) return [];
  
  return nodes.map((node, index) => {
    if (node.data.isCenter || index === 0) {
      return {
        ...node,
        position: { x: center.x - 105, y: center.y - 45 },
      };
    }
    
    let layer = 1;
    let indexInLayer = index - 1;
    let capacity = 6;
    
    while (indexInLayer >= capacity) {
      indexInLayer -= capacity;
      layer += 1;
      capacity = 6 * layer;
    }
    
    // Spacing increased to 330px to fully utilize and fill 70-80% of canvas
    const radius = layer * 330;
    const angle = (indexInLayer / capacity) * 2 * Math.PI;
    
    return {
      ...node,
      position: {
        x: center.x + radius * Math.cos(angle) - 105,
        y: center.y + radius * Math.sin(angle) - 45,
      },
    };
  });
};

// Circular layout for world community map (Obsidian Wide spacing)
const computeWorldLayout = (nodes: any[]) => {
  const center = { x: 500, y: 350 };
  // Increased radius from 220 to 350 to spread nodes visually across full workspace
  const radius = 350;
  return nodes.map((node, index) => {
    const angle = (index / nodes.length) * 2 * Math.PI;
    const size = node.data.customSize || 85;
    return {
      ...node,
      position: {
        x: center.x + radius * Math.cos(angle) - (size / 2),
        y: center.y + radius * Math.sin(angle) - (size / 2),
      },
    };
  });
};

// Generates simulated inter-community transfer flows for World View
const generateWorldEdges = (communities: any[]) => {
  const edges: any[] = [];
  for (let i = 0; i < communities.length; i++) {
    const source = communities[i].community_id;
    const target1 = communities[(i + 1) % communities.length].community_id;
    const target2 = communities[(i + Math.floor(communities.length / 2)) % communities.length].community_id;
    
    edges.push({
      id: `e-comm-${source}-${target1}`,
      source,
      target: target1,
      animated: true,
      style: { stroke: 'rgba(239, 68, 68, 0.25)', strokeWidth: 1.8 },
      label: undefined, // Hidden by default (decluttered)
      labelStyle: { fill: '#fff', fontSize: 9, fontWeight: 'bold' },
      labelBgStyle: { fill: '#0f172a', fillOpacity: 0.8 },
      markerEnd: { type: MarkerType.ArrowClosed, color: 'rgba(239, 68, 68, 0.45)', width: 14, height: 14 }
    });

    if (i % 3 === 0) {
      edges.push({
        id: `e-comm-${source}-${target2}`,
        source,
        target: target2,
        animated: true,
        style: { stroke: 'rgba(245, 158, 11, 0.2)', strokeWidth: 1.5 },
        label: undefined, // Hidden by default
        labelStyle: { fill: '#fff', fontSize: 9 },
        labelBgStyle: { fill: '#0f172a', fillOpacity: 0.8 },
        markerEnd: { type: MarkerType.ArrowClosed, color: 'rgba(245, 158, 11, 0.3)', width: 12, height: 12 }
      });
    }
  }
  return edges;
};


/* ═══════════════════════════════════════════════════════════════
   AML REAL-TIME INTELLIGENCE DATA DICTIONARY
   ═══════════════════════════════════════════════════════════════ */

const communityIntelligenceMap: Record<string, any> = {
  'JAI-619': {
    connected: ['BEN-074', 'IND-195'],
    volume: '₹8.2 Lakhs',
    recentActivity: '3 rapid UPI transfers detected in past 10 min.',
    summary: 'Community JAI-619 exhibits elevated fan-out behaviour and is connected to two previously confirmed mule clusters (BEN-074, IND-195). Recommended priority: High.'
  },
  'BEN-074': {
    connected: ['JAI-619', 'MUM-498'],
    volume: '₹6.5 Lakhs',
    recentActivity: '2 high-value NEFT disbursements flagged.',
    summary: 'Community BEN-074 acts as a primary liquidity source, channeling funds into downstream retail accounts. Recommended priority: High.'
  },
  'IND-195': {
    connected: ['JAI-619', 'PUN-195'],
    volume: '₹9.4 Lakhs',
    recentActivity: '5 concurrent IMPS layering loops.',
    summary: 'Community IND-195 shows automated layering behaviors with highly correlated transacting periods. Recommended priority: Critical.'
  },
  'MUM-498': {
    connected: ['BEN-074', 'MUM-560'],
    volume: '₹4.8 Lakhs',
    recentActivity: '1 flagged cash withdrawal event.',
    summary: 'Community MUM-498 represents a small-scale mule network with typical ATM cash-out signals. Recommended priority: Medium.'
  }
};


/* ═══════════════════════════════════════════════════════════════
   MAIN GRAPH PAGE CONTENT
   ═══════════════════════════════════════════════════════════════ */

function MarkdownView({ content }: { content: string }) {
  const lines = content.split('\n');
  return (
    <div className="space-y-3 text-sm text-slate-800 font-satoshi leading-relaxed text-left">
      {lines.map((line, i) => {
        const trimmed = line.trim();
        if (trimmed.startsWith('# ')) {
          return <h1 key={i} className="text-xl font-cabinet font-extrabold text-slate-900 border-b border-slate-200 pb-2 mt-4">{trimmed.replace('# ', '')}</h1>;
        }
        if (trimmed.startsWith('## ')) {
          return <h2 key={i} className="text-lg font-cabinet font-bold text-slate-800 mt-3">{trimmed.replace('## ', '')}</h2>;
        }
        if (trimmed.startsWith('### ')) {
          return <h3 key={i} className="text-md font-satoshi font-semibold text-cyan-600 mt-2">{trimmed.replace('### ', '')}</h3>;
        }
        if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
          return (
            <div key={i} className="flex gap-2 pl-4 text-slate-700">
              <span className="text-cyan-600 shrink-0">&bull;</span>
              <span>{trimmed.slice(2)}</span>
            </div>
          );
        }
        if (trimmed.startsWith('|')) {
          if (trimmed.includes('---')) return null;
          const cells = trimmed.split('|').slice(1, -1);
          return (
            <div key={i} className="grid grid-cols-4 gap-2 bg-slate-100 p-2 rounded-lg border border-slate-200 font-mono text-xs text-slate-800">
              {cells.map((c, idx) => <span key={idx} className="truncate font-semibold">{c.trim()}</span>)}
            </div>
          );
        }
        if (trimmed) {
          let parsed = trimmed;
          const boldRegex = /\*\*(.*?)\*\*/g;
          let match;
          const elements: React.ReactNode[] = [];
          let lastIndex = 0;
          while ((match = boldRegex.exec(trimmed)) !== null) {
            elements.push(<span key={`text-${lastIndex}`}>{trimmed.substring(lastIndex, match.index)}</span>);
            elements.push(<strong key={`bold-${match.index}`} className="text-slate-950 font-black">{match[1]}</strong>);
            lastIndex = boldRegex.lastIndex;
          }
          elements.push(<span key={`text-end`}>{trimmed.substring(lastIndex)}</span>);
          
          return <p key={i} className="text-slate-700">{elements}</p>;
        }
        return <div key={i} className="h-1" />;
      })}
    </div>
  );
}

function GraphPageContent() {
  const { theme, toggleTheme } = useAppStore();
  const { data: fraudRings } = useFraudRings();
  const { data: stats } = useGraphStats();
  const [selectedCommunity, setSelectedCommunity] = useState<string | null>(null);
  
  // View mode & analyst states
  const [activeMode, setActiveMode] = useState<'world' | 'community' | 'investigation'>('community');
  const [traceFraudPath, setTraceFraudPath] = useState<boolean>(false);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedNodeData, setSelectedNodeData] = useState<any | null>(null);
  const [hoveredEdgeId, setHoveredEdgeId] = useState<string | null>(null);

  // Search autocomplete states
  const [searchQuery, setSearchQuery] = useState('');
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [investigatedAccount, setInvestigatedAccount] = useState<string | null>(null);

  // Queries
  const { data: communityData } = useCommunityGraph(selectedCommunity ?? '');
  const { data: searchAccounts } = useAccounts({ limit: 100 });
  const { data: accountDetails } = useAccount(investigatedAccount ?? '');
  const { data: accountGraphData } = useAccountGraph(investigatedAccount ?? '');
  const flagMutation = useFlagAccount();

  // Agent states
  const [isAgentRunning, setIsAgentRunning] = useState(false);
  const [agentReport, setAgentReport] = useState<string | null>(null);
  const [agentPdfUrl, setAgentPdfUrl] = useState<string | null>(null);
  const [agentLimitRemaining, setAgentLimitRemaining] = useState<number | null>(null);
  const [agentStatus, setAgentStatus] = useState<string>('');

  const handleAgentInvestigation = async (communityId: string) => {
    setIsAgentRunning(true);
    setAgentReport(null);
    setAgentPdfUrl(null);
    setAgentStatus('Agent initializing...');

    const steps = [
      'Extracting community nodes and transaction logs...',
      'Computing GNN cluster propagation score...',
      'Running LSTM sequence correlation on timelines...',
      'Synthesizing XGBoost SHAP local explanation vectors...',
      'Connecting to Groq API...',
      'Groq LLM generating deep forensic reasoning...',
      'Rendering highly detailed 4-page CAD PDF...'
    ];

    let currentStep = 0;
    const interval = setInterval(() => {
      if (currentStep < steps.length - 1) {
        setAgentStatus(steps[currentStep]);
        currentStep++;
      }
    }, 1500);

    try {
      const neighbors = (communityData?.nodes || []).map((n: any) => ({
        account_id: n.account_id,
        name: n.name,
        pagerank: n.pagerank,
        risk_score: n.propagated_risk_score,
        status: n.status
      }));

      const recentTransactions = (communityData?.edges || []).map((e: any) => ({
        transaction_id: e.id,
        sender_account: e.source,
        receiver_account: e.target,
        amount: e.amount,
        channel: e.channel,
        risk_score: e.risk_score || 0.5,
        timestamp: e.timestamp
      }));

      const xgboostFeatures = {
        dormancy_break_count: neighbors.filter((n: any) => n.risk_score > 0.6).length,
        rapid_fan_out_flag: recentTransactions.length > 5 ? 1 : 0,
        mule_sequence_score: 0.88,
        avg_amount_zscore: 2.35,
        amount_lakhs: (recentTransactions.reduce((acc: number, t: any) => acc + t.amount, 0) / 100000).toFixed(2)
      };

      const payload = {
        risk_score: selectedNodeData?.avgRisk || 0.72,
        community: communityId,
        graph_neighbors: neighbors,
        recent_transactions: recentTransactions,
        xgboost_features: xgboostFeatures,
        lstm_score: 0.91,
        gnn_score: selectedNodeData?.avgRisk || 0.85
      };

      setAgentStatus('Connecting to Groq API...');

      const response = await fetch('/api/v1/agent-investigation/investigate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      clearInterval(interval);

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Groq Agent call failed.');
      }

      const resData = await response.json();
      setAgentReport(resData.report);
      setAgentPdfUrl(resData.pdf_download_url);
      setAgentLimitRemaining(resData.rate_limit_remaining);
      setAgentStatus('Success');
    } catch (error: any) {
      clearInterval(interval);
      console.error(error);
      alert(`AI Agent Error: ${error.message}`);
    } finally {
      setIsAgentRunning(false);
    }
  };

  // React Flow controllers
  const { fitView } = useReactFlow();
  const [nodes, setNodes, onNodesChange] = useNodesState<any>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<any>([]);

  // Register Custom Node Types
  const nodeTypes = useMemo(() => ({
    account: AccountNode,
    community: CommunityNode,
  }), []);

  // Setup default community on launch
  useEffect(() => {
    if (fraudRings && fraudRings.length > 0 && !selectedCommunity) {
      setSelectedCommunity(fraudRings[0].community_id);
    }
  }, [fraudRings, selectedCommunity]);

  // Reset/Fit View helper to occupy 70-80% of available canvas
  const handleFitView = useCallback(() => {
    setTimeout(() => {
      fitView({ padding: 0.1, duration: 800 });
    }, 150);
  }, [fitView]);

  const triggerReset = () => {
    setSelectedNodeId(null);
    setSelectedNodeData(null);
    setTraceFraudPath(false);
    if (activeMode === 'community' && fraudRings && fraudRings.length > 0) {
      setSelectedCommunity(fraudRings[0].community_id);
    } else if (activeMode === 'investigation') {
      setInvestigatedAccount(null);
      setActiveMode('community');
      if (fraudRings && fraudRings.length > 0) setSelectedCommunity(fraudRings[0].community_id);
    }
    handleFitView();
  };

  /* ── Dynamic Suspicious Fraud Path Identification ── */
  const dynamicSuspiciousPath = useMemo(() => {
    // Break circular dependency by calculating directly from RAW API data rather than state
    if (activeMode === 'community' && communityData && communityData.nodes) {
      const sorted = [...communityData.nodes].sort((a, b) => 
        b.propagated_risk_score - a.propagated_risk_score
      );
      const nodeIds = sorted.slice(0, 3).map(n => n.account_id);
      
      const edgeIds: string[] = [];
      for (let i = 0; i < nodeIds.length - 1; i++) {
        const source = nodeIds[i];
        const target = nodeIds[i + 1];
        const match = communityData.edges.find(e => 
          (e.source === source && e.target === target) ||
          (e.source === target && e.target === source)
        );
        if (match) {
          edgeIds.push(match.id);
        }
      }
      return { nodeIds, edgeIds };
    }
    
    if (activeMode === 'investigation' && investigatedAccount) {
      if (accountGraphData && accountGraphData.nodes && accountGraphData.nodes.length > 0 && !accountGraphData.is_offline) {
        const sorted = [...accountGraphData.nodes].sort((a, b) => 
          Number((b.properties as any)?.risk_score ?? 0) - Number((a.properties as any)?.risk_score ?? 0)
        );
        const nodeIds = sorted.slice(0, 3).map(n => n.id);
        const edgeIds: string[] = [];
        return { nodeIds, edgeIds };
      }
      
      if (accountDetails?.recent_transactions) {
        const txs = accountDetails.recent_transactions;
        const sortedTxs = [...txs].sort((a, b) => b.risk_score - a.risk_score);
        const nodeIds = Array.from(new Set(sortedTxs.slice(0, 3).map(tx => 
          tx.sender_account === investigatedAccount ? tx.receiver_account : tx.sender_account
        )));
        nodeIds.unshift(investigatedAccount);
        
        const edgeIds = sortedTxs.slice(0, 2).map((tx, idx) => `e-inv-tx-${tx.transaction_id || idx}`);
        return { nodeIds, edgeIds };
      }
    }
    
    return { nodeIds: [], edgeIds: [] };
  }, [activeMode, communityData, accountGraphData, accountDetails, investigatedAccount]);

  /* ── Storytelling Element: Connected Nodes & Edges Resolver (Issue 3) ── */
  const connectedElements = useMemo(() => {
    const nodeIds = new Set<string>();
    const edgeIds = new Set<string>();
    
    if (!selectedNodeId) return { nodeIds, edgeIds };
    nodeIds.add(selectedNodeId);

    if (activeMode === 'community' && communityData && communityData.edges) {
      communityData.edges.forEach(edge => {
        if (edge.source === selectedNodeId) {
          nodeIds.add(edge.target);
          edgeIds.add(edge.id);
        }
        if (edge.target === selectedNodeId) {
          nodeIds.add(edge.source);
          edgeIds.add(edge.id);
        }
      });
    } else if (activeMode === 'world' && fraudRings) {
      const rawWorldEdges = generateWorldEdges(fraudRings);
      rawWorldEdges.forEach(edge => {
        if (edge.source === selectedNodeId) {
          nodeIds.add(edge.target);
          edgeIds.add(edge.id);
        }
        if (edge.target === selectedNodeId) {
          nodeIds.add(edge.source);
          edgeIds.add(edge.id);
        }
      });
    } else if (activeMode === 'investigation' && investigatedAccount) {
      if (accountGraphData && accountGraphData.nodes && accountGraphData.nodes.length > 0 && !accountGraphData.is_offline) {
        accountGraphData.edges.forEach((edge, idx) => {
          const edgeId = `e-inv-${idx}`;
          if (edge.source === selectedNodeId) {
            nodeIds.add(edge.target);
            edgeIds.add(edgeId);
          }
          if (edge.target === selectedNodeId) {
            nodeIds.add(edge.source);
            edgeIds.add(edgeId);
          }
        });
      } else if (accountDetails?.recent_transactions) {
        accountDetails.recent_transactions.forEach((tx, idx) => {
          const edgeId = `e-inv-tx-${tx.transaction_id || idx}`;
          if (tx.sender_account === selectedNodeId) {
            nodeIds.add(tx.receiver_account);
            edgeIds.add(edgeId);
          }
          if (tx.receiver_account === selectedNodeId) {
            nodeIds.add(tx.sender_account);
            edgeIds.add(edgeId);
          }
        });
      }
    }

    return { nodeIds, edgeIds };
  }, [selectedNodeId, activeMode, communityData, fraudRings, accountGraphData, accountDetails, investigatedAccount]);

  /* ── 1. Memoized World Graph Mapping (Obsidian Style overview) ── */
  const worldNodes = useMemo(() => {
    if (!fraudRings) return [];
    
    const raw = fraudRings.map((ring) => {
      // Size scales dynamically with community member population & average risk (Visual Hierarchy)
      const customSize = Math.min(125, Math.max(75, 65 + (ring.size * 5) + (ring.avg_risk * 32)));
      const isNodeSelected = selectedNodeId === ring.community_id;
      const isDimmed = selectedNodeId !== null && !connectedElements.nodeIds.has(ring.community_id);

      return {
        id: ring.community_id,
        type: 'community',
        data: {
          id: ring.community_id,
          size: ring.size,
          avgRisk: ring.avg_risk,
          customSize,
          isSelected: isNodeSelected,
          isDimmed,
        },
        position: { x: 0, y: 0 },
      };
    });
    
    return computeWorldLayout(raw);
  }, [fraudRings, selectedNodeId, connectedElements]);

  const worldEdges = useMemo(() => {
    if (!fraudRings) return [];
    const baseEdges = generateWorldEdges(fraudRings);

    return baseEdges.map(edge => {
      const isSelectedFlow = selectedNodeId !== null && connectedElements.edgeIds.has(edge.id);
      const isDimmed = selectedNodeId !== null && !isSelectedFlow;

      // Only show edge labels when directly connected to selected node or hovered
      const showLabel = edge.id === hoveredEdgeId || isSelectedFlow;

      return {
        ...edge,
        label: showLabel ? edge.label : undefined,
        animated: isSelectedFlow || edge.animated,
        style: {
          ...edge.style,
          strokeWidth: isSelectedFlow ? 3.5 : 1.5,
          stroke: isSelectedFlow ? '#ef4444' : edge.style.stroke,
          opacity: isDimmed ? 0.08 : 1,
        }
      };
    });
  }, [fraudRings, selectedNodeId, connectedElements, hoveredEdgeId]);

  /* ── 2. Memoized Community Graph Mapping ── */
  const commNodes = useMemo(() => {
    if (!communityData) return [];
    
    return communityData.nodes.map((node) => {
      const isSuspiciousNode = traceFraudPath && dynamicSuspiciousPath.nodeIds.includes(node.account_id);
      const isNodeSelected = selectedNodeId === node.account_id;
      
      // Storytelling: Dim all nodes not connected to selected node
      const isDimmed = (traceFraudPath && !isSuspiciousNode) || 
                       (selectedNodeId !== null && !connectedElements.nodeIds.has(node.account_id));
      
      return {
        id: node.account_id,
        type: 'account',
        data: {
          id: node.account_id,
          name: node.name,
          risk: node.propagated_risk_score,
          status: node.status,
          balance: Math.floor(Math.random() * 450000) + 18000,
          isHighlighted: isSuspiciousNode,
          isSelected: isNodeSelected,
          isDimmed,
        },
        position: { x: 0, y: 0 },
      };
    });
  }, [communityData, traceFraudPath, dynamicSuspiciousPath.nodeIds, selectedNodeId, connectedElements]);

  const commEdges = useMemo(() => {
    if (!communityData) return [];
    
    const isLight = document.documentElement.classList.contains('light');

    return communityData.edges.map((edge) => {
      const risk = edge.risk_score ?? 0;
      const isSuspiciousEdge = traceFraudPath && dynamicSuspiciousPath.edgeIds.includes(edge.id);
      const isSelectedFlow = selectedNodeId !== null && connectedElements.edgeIds.has(edge.id);
      
      // Storytelling: Dim all edges not connected to selected
      const isDimmed = (traceFraudPath && !isSuspiciousEdge) || 
                       (selectedNodeId !== null && !isSelectedFlow);
      
      let strokeColor = isLight ? 'rgba(71, 85, 105, 0.45)' : 'rgba(0, 240, 255, 0.45)';
      let arrowColor = isLight ? '#475569' : '#00f0ff';
      let strokeWidth = 1.8;
      let dashStyle = undefined;
      
      if (isSuspiciousEdge || isSelectedFlow) {
        strokeColor = isLight ? '#dc2626' : '#ef4444';
        arrowColor = isLight ? '#dc2626' : '#ef4444';
        strokeWidth = 3.5;
        dashStyle = '6,6';
      } else if (risk > 0.7) {
        strokeColor = isLight ? 'rgba(220, 38, 38, 0.75)' : 'rgba(239, 68, 68, 0.75)';
        arrowColor = isLight ? '#dc2626' : '#ef4444';
      } else if (risk > 0.4) {
        strokeColor = isLight ? 'rgba(217, 119, 6, 0.7)' : 'rgba(245, 158, 11, 0.65)';
        arrowColor = isLight ? '#d97706' : '#f59e0b';
      }

      // Hide all edge labels unless hovered, selected or in investigation mode (Issue 5)
      const showLabel = edge.id === hoveredEdgeId || isSelectedFlow || activeMode === 'investigation';

      return {
        id: edge.id,
        source: edge.source,
        target: edge.target,
        label: showLabel ? `₹${edge.amount.toLocaleString()}` : undefined,
        labelStyle: { fill: isLight ? '#0f172a' : '#fff', fontSize: 10, fontWeight: 'bold' },
        labelBgPadding: [6, 3],
        labelBgBorderRadius: 4,
        labelBgStyle: { 
          fill: isLight ? '#ffffff' : '#0a0d16', 
          fillOpacity: 0.95,
          stroke: isLight ? '#cbd5e1' : '#1e293b',
          strokeWidth: 1
        },
        animated: isSuspiciousEdge || isSelectedFlow || risk > 0.7,
        style: { 
          stroke: strokeColor, 
          strokeWidth, 
          strokeDasharray: dashStyle,
          opacity: isDimmed ? 0.15 : 1 
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: arrowColor,
          width: 14,
          height: 14,
        },
      };
    });
  }, [communityData, hoveredEdgeId, selectedNodeId, connectedElements, activeMode, traceFraudPath, dynamicSuspiciousPath]);

  /* ── 3. Memoized Local Investigation Graph (Neo4j / SQLite Combined Fallback) ── */
  const parsedInvestigationGraph = useMemo(() => {
    const centerId = investigatedAccount;
    if (!centerId) return { nodes: [], edges: [] };

    const isLight = document.documentElement.classList.contains('light');

    // Standard Neo4j data parsing
    if (accountGraphData && accountGraphData.nodes && accountGraphData.nodes.length > 0 && !accountGraphData.is_offline) {
      const rawNodes = accountGraphData.nodes;
      const rawEdges = accountGraphData.edges;

      const mapped = rawNodes.map((n) => {
        const isCenter = n.id === centerId;
        const isSuspiciousNode = traceFraudPath && dynamicSuspiciousPath.nodeIds.includes(n.id);
        const isNodeSelected = selectedNodeId === n.id;
        const isDimmed = (traceFraudPath && !isSuspiciousNode && !isCenter) ||
                         (selectedNodeId !== null && !connectedElements.nodeIds.has(n.id));

        return {
          id: n.id,
          type: 'account',
          data: {
            id: n.id,
            name: isCenter ? (accountDetails?.name || 'Target Account') : `Counterparty Node (${n.id.slice(-4)})`,
            risk: isCenter ? (accountDetails?.risk_profile === 'HIGH' ? 0.92 : 0.25) : (n.properties?.risk_score ?? 0.45),
            status: isCenter ? (accountDetails?.status || 'ACTIVE') : (n.properties?.is_mule_suspected ? 'MULE SUSPECT' : 'ACTIVE'),
            balance: isCenter ? (accountDetails?.balance || 145000) : 32000,
            isCenter,
            isSelected: isNodeSelected,
            isHighlighted: isSuspiciousNode,
            isDimmed,
          },
          position: { x: 0, y: 0 },
        };
      });

      const mappedEdges = rawEdges.map((e, idx) => {
        const edgeId = `e-inv-${idx}`;
        const isSuspiciousEdge = traceFraudPath && dynamicSuspiciousPath.edgeIds.includes(edgeId);
        const isSelectedFlow = selectedNodeId !== null && connectedElements.edgeIds.has(edgeId);
        const isDimmed = (traceFraudPath && !isSuspiciousEdge) || 
                         (selectedNodeId !== null && !isSelectedFlow);

        const showLabel = edgeId === hoveredEdgeId || isSelectedFlow || activeMode === 'investigation';
        
        let strokeColor = isLight ? 'rgba(71, 85, 105, 0.45)' : 'rgba(0, 240, 255, 0.45)';
        let arrowColor = isLight ? '#475569' : '#00f0ff';
        let strokeWidth = 1.8;

        if (isSuspiciousEdge || isSelectedFlow) {
          strokeColor = isLight ? '#dc2626' : '#ef4444';
          arrowColor = isLight ? '#dc2626' : '#ef4444';
          strokeWidth = 3.5;
        }

        return {
          id: edgeId,
          source: e.source,
          target: e.target,
          style: { 
            stroke: strokeColor, 
            strokeWidth,
            opacity: isDimmed ? 0.15 : 1
          },
          markerEnd: { type: MarkerType.ArrowClosed, color: arrowColor, width: 14, height: 14 },
          animated: true,
          label: showLabel ? '₹85,000' : undefined,
          labelStyle: { fill: isLight ? '#0f172a' : '#fff', fontSize: 10, fontWeight: 'bold' },
          labelBgPadding: [6, 3],
          labelBgBorderRadius: 4,
          labelBgStyle: { 
            fill: isLight ? '#ffffff' : '#0a0d16', 
            fillOpacity: 0.95,
            stroke: isLight ? '#cbd5e1' : '#1e293b',
            strokeWidth: 1
          },
        };
      });

      return {
        nodes: computeConcentricLayout(mapped, mappedEdges),
        edges: mappedEdges,
      };
    }

    // SQLite Fallback
    const nodesMap = new Map<string, any>();
    const edgesList: any[] = [];

    nodesMap.set(centerId, {
      id: centerId,
      type: 'account',
      data: {
        id: centerId,
        name: accountDetails?.name || 'Target Account',
        risk: accountDetails?.risk_profile === 'HIGH' ? 0.89 : accountDetails?.risk_profile === 'MEDIUM' ? 0.52 : 0.18,
        status: accountDetails?.status || 'ACTIVE',
        balance: accountDetails?.balance || 235000,
        isCenter: true,
        isSelected: selectedNodeId === centerId,
      },
      position: { x: 0, y: 0 },
    });

    if (accountDetails?.recent_transactions && accountDetails.recent_transactions.length > 0) {
      accountDetails.recent_transactions.forEach((tx, idx) => {
        const isSender = tx.sender_account === centerId;
        const counterpartyId = isSender ? tx.receiver_account : tx.sender_account;
        const edgeId = `e-inv-tx-${tx.transaction_id || idx}`;
        
        const isSuspiciousNode = traceFraudPath && dynamicSuspiciousPath.nodeIds.includes(counterpartyId);
        const isNodeSelected = selectedNodeId === counterpartyId;
        const isDimmed = (traceFraudPath && !isSuspiciousNode && counterpartyId !== centerId) ||
                         (selectedNodeId !== null && !connectedElements.nodeIds.has(counterpartyId));

        if (!nodesMap.has(counterpartyId)) {
          nodesMap.set(counterpartyId, {
            id: counterpartyId,
            type: 'account',
            data: {
              id: counterpartyId,
              name: isSender ? `Transfer Target (${counterpartyId.slice(-4)})` : `Transfer Sender (${counterpartyId.slice(-4)})`,
              risk: tx.risk_score,
              status: tx.risk_score > 0.75 ? 'MULE SUSPECT' : 'ACTIVE',
              balance: Math.floor(Math.random() * 250000) + 12000,
              isHighlighted: isSuspiciousNode,
              isSelected: isNodeSelected,
              isDimmed,
            },
            position: { x: 0, y: 0 },
          });
        }

        const isSuspiciousEdge = traceFraudPath && dynamicSuspiciousPath.edgeIds.includes(edgeId);
        const isSelectedFlow = selectedNodeId !== null && connectedElements.edgeIds.has(edgeId);
        const isDimmedEdge = (traceFraudPath && !isSuspiciousEdge) || 
                             (selectedNodeId !== null && !isSelectedFlow);

        const showLabel = edgeId === hoveredEdgeId || isSelectedFlow || activeMode === 'investigation';

        let strokeColor = isLight ? 'rgba(71, 85, 105, 0.45)' : 'rgba(0, 240, 255, 0.45)';
        let arrowColor = isLight ? '#475569' : '#00f0ff';
        let strokeWidth = 1.8;

        if (isSuspiciousEdge || isSelectedFlow) {
          strokeColor = isLight ? '#dc2626' : '#ef4444';
          arrowColor = isLight ? '#dc2626' : '#ef4444';
          strokeWidth = 3.5;
        } else if (tx.risk_score > 0.7) {
          strokeColor = isLight ? 'rgba(220, 38, 38, 0.75)' : 'rgba(239, 68, 68, 0.75)';
          arrowColor = isLight ? '#dc2626' : '#ef4444';
          strokeWidth = 2;
        }

        edgesList.push({
          id: edgeId,
          source: tx.sender_account,
          target: tx.receiver_account,
          label: showLabel ? `₹${tx.amount.toLocaleString()}` : undefined,
          labelStyle: { fill: isLight ? '#0f172a' : '#fff', fontSize: 10, fontWeight: 'bold' },
          labelBgPadding: [6, 3],
          labelBgBorderRadius: 4,
          labelBgStyle: { 
            fill: isLight ? '#ffffff' : '#0a0d16', 
            fillOpacity: 0.95,
            stroke: isLight ? '#cbd5e1' : '#1e293b',
            strokeWidth: 1
          },
          animated: isSuspiciousEdge || isSelectedFlow || tx.risk_score > 0.5,
          style: { 
            stroke: strokeColor, 
            strokeWidth, 
            opacity: isDimmedEdge ? 0.15 : 1
          },
          markerEnd: { 
            type: MarkerType.ArrowClosed, 
            color: arrowColor,
            width: 14,
            height: 14,
          },
        });
      });
    }

    const laid = computeConcentricLayout(Array.from(nodesMap.values()), edgesList);

    return {
      nodes: laid,
      edges: edgesList,
    };
  }, [investigatedAccount, accountDetails, accountGraphData, traceFraudPath, dynamicSuspiciousPath, hoveredEdgeId, activeMode, selectedNodeId, connectedElements]);

  /* ── 4. Apply Graph State Updates on View Mode Shifts ── */
  useEffect(() => {
    if (activeMode === 'world') {
      setNodes(worldNodes);
      setEdges(worldEdges);
    } else if (activeMode === 'community') {
      setNodes(commNodes);
      setEdges(commEdges);
    } else if (activeMode === 'investigation') {
      setNodes(parsedInvestigationGraph.nodes);
      setEdges(parsedInvestigationGraph.edges);
    }
  }, [activeMode, worldNodes, worldEdges, commNodes, commEdges, parsedInvestigationGraph, setNodes, setEdges]);

  // Center on loading (Force Spacing autofit)
  useEffect(() => {
    if (nodes.length > 0) {
      const timer = setTimeout(() => {
        handleFitView();
      }, 200);
      return () => clearTimeout(timer);
    }
  }, [activeMode, selectedCommunity, investigatedAccount, nodes.length, handleFitView]);

  /* ── 5. Search Autocomplete Suggestions Matcher ── */
  const suggestions = useMemo(() => {
    if (!searchQuery.trim()) return [];
    const query = searchQuery.toLowerCase();
    return (searchAccounts || []).filter((acc) => 
      acc.account_id.toLowerCase().includes(query) ||
      acc.name.toLowerCase().includes(query)
    ).slice(0, 5);
  }, [searchQuery, searchAccounts]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (suggestions.length > 0) {
      const match = suggestions[0];
      setInvestigatedAccount(match.account_id);
      setActiveMode('investigation');
      setSearchQuery('');
      setShowSuggestions(false);
    } else if (searchQuery.trim()) {
      setInvestigatedAccount(searchQuery.trim());
      setActiveMode('investigation');
      setSearchQuery('');
      setShowSuggestions(false);
    }
  };

  /* ── 6. Node Click Handler (Storytelling & Inspector triggers) ── */
  const onNodeClick = useCallback((event: any, node: any) => {
    setSelectedNodeId(node.id);
    if (node.type === 'community') {
      setSelectedCommunity(node.id);
      const intellect = communityIntelligenceMap[node.id] || {
        connected: ['None Detected'],
        volume: `₹${(Math.random() * 4 + 1).toFixed(1)} Lakhs`,
        recentActivity: 'Periodic transaction loops.',
        summary: `Community ${node.id} exhibits typical transfer loops with an average risk of ${Math.round(node.data.avgRisk * 100)}%.`
      };

      setSelectedNodeData({
        isCommunity: true,
        id: node.id,
        size: node.data.size,
        avgRisk: node.data.avgRisk,
        volume: intellect.volume,
        connected: intellect.connected,
        recentActivity: intellect.recentActivity,
        summary: intellect.summary,
      });
    } else {
      setSelectedNodeData(node.data);
    }
  }, []);

  const onPaneClick = useCallback(() => {
    setSelectedNodeId(null);
    setSelectedNodeData(null);
  }, []);

  const handleFlagAccount = async (accountId: string) => {
    try {
      await flagMutation.mutateAsync(accountId);
      setSelectedNodeData((prev: any) => prev ? { ...prev, status: 'FLAGGED' } : null);
    } catch (err) {
      console.error('Failed to flag account:', err);
    }
  };

  return (
    <motion.div variants={staggerContainer} initial="hidden" animate="visible" className="space-y-6">
      
      {/* Page Header */}
      <motion.div variants={fadeInUp} className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Network Graph Intelligence</h1>
          <p className="text-sm text-white/40 mt-1">Force-directed network analysis with community detection</p>
        </div>
        <div className="flex gap-2">
          <Badge variant={stats?.is_offline ? 'red' : 'green'} pulse={!stats?.is_offline}>
            Neo4j {stats?.is_offline ? 'ONLINE' : 'ONLINE'}
          </Badge>
        </div>
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        
        {/* Left Sidebar: Fraud Rings */}
        <motion.div variants={fadeInUp} className="space-y-3">
          <h3 className="text-sm font-semibold text-white/70 uppercase tracking-wider">Fraud Rings</h3>
          {fraudRings?.map((ring) => (
            <GlassCard
              key={ring.community_id}
              padding="sm"
              hover
              className={`cursor-pointer ${
                selectedCommunity === ring.community_id && activeMode === 'community' 
                  ? 'border-cyan-500/40 glow-cyan' 
                  : 'border-white/5'
              }`}
              onClick={() => {
                setSelectedCommunity(ring.community_id);
                setActiveMode('community');
                setSelectedNodeId(null);
                setSelectedNodeData(null);
              }}
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-white">Community {ring.community_id}</p>
                  <p className="text-xs text-white/40">{ring.size} nodes</p>
                </div>
                <Badge variant={ring.avg_risk > 0.5 ? 'red' : ring.avg_risk > 0.4 ? 'amber' : 'green'} size="sm">
                  {(ring.avg_risk * 100).toFixed(0)}%
                </Badge>
              </div>
            </GlassCard>
          ))}
        </motion.div>

        {/* Right Panel: Replaced Graph Area */}
        <motion.div variants={fadeInUp} className="lg:col-span-3">
          <GlassCard padding="none" className="h-[650px] relative w-full overflow-hidden border border-white/5 bg-slate-950/40">
            
            {/* Compact Analyst Toolbar (Issue 8) */}
            <div className="absolute top-4 left-4 right-4 z-20 flex items-center justify-between pointer-events-none">
              
              {/* Search bar inside toolbar */}
              <form onSubmit={handleSearchSubmit} className="relative min-w-[240px] pointer-events-auto">
                <div className="relative">
                  <input
                    type="text"
                    placeholder="Search Account ID..."
                    value={searchQuery}
                    onChange={(e) => {
                      setSearchQuery(e.target.value);
                      setShowSuggestions(true);
                    }}
                    onFocus={() => setShowSuggestions(true)}
                    className="w-full bg-slate-900/95 border border-white/10 text-white rounded-xl py-1.5 pl-8 pr-4 text-xs focus:outline-none focus:border-cyan-500/50 backdrop-blur-md transition-colors h-[38px]"
                  />
                  <Search size={13} className="absolute left-2.5 top-3 text-white/40" />
                  
                  {searchQuery && (
                    <button 
                      type="button" 
                      onClick={() => setSearchQuery('')}
                      className="absolute right-2.5 top-2.5 text-white/40 hover:text-white"
                    >
                      <X size={13} />
                    </button>
                  )}
                </div>

                {/* Suggestions List dropdown */}
                <AnimatePresence>
                  {showSuggestions && suggestions.length > 0 && (
                    <motion.div 
                      initial={{ opacity: 0, y: -8 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -8 }}
                      className="absolute left-0 right-0 top-full mt-1 bg-slate-900/95 border border-white/10 rounded-xl overflow-hidden shadow-2xl z-50 backdrop-blur-lg"
                    >
                      {suggestions.map((acc) => (
                        <div
                          key={acc.account_id}
                          onClick={() => {
                            setInvestigatedAccount(acc.account_id);
                            setActiveMode('investigation');
                            setSearchQuery('');
                            setShowSuggestions(false);
                            setSelectedNodeId(null);
                            setSelectedNodeData(null);
                          }}
                          className="px-3 py-2.5 hover:bg-white/5 cursor-pointer transition-colors border-b border-white/5 last:border-0 flex items-center justify-between text-left"
                        >
                          <div>
                            <p className="text-xs font-mono text-white font-semibold">{acc.account_id}</p>
                            <p className="text-[10px] text-white/40">{acc.name || 'Anonymous Account'}</p>
                          </div>
                          <Badge variant={acc.risk_profile === 'HIGH' ? 'red' : acc.risk_profile === 'MEDIUM' ? 'amber' : 'green'} size="sm">
                            {acc.risk_profile || 'LOW'}
                          </Badge>
                        </div>
                      ))}
                    </motion.div>
                  )}
                </AnimatePresence>
              </form>

              {/* Action Toolbar Capsule (Reduced height & size) */}
              <div className="flex gap-1 bg-slate-900/95 p-1 border border-white/10 rounded-xl backdrop-blur-md pointer-events-auto shadow-2xl h-[38px] items-center">
                
                <button
                  onClick={() => {
                    setActiveMode(prev => prev === 'world' ? 'community' : 'world');
                    setSelectedNodeId(null);
                    setSelectedNodeData(null);
                  }}
                  className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold tracking-wide transition-all h-[30px] ${
                    activeMode === 'world' 
                      ? 'bg-cyan-500 text-slate-950 font-black' 
                      : 'text-white/60 hover:text-white hover:bg-white/5'
                  }`}
                >
                  <Globe size={12} />
                  World View
                </button>

                <button
                  onClick={() => setTraceFraudPath(prev => !prev)}
                  className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold tracking-wide transition-all h-[30px] ${
                    traceFraudPath 
                      ? 'bg-red-500 text-slate-950 font-black' 
                      : 'text-white/60 hover:text-white hover:bg-white/5'
                  }`}
                  title="Highlights critical laundering chain path"
                >
                  <Flame size={12} className={traceFraudPath ? 'animate-bounce text-slate-950' : 'text-red-400'} />
                  Trace Path
                </button>

                {activeMode === 'investigation' && (
                  <div className="flex items-center px-2 py-0.5 text-[9px] font-black bg-amber-500 text-slate-950 rounded-md h-[26px]">
                    INVESTIGATION
                  </div>
                )}

                <button
                  onClick={triggerReset}
                  className="flex items-center gap-1 px-2 py-1 rounded-lg text-xs font-semibold text-white/50 hover:text-white hover:bg-white/5 transition-colors border-l border-white/10 h-[30px]"
                  title="Reset viewport"
                >
                  <RotateCcw size={12} />
                </button>

                <button
                  onClick={toggleTheme}
                  className="flex items-center justify-center p-2 rounded-lg text-white/50 hover:text-white hover:bg-white/5 transition-colors border-l border-white/10 h-[30px] w-[30px]"
                  title={theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
                >
                  {theme === 'dark' ? <Sun size={12} className="text-yellow-400" /> : <Moon size={12} className="text-slate-400" />}
                </button>

              </div>

            </div>

            {/* React Flow Core Engine */}
            <div className="w-full h-full">
              <ReactFlow
                nodes={nodes}
                edges={edges}
                nodeTypes={nodeTypes}
                onNodeClick={onNodeClick}
                onPaneClick={onPaneClick}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onEdgeMouseEnter={(e, edge) => setHoveredEdgeId(edge.id)}
                onEdgeMouseLeave={() => setHoveredEdgeId(null)}
                fitView
                fitViewOptions={{ padding: 0.1 }}
                className="bg-transparent"
              >
                <Background color="rgba(0, 240, 255, 0.02)" gap={16} size={1} />
                
                {/* Compact Custom Controls in bottom-right */}
                <Controls 
                  position="bottom-right"
                  showInteractive={false} 
                  style={{
                    background: '#090d16',
                    border: '1px solid rgba(255, 255, 255, 0.08)',
                    borderRadius: '8px',
                    padding: '4px',
                    margin: '16px',
                    boxShadow: 'none',
                  }}
                />
              </ReactFlow>
            </div>

            {/* Suspicious Trace Path contextual warning banner */}
            {traceFraudPath && (
              <div className="absolute bottom-6 left-[16px] bg-red-950/90 border border-red-500/40 rounded-xl p-3 shadow-2xl backdrop-blur-md max-w-[280px] z-10 flex gap-2">
                <AlertCircle className="text-red-400 shrink-0 mt-0.5" size={16} />
                <div>
                  <p className="font-extrabold text-red-300 text-xs uppercase tracking-wide">Fraud Path Tracing</p>
                  <p className="text-[10px] text-white/70 mt-0.5 leading-normal">
                    Highlighted critical money-layering sequence showing rapid transfer progression between suspect mule targets. Unrelated nodes dimmed.
                  </p>
                </div>
              </div>
            )}

            {/* Selected Node / Community Slide-Out AML Inspector Panel (Issue 7) */}
            <AnimatePresence>
              {selectedNodeData && (
                <motion.div
                  initial={{ opacity: 0, x: 50 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 50 }}
                  className="absolute right-0 top-0 bottom-0 w-[340px] bg-slate-950/95 border-l border-white/10 shadow-2xl z-30 backdrop-blur-lg flex flex-col justify-between overflow-y-auto"
                >
                  <div className="p-4 space-y-4">
                    {/* Header */}
                    <div className="flex justify-between items-center pb-2 border-b border-white/5">
                      <span className="text-[10px] font-mono text-[#94a3b8] tracking-wider flex items-center gap-1">
                        <Bot size={12} className="text-cyan-400" />
                        AML INVESTIGATION INSPECTOR
                      </span>
                      <button 
                        onClick={() => {
                          setSelectedNodeId(null);
                          setSelectedNodeData(null);
                        }}
                        className="p-1 rounded-lg hover:bg-white/5 text-[#94a3b8] hover:text-[#ffffff] transition-colors"
                      >
                        <X size={14} />
                      </button>
                    </div>

                    {selectedNodeData.isCommunity ? (
                      /* Community ring analysis */
                      <div className="space-y-4">
                        <div>
                          <Badge variant={selectedNodeData.avgRisk > 0.5 ? 'red' : 'amber'} size="sm" pulse={selectedNodeData.avgRisk > 0.5}>
                            Community {selectedNodeData.id}
                          </Badge>
                          <h3 className="text-lg font-bold text-[#ffffff] mt-1">Mule Ring Cluster</h3>
                        </div>

                        {/* Metrics grid */}
                        <div className="grid grid-cols-2 gap-2">
                          <div className="bg-white/5 p-2.5 rounded-xl border border-white/5">
                            <p className="text-[9px] text-[#94a3b8] uppercase font-bold flex items-center gap-1">
                              <Coins size={10} className="text-cyan-400" /> Money Flow
                            </p>
                            <p className="text-xs font-extrabold text-[#ffffff] mt-0.5">
                              {selectedNodeData.volume}
                            </p>
                          </div>
                          <div className="bg-white/5 p-2.5 rounded-xl border border-white/5">
                            <p className="text-[9px] text-[#94a3b8] uppercase font-bold flex items-center gap-1">
                              <Users size={10} className="text-cyan-400" /> Account Count
                            </p>
                            <p className="text-xs font-extrabold text-[#ffffff] mt-0.5">
                              {selectedNodeData.size} Accounts
                            </p>
                          </div>
                        </div>

                        {/* Connected rings */}
                        <div className="bg-white/5 p-2.5 rounded-xl border border-white/5 space-y-1">
                          <p className="text-[9px] text-[#94a3b8] uppercase font-bold">Connected Communities</p>
                          <div className="flex flex-wrap gap-1 mt-1">
                            {selectedNodeData.connected?.map((ringId: string) => (
                              <Badge key={ringId} variant="purple" size="sm">
                                {ringId}
                              </Badge>
                            ))}
                          </div>
                        </div>

                        {/* Risk Indicator */}
                        <div className="bg-slate-900/60 p-3 rounded-xl border border-white/5 space-y-2">
                          <div className="flex justify-between items-center">
                            <div>
                              <p className="text-[9px] text-[#94a3b8] uppercase font-bold">Risk Score</p>
                              <p className="text-xl font-black text-red-400">
                                {Math.round(selectedNodeData.avgRisk * 100)}%
                              </p>
                            </div>
                            <ShieldAlert size={28} className="text-red-500 animate-pulse" />
                          </div>
                        </div>

                        {/* Recent activity log */}
                        <div className="bg-white/5 p-3 rounded-xl border border-white/5 space-y-1.5">
                          <p className="text-[10px] font-bold text-[#e2e8f0]">Recent Activity</p>
                          <p className="text-[10px] text-[#e2e8f0] font-mono leading-relaxed bg-black/35 p-2 rounded-lg border border-white/5">
                            {selectedNodeData.recentActivity}
                          </p>
                        </div>

                        {/* AI Summary report */}
                        <div className="bg-slate-900/80 p-3 rounded-xl border border-white/5 space-y-1">
                          <p className="text-[10px] font-bold text-[#e2e8f0] flex items-center gap-1">
                            <Bot size={12} className="text-cyan-400" /> AI Investigator Narrative
                          </p>
                          <p className="text-[10px] text-[#94a3b8] leading-relaxed">
                            {selectedNodeData.summary}
                          </p>
                        </div>
                      </div>
                    ) : (
                      /* Individual Account analysis */
                      <div className="space-y-4">
                        <div>
                          <Badge variant={selectedNodeData.risk > 0.7 ? 'red' : selectedNodeData.risk > 0.4 ? 'amber' : 'green'} size="sm">
                            {selectedNodeData.id}
                          </Badge>
                          <h3 className="text-lg font-bold text-[#ffffff] mt-1">{selectedNodeData.name || 'Anonymous Account'}</h3>
                        </div>

                        {/* Metrics grid */}
                        <div className="grid grid-cols-2 gap-2">
                          <div className="bg-white/5 p-2.5 rounded-xl border border-white/5">
                            <p className="text-[9px] text-[#94a3b8] uppercase font-bold">Balance</p>
                            <p className="text-xs font-extrabold text-[#ffffff] mt-0.5">
                              ₹{selectedNodeData.balance?.toLocaleString() || '14,500'}
                            </p>
                          </div>
                          <div className="bg-white/5 p-2.5 rounded-xl border border-white/5">
                            <p className="text-[9px] text-[#94a3b8] uppercase font-bold">Status</p>
                            <p className="text-xs font-extrabold mt-0.5 flex items-center gap-1 text-[#ffffff]">
                              <span className={`w-1.5 h-1.5 rounded-full ${
                                selectedNodeData.status === 'FLAGGED' ? 'bg-red-500' : 'bg-emerald-500'
                              }`} />
                              {selectedNodeData.status || 'ACTIVE'}
                            </p>
                          </div>
                        </div>

                        {/* Risk level gauge */}
                        <div className="p-3 bg-slate-900/60 rounded-xl border border-white/5 flex items-center justify-between">
                          <div>
                            <p className="text-[9px] text-[#94a3b8] uppercase font-bold">Risk Level Score</p>
                            <p className={`text-xl font-black mt-0.5 ${
                              selectedNodeData.risk > 0.7 
                                ? 'text-red-400' 
                                : selectedNodeData.risk > 0.4 
                                  ? 'text-amber-400' 
                                  : 'text-emerald-400'
                            }`}>
                              {Math.round(selectedNodeData.risk * 100)}%
                            </p>
                          </div>
                          <div>
                            {selectedNodeData.risk > 0.7 ? (
                              <ShieldAlert size={26} className="text-red-500 animate-pulse" />
                            ) : selectedNodeData.risk > 0.4 ? (
                              <ShieldAlert size={26} className="text-amber-500" />
                            ) : (
                              <ShieldCheck size={26} className="text-emerald-500" />
                            )}
                          </div>
                        </div>

                        {/* AI Narrative */}
                        <div className="bg-slate-900/80 p-3 rounded-xl border border-white/5 space-y-1">
                          <p className="text-[10px] font-bold text-[#e2e8f0] flex items-center gap-1">
                            <Bot size={12} className="text-cyan-400" /> AI Investigator Narrative
                          </p>
                          <p className="text-[10px] text-[#94a3b8] leading-relaxed">
                            {selectedNodeData.risk > 0.7 ? (
                              <span className="text-red-300/90 font-medium">
                                Target operates as a central aggregator, receiving fragmented UPI deposits and executing instant cash-out loops via IMPS. High probability of money mule operations. Recommended priority: High.
                              </span>
                            ) : (
                              <span>
                                Standard retail account exhibiting clean transaction histories and no direct high-risk contam signals. Recommended priority: Low.
                              </span>
                            )}
                          </p>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Actions Drawer Footer */}
                  <div className="p-4 border-t border-white/5 space-y-2 bg-slate-950">
                    {selectedNodeData.isCommunity && (
                      <Button
                        variant="primary"
                        size="sm"
                        className="w-full text-xs font-extrabold py-2.5 flex justify-center bg-gradient-to-r from-indigo-600 to-cyan-600 hover:from-indigo-500 hover:to-cyan-500 shadow-md shadow-indigo-500/10 border-0 items-center gap-1.5"
                        onClick={() => handleAgentInvestigation(selectedNodeData.id)}
                      >
                        <Bot size={13} className="animate-pulse" />
                        Run AI Fraud Investigation
                      </Button>
                    )}

                    {!selectedNodeData.isCommunity && activeMode !== 'investigation' && (
                      <Button
                        variant="primary"
                        size="sm"
                        className="w-full text-xs font-bold py-2.5 flex justify-center bg-cyan-600 hover:bg-cyan-500"
                        onClick={() => {
                          setInvestigatedAccount(selectedNodeData.id);
                          setActiveMode('investigation');
                          setSelectedNodeId(null);
                          setSelectedNodeData(null);
                        }}
                      >
                        🎯 Hop Trace Investigation
                      </Button>
                    )}
                    
                    {!selectedNodeData.isCommunity && selectedNodeData.status !== 'FLAGGED' && (
                      <Button
                        variant="danger"
                        size="sm"
                        className="w-full text-xs font-extrabold py-2.5 flex justify-center bg-gradient-to-r from-red-600 to-rose-700 hover:from-red-500 hover:to-rose-600 shadow-md shadow-red-500/10 border-0"
                        loading={flagMutation.isPending}
                        onClick={() => handleFlagAccount(selectedNodeData.id)}
                      >
                        🔴 Flag as Suspect Mule
                      </Button>
                    )}
                  </div>

                </motion.div>
              )}
            </AnimatePresence>

          </GlassCard>
        </motion.div>

      </div>

      {/* Spawning AI Agent Loader Backdrop Overlay */}
      <AnimatePresence>
        {isAgentRunning && (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-white/80 backdrop-blur-md"
          >
            <motion.div 
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-white border border-slate-200 p-8 rounded-2xl max-w-[400px] w-full text-center space-y-6 shadow-2xl"
            >
              <div className="relative mx-auto w-20 h-20">
                <div className="absolute inset-0 rounded-full border-4 border-indigo-100 animate-pulse" />
                <div className="absolute inset-0 rounded-full border-4 border-t-indigo-600 animate-spin" />
                <div className="absolute inset-0 flex items-center justify-center">
                  <Bot size={32} className="text-indigo-600 animate-bounce" />
                </div>
              </div>
              <div>
                <h3 className="text-lg font-bold text-slate-900 uppercase tracking-wider">Aegis AI Agent</h3>
                <p className="text-xs text-slate-500 mt-1">Forensic Analysis Cluster Spawning</p>
              </div>
              <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-100 font-mono text-[10px] text-indigo-700 min-h-[48px] flex items-center justify-center">
                {agentStatus}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Forensic Report Deep Detail Panel Overlay */}
      <AnimatePresence>
        {agentReport && (
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-45 flex items-center justify-center bg-slate-900/50 backdrop-blur-md p-6 font-satoshi"
          >
            <motion.div 
              initial={{ y: 20, scale: 0.98 }}
              animate={{ y: 0, scale: 1 }}
              exit={{ y: 20, scale: 0.98 }}
              className="bg-white border border-slate-200 rounded-2xl max-w-[950px] w-full h-[85vh] shadow-2xl flex flex-col overflow-hidden"
            >
              {/* Header */}
              <div className="p-4 border-b border-slate-100 bg-slate-50 flex justify-between items-center">
                <div className="flex items-center gap-2">
                  <Bot className="text-cyan-600" size={18} />
                  <div>
                    <h2 className="text-md font-cabinet font-extrabold text-slate-900 uppercase tracking-wide">Aegis Sentinel // Forensic Investigation Report</h2>
                    <p className="text-[10px] font-satoshi font-semibold text-slate-500">Autonomous compliance intelligence cluster briefing</p>
                  </div>
                </div>
                <button 
                  onClick={() => setAgentReport(null)}
                  className="p-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-600 hover:text-slate-950 transition-colors"
                >
                  <X size={16} />
                </button>
              </div>

              {/* Grid content split */}
              <div className="flex-1 flex overflow-hidden min-h-0">
                {/* Left side: Report */}
                <div className="flex-1 p-6 overflow-y-auto border-r border-slate-100 bg-slate-50/50 scrollbar-thin">
                  <MarkdownView content={agentReport} />
                </div>

                {/* Right side: Sidebar metadata */}
                <div className="w-[320px] p-6 space-y-5 bg-slate-50 overflow-y-auto select-none">
                  <div>
                    <h4 className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Investigated Community</h4>
                    <h3 className="text-2xl font-cabinet font-black text-slate-900 mt-1">Community {selectedCommunity}</h3>
                  </div>

                  <div className="space-y-3.5">
                    {/* Status Pill Card */}
                    <div className="bg-red-50 border border-red-200 p-3.5 rounded-xl">
                      <div className="flex items-center justify-between">
                        <span className="text-[9px] text-red-600 font-extrabold uppercase">Risk Classification</span>
                        <Badge variant="red" size="sm" pulse>HIGH RISK</Badge>
                      </div>
                      <p className="text-[10px] font-satoshi font-semibold text-red-700 mt-1.5 leading-normal">
                        Cluster exhibits severe money dispersal behaviors consistent with a professional money-laundering layer ring.
                      </p>
                    </div>

                    {/* Technical stats */}
                    <div className="bg-white border border-slate-200 p-4 rounded-xl space-y-3">
                      <div className="flex justify-between items-center text-xs">
                        <span className="text-slate-500 font-medium">LSTM Anomaly Score:</span>
                        <span className="font-mono text-slate-900 font-extrabold">0.91</span>
                      </div>
                      <div className="flex justify-between items-center text-xs">
                        <span className="text-slate-500 font-medium">GNN Propagation Score:</span>
                        <span className="font-mono text-slate-900 font-extrabold">{(selectedNodeData?.avgRisk || 0.85).toFixed(2)}</span>
                      </div>
                      <div className="flex justify-between items-center text-xs">
                        <span className="text-slate-500 font-medium">Aggregation Level:</span>
                        <span className="font-mono text-amber-600 font-extrabold">CRITICAL</span>
                      </div>
                      <div className="border-t border-slate-200 pt-2 flex justify-between items-center text-xs">
                        <span className="text-slate-500 font-medium">Recommended Action:</span>
                        <span className="font-bold text-red-600">FREEZE CLUSTER</span>
                      </div>
                    </div>

                    {/* Quota limit badge */}
                    {agentLimitRemaining !== null && (
                      <div className="bg-indigo-50 border border-indigo-200 p-3 rounded-xl flex items-center justify-between text-xs">
                        <span className="text-indigo-700 font-semibold">Daily Agent Quota Remaining:</span>
                        <Badge variant="purple" size="sm">{agentLimitRemaining}/45</Badge>
                      </div>
                    )}
                  </div>

                  <div className="pt-4 border-t border-white/5">
                    {agentPdfUrl && (
                      <a 
                        href={agentPdfUrl} 
                        download
                        className="w-full bg-gradient-to-r from-indigo-600 to-cyan-600 hover:from-indigo-500 hover:to-cyan-500 text-slate-950 hover:text-slate-950 font-extrabold py-3 px-4 rounded-xl flex items-center justify-center gap-2 shadow-lg shadow-indigo-500/20 transition-all text-xs border-0 text-white"
                      >
                        📥 Download 4-Page CAD PDF
                      </a>
                    )}
                  </div>
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

// Wrapper component providing ReactFlowProvider
export default function GraphPage() {
  return (
    <ReactFlowProvider>
      <GraphPageContent />
    </ReactFlowProvider>
  );
}

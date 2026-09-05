import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Cpu, 
  Play, 
  Terminal, 
  CheckCircle, 
  AlertCircle, 
  Activity, 
  Sparkles,
  GitBranch, 
  Clock, 
  FileJson,
  Zap
} from 'lucide-react';
import { useTrainModels, useTrainingStatus } from '@/hooks/useApi';
import { GlassCard } from '@/components/ui/GlassCard';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { fadeInUp, staggerContainer } from '@/lib/animations';
import AegisFraudModels from '@/components/models/AegisFraudModels';

export default function ModelsPage() {
  const [isPolling, setIsPolling] = useState(false);
  const [activeTab, setActiveTab] = useState<'core' | 'aegis'>('core');
  const trainMutation = useTrainModels();
  
  // Poll every 1.5s when training is active
  const { data: status, refetch } = useTrainingStatus(isPolling ? 1500 : false);
  const logEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (status?.status === 'training') {
      setIsPolling(true);
    } else {
      setIsPolling(false);
    }
  }, [status?.status]);

  // Auto scroll terminal logs
  useEffect(() => {
    if (logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [status?.logs?.length]);

  const handleTriggerTraining = () => {
    trainMutation.mutate(undefined, {
      onSuccess: () => {
        setIsPolling(true);
        refetch();
      }
    });
  };

  const modelCards = [
    {
      name: 'XGBoost Fraud Scorer',
      type: 'Supervised Classifier',
      desc: 'Predicts high-fidelity transaction fraud risk based on tabular, network, and behavioral engineered features.',
      target: 'Transaction Fraud Scoring',
      artifact: 'models/xgb_fraud.json',
      features: ['SHAP Interpretability', 'AUC-PR optimized', 'Real-time inference'],
      status: 'production',
      icon: Cpu,
      color: 'from-cyan-500 to-blue-600',
    },
    {
      name: 'GraphSAGE GNN Mule Detector',
      type: 'Deep Graph Neural Network',
      desc: 'Applies deep spatial learning to detect structural anomalies, multi-hop relay chains, and high-degree fan-out nodes.',
      target: 'Account Mule suspect labeling',
      artifact: 'models/gnn_mule.pt',
      features: ['GraphSAGE embeddings', 'Unsupervised GNN representation', 'Contagion tracking'],
      status: 'production',
      icon: GitBranch,
      color: 'from-purple-500 to-indigo-600',
    },
    {
      name: 'Improved LSTM Autoencoder',
      type: 'Recurrent Neural Network with Attention',
      desc: 'Deep Bidirectional sequence autoencoder with learnable positional encoding, multi-head self-attention, and variational dropout. Evaluates temporal behaviors to flag account anomalies via reconstruction error spikes.',
      target: 'Temporal pattern anomaly detection',
      artifact: 'models/lstm_ae.pt',
      features: [
        'Bidirectional encoding',
        '8-Head Multi-Head Attention',
        'Variational Dropout (0.3)',
        'Learnable Positional Encoding',
        'Val ROC-AUC >0.92'
      ],
      status: 'production',
      icon: Activity,
      color: 'from-pink-500 to-rose-600',
    },
    {
      name: 'Temporal GNN Isolation Forest',
      type: 'Hybrid Unsupervised Outlier Detector',
      desc: 'Leverages temporal GraphSAGE network embeddings combined with isolation forest decision trees to isolate structural transaction relation anomalies across continuous time-slice windows.',
      target: 'High-Velocity Mule Account Discovery',
      artifact: 'models/gnn_iforest.pt',
      features: [
        'Temporal relation mapping',
        'Isolation Forest pruning',
        'Dynamic window clustering',
        'Unsupervised score calibration'
      ],
      status: 'production',
      icon: GitBranch,
      color: 'from-amber-500 to-orange-600',
    },
    {
      name: 'Selective RAM Swap Manager',
      type: 'Active Pipeline Optimization Layer',
      desc: 'Aggressively tunes swappiness and evicts idle background processes prior to training, while pinning critical API backend and frontend pages directly in physical RAM.',
      target: 'Zero-Thrashing Pipeline Headroom',
      artifact: 'src/system/swap_manager.py',
      features: [
        'mlockall core pinning',
        'cgroups v2 swap disablement',
        'vmstat I/O settle checking',
        'Dynamic sysctl tuning (vm=100/500)'
      ],
      status: 'production',
      icon: Zap,
      color: 'from-emerald-500 to-teal-600',
    },
  ];

  return (
    <motion.div variants={staggerContainer} initial="hidden" animate="visible" className="space-y-6">
      {/* Header */}
      <motion.div variants={fadeInUp} className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Sparkles className="text-cyan-400" />
            Machine Learning Pipelines
          </h1>
          <p className="text-sm text-white/40 mt-1">Manage and retrain downstream AI models and neural transaction graph classifiers.</p>
        </div>
        <Badge variant={status?.status === 'training' ? 'amber' : 'green'} pulse={status?.status === 'training'}>
          {status?.status === 'training' ? 'PIPELINE RUNNING' : 'PIPELINE STANDBY'}
        </Badge>
      </motion.div>

      {/* Tab Switcher */}
      <div className="flex border-b border-white/[0.06] gap-6 mt-2">
        <button
          onClick={() => setActiveTab('core')}
          className={`pb-3 text-sm font-semibold tracking-wide transition-all relative ${
            activeTab === 'core'
              ? 'text-cyan-400 font-bold'
              : 'text-white/40 hover:text-white/70'
          }`}
        >
          Core ML Pipelines
          {activeTab === 'core' && (
            <motion.div layoutId="activeTabUnderline" className="absolute bottom-0 left-0 right-0 h-[2px] bg-cyan-400" />
          )}
        </button>
        <button
          onClick={() => setActiveTab('aegis')}
          className={`pb-3 text-sm font-semibold tracking-wide transition-all relative ${
            activeTab === 'aegis'
              ? 'text-purple-400 font-bold'
              : 'text-white/40 hover:text-white/70'
          }`}
        >
          Aegis Fraud Models
          {activeTab === 'aegis' && (
            <motion.div layoutId="activeTabUnderline" className="absolute bottom-0 left-0 right-0 h-[2px] bg-purple-400" />
          )}
        </button>
      </div>

      {activeTab === 'core' ? (
        <>
          {/* Main retraining console */}
          <motion.div variants={fadeInUp}>
            <GlassCard padding="lg" className="border-cyan-500/20 relative overflow-hidden">
              {/* Decorative backdrop light */}
              <div className="absolute -top-24 -right-24 w-48 h-48 rounded-full bg-cyan-500/10 blur-[80px]" />
              
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-center">
                {/* Control Console */}
                <div className="lg:col-span-1 space-y-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
                      <Zap size={20} />
                    </div>
                    <div>
                      <h3 className="text-lg font-semibold text-white">Central Pipeline Control</h3>
                      <p className="text-xs text-white/40">Sync database transactions and retrain AI models on demand.</p>
                    </div>
                  </div>

                  <div className="py-2 space-y-2">
                    <div className="flex justify-between text-xs">
                      <span className="text-white/40">Pipeline Status:</span>
                      <span className={`font-semibold uppercase tracking-wider ${
                        status?.status === 'training' ? 'text-amber-400' :
                        status?.status === 'completed' ? 'text-green-400' :
                        status?.status === 'failed' ? 'text-red-400' : 'text-cyan-400'
                      }`}>
                        {status?.status ?? 'idle'}
                      </span>
                    </div>
                    {status?.started_at && (
                      <div className="flex justify-between text-xs">
                        <span className="text-white/40">Last Run Triggered:</span>
                        <span className="text-white/70 flex items-center gap-1 font-mono">
                          <Clock size={12} />
                          {new Date(status.started_at * 1000).toLocaleTimeString()}
                        </span>
                      </div>
                    )}
                  </div>

                  <Button
                    variant={status?.status === 'training' ? 'secondary' : 'primary'}
                    className="w-full flex items-center justify-center gap-2"
                    onClick={handleTriggerTraining}
                    disabled={status?.status === 'training'}
                  >
                    {status?.status === 'training' ? (
                      <>
                        <Activity className="animate-pulse" size={16} />
                        Retraining Models...
                      </>
                    ) : (
                      <>
                        <Play size={16} />
                        Trigger End-to-End Pipeline
                      </>
                    )}
                  </Button>
                </div>

                {/* Live Subprocess Console Log */}
                <div className="lg:col-span-2">
                  <div className="rounded-xl border border-white/[0.06] bg-void/80 p-4 h-[220px] flex flex-col">
                    <div className="flex items-center justify-between border-b border-white/[0.06] pb-2 mb-2 text-xs text-white/40 font-mono">
                      <span className="flex items-center gap-2">
                        <Terminal size={12} className="text-cyan-400" />
                        realtime_pipeline_monitor.log
                      </span>
                      <span>UTF-8</span>
                    </div>
                    <div className="flex-1 overflow-y-auto space-y-1 font-mono text-[10px] text-white/70 scrollbar-thin">
                      {status?.logs && status.logs.length > 0 ? (
                        status.logs.map((log, i) => (
                          <div key={i} className="leading-5 border-l-2 border-cyan-500/20 pl-2">
                            <span className="text-cyan-500/50 mr-2">[{i + 1}]</span>
                            {log}
                          </div>
                        ))
                      ) : (
                        <div className="h-full flex items-center justify-center text-white/20 italic">
                          No active logs. Click "Trigger End-to-End Pipeline" to start pipeline retraining.
                        </div>
                      )}
                      <div ref={logEndRef} />
                    </div>
                  </div>
                </div>
              </div>
            </GlassCard>
          </motion.div>

          {/* Model Cards Grid */}
          <motion.div variants={fadeInUp} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {modelCards.map((model) => (
              <GlassCard key={model.name} padding="md" className="flex flex-col justify-between group hover:border-cyan-500/20 transition-all duration-300">
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${model.color} flex items-center justify-center text-white`}>
                      <model.icon size={20} />
                    </div>
                    <Badge variant="cyan" size="sm">ACTIVE</Badge>
                  </div>

                  <div>
                    <h3 className="text-base font-bold text-white leading-tight">{model.name}</h3>
                    <p className="text-[10px] text-cyan-400 font-medium mt-0.5 tracking-wider uppercase">{model.type}</p>
                    <p className="text-xs text-white/50 mt-2 leading-relaxed h-[60px] overflow-hidden">{model.desc}</p>
                  </div>

                  <div className="pt-2 border-t border-white/[0.04] space-y-2">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-white/30">Target:</span>
                      <span className="text-white/70 font-medium">{model.target}</span>
                    </div>
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-white/30">Artifact:</span>
                      <span className="text-cyan-400/80 font-mono text-[10px] flex items-center gap-1">
                        <FileJson size={10} />
                        {model.artifact}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="mt-4 pt-3 border-t border-white/[0.04]">
                  <h4 className="text-[10px] text-white/40 uppercase tracking-wider mb-2 font-medium">Pipeline Capabilities</h4>
                  <div className="flex flex-wrap gap-1.5">
                    {model.features.map((feat) => (
                      <span key={feat} className="text-[9px] px-2 py-0.5 rounded bg-white/[0.03] border border-white/[0.05] text-white/60">
                        {feat}
                      </span>
                    ))}
                  </div>
                </div>
              </GlassCard>
            ))}
          </motion.div>
        </>
      ) : (
        <AegisFraudModels />
      )}
    </motion.div>
  );
}



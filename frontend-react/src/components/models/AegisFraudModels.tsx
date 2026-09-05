import { useState, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { 
  Cpu, 
  Play, 
  Terminal, 
  CheckCircle, 
  AlertCircle, 
  Activity, 
  Download, 
  Search, 
  AlertTriangle,
  Clock, 
  FileJson,
  Zap
} from 'lucide-react';
import { GlassCard } from '@/components/ui/GlassCard';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { fadeInUp, staggerContainer } from '@/lib/animations';

interface ModelInfo {
  id: string;
  name: string;
  type: string;
  badge: 'Supervised' | 'Unsupervised' | 'Ensemble' | 'Preprocessing';
  desc: string;
  color: string;
}

const Aegis_MODELS_LIST: ModelInfo[] = [
  {
    id: 'preprocessing',
    name: 'Aegis Feature Pipeline',
    type: 'Preprocessing & Mutual Info Selection',
    badge: 'Preprocessing',
    desc: 'Cleans null features, drops high-missing columns, applies KNN imputation, and uses Mutual Information to select top 100 features + 18 Aegis features.',
    color: 'from-cyan-500 to-blue-600'
  },
  {
    id: 'xgboost',
    name: 'Aegis XGBoost + SMOTE',
    type: 'XGBoost Supervised Classifier',
    badge: 'Supervised',
    desc: 'Uses Synthetic Minority Over-sampling Technique (SMOTE) to balance dataset fraud class and fits an ensemble of gradient-boosted trees.',
    color: 'from-teal-500 to-emerald-600'
  },
  {
    id: 'lightgbm',
    name: 'Aegis LightGBM + Class Weights',
    type: 'LightGBM Classifier',
    badge: 'Supervised',
    desc: 'Uses LightGBM with highly optimized leaf-wise tree growth, balanced class weighting, and early stopping callbacks for lightning-fast training.',
    color: 'from-purple-500 to-indigo-600'
  },
  {
    id: 'randomforest',
    name: 'Aegis Random Forest + SMOTETomek',
    type: 'Random Forest Classifier',
    badge: 'Supervised',
    desc: 'Combines SMOTE over-sampling with Tomek links cleaning of borderline majority class samples, feeding into balanced Random Forest trees.',
    color: 'from-pink-500 to-rose-600'
  },
  {
    id: 'isoforest',
    name: 'Aegis Isolation Forest',
    type: 'Unsupervised Anomaly Detector',
    badge: 'Unsupervised',
    desc: 'Fits Isolation Forest on legitimate accounts only. Learns normal behavior boundaries to detect novel and unseen transaction fraud variants.',
    color: 'from-amber-500 to-orange-600'
  },
  {
    id: 'mlp',
    name: 'Aegis MLP + Focal Loss',
    type: 'PyTorch Deep Neural Network',
    badge: 'Supervised',
    desc: 'A PyTorch Multi-Layer Perceptron (MLP) trained with Focal Loss to penalize easy classification targets and prioritize hard-to-classify fraud cases.',
    color: 'from-blue-500 to-indigo-700'
  },
  {
    id: 'ensemble',
    name: 'Aegis Voting Ensemble',
    type: 'Soft Voting Classifier',
    badge: 'Ensemble',
    desc: 'Combines XGBoost, LightGBM, Random Forest, PyTorch MLP, and Isolation Forest models. Uses weighted probability voting for production predictions.',
    color: 'from-purple-600 to-pink-600'
  }
];

const DEFAULT_SAMPLE_FEATURES_Aegis = {
  "F115": 0.825,
  "F321": -0.104,
  "F527": 1.492,
  "F531": -0.228,
  "F670": 3.011,
  "F1692": -0.924,
  "F2082": 0.155,
  "F2122": 1.252,
  "F2582": -0.582,
  "F2678": 0.448,
  "F2737": 1.137,
  "F2956": -0.408,
  "F3043": 0.0,
  "F3836": 2.115,
  "F3887": 32,
  "F3889": 89,
  "F3891": 4,
  "F3894": 1
};

const DEFAULT_SAMPLE_FEATURES_CORE = {
  "amount_zscore": 1.25,
  "is_new_beneficiary": 1,
  "fan_out_ratio": 0.45,
  "dormancy_break_flag": 0,
  "night_txn_ratio": 0.15,
  "txn_velocity_1h": 2.0,
  "txn_velocity_24h": 5.0,
  "txn_velocity_7d": 12.0,
  "unique_beneficiaries_7d": 4,
  "graph_degree_centrality": 0.05,
  "suspicious_neighbor_count": 0,
  "hop_2_mule_count": 1
};

export default function AegisFraudModels() {
  const [status, setStatus] = useState<string>('idle');
  const [currentStep, setCurrentStep] = useState<string>('idle');
  const [logs, setLogs] = useState<string[]>([]);
  const [metrics, setMetrics] = useState<Record<string, any>>({});
  const [modelsReady, setModelsReady] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  
  // Prediction Playground State
  const [pipelineType, setPipelineType] = useState<'aegis' | 'core'>('aegis');
  const [predictPayload, setPredictPayload] = useState<string>(
    JSON.stringify(DEFAULT_SAMPLE_FEATURES_Aegis, null, 2)
  );
  const [predictResult, setPredictResult] = useState<any>(null);
  const [predicting, setPredicting] = useState<boolean>(false);
  const [predictError, setPredictError] = useState<string | null>(null);

  const logEndRef = useRef<HTMLDivElement>(null);
  const pollingRef = useRef<any>(null);

  // Poll status endpoint
  const checkStatus = async () => {
    try {
      const res = await fetch('/api/v1/fraud-models/status');
      if (res.ok) {
        const data = await res.json();
        setStatus(data.status);
        setCurrentStep(data.current_step);
        setLogs(data.logs || []);
        setMetrics(data.metrics || {});
        setModelsReady(data.models_ready || []);
        setError(data.error);

        if (data.status !== 'training') {
          stopPolling();
        }
      }
    } catch (err) {
      console.error("Error polling fraud models status:", err);
    }
  };

  const startPolling = () => {
    stopPolling();
    pollingRef.current = setInterval(checkStatus, 2000);
  };

  const stopPolling = () => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  };

  // Check status on load and cleanup
  useEffect(() => {
    checkStatus();
    return () => stopPolling();
  }, []);

  // Poll when status is training
  useEffect(() => {
    if (status === 'training') {
      startPolling();
    } else {
      stopPolling();
    }
  }, [status]);

  // Auto scroll logs
  useEffect(() => {
    if (logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs.length]);

  const handleTrainAll = async () => {
    try {
      setError(null);
      setPredictResult(null);
      const res = await fetch('/api/v1/fraud-models/train', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          dataset_path: "/home/krsna/Desktop/Aegis/SETDATA/aegis_notebooks/DataSet.csv"
        })
      });
      if (res.ok) {
        const data = await res.json();
        setStatus(data.status);
        checkStatus();
      } else {
        const errData = await res.json();
        setError(errData.detail || "Failed to trigger model training.");
      }
    } catch (err) {
      setError("Network error triggering model training.");
    }
  };

  const handleDownload = (modelId: string) => {
    window.open(`/api/v1/fraud-models/download/${modelId}`, '_blank');
  };

  const handlePipelineChange = (type: 'aegis' | 'core') => {
    setPipelineType(type);
    setPredictResult(null);
    setPredictError(null);
    if (type === 'aegis') {
      setPredictPayload(JSON.stringify(DEFAULT_SAMPLE_FEATURES_Aegis, null, 2));
    } else {
      setPredictPayload(JSON.stringify(DEFAULT_SAMPLE_FEATURES_CORE, null, 2));
    }
  };

  const handlePredict = async () => {
    setPredicting(true);
    setPredictResult(null);
    setPredictError(null);
    try {
      const parsedFeatures = JSON.parse(predictPayload);
      const res = await fetch('/api/v1/fraud-models/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          features: parsedFeatures,
          pipeline_type: pipelineType
        })
      });
      if (res.ok) {
        const data = await res.json();
        setPredictResult(data);
      } else {
        const errData = await res.json();
        setPredictError(errData.detail || "Prediction request failed.");
      }
    } catch (err: any) {
      setPredictError(err.message || "Invalid JSON formatting in features dictionary.");
    } finally {
      setPredicting(false);
    }
  };

  const getModelStatus = (id: string) => {
    if (modelsReady.includes(id)) return 'ready';
    if (status === 'training' && currentStep === id) return 'training';
    return 'idle';
  };

  return (
    <motion.div variants={staggerContainer} initial="hidden" animate="visible" className="space-y-6 mt-6">
      
      {/* Retraining Console */}
      <motion.div variants={fadeInUp}>
        <GlassCard padding="lg" className="border-cyan-500/20 relative overflow-hidden">
          <div className="absolute -top-24 -right-24 w-48 h-48 rounded-full bg-cyan-500/10 blur-[80px]" />
          
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-center">
            
            {/* Controls */}
            <div className="lg:col-span-1 space-y-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400">
                  <Zap size={20} />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-white">Aegis Fraud Training Console</h3>
                  <p className="text-xs text-white/40">Train, track, and deploy the 7-step ensemble pipeline.</p>
                </div>
              </div>

              <div className="py-2 space-y-2">
                <div className="flex justify-between text-xs">
                  <span className="text-white/40">Pipeline Status:</span>
                  <span className={`font-semibold uppercase tracking-wider ${
                    status === 'training' ? 'text-amber-400 animate-pulse' :
                    status === 'completed' ? 'text-green-400' :
                    status === 'failed' ? 'text-red-400' : 'text-cyan-400'
                  }`}>
                    {status}
                  </span>
                </div>
                
                {currentStep && currentStep !== 'idle' && status === 'training' && (
                  <div className="flex justify-between text-xs">
                    <span className="text-white/40">Current Step:</span>
                    <span className="text-white/80 font-mono font-medium tracking-wider uppercase text-cyan-400">
                      {currentStep}
                    </span>
                  </div>
                )}
              </div>

              <Button
                variant={status === 'training' ? 'secondary' : 'primary'}
                className="w-full flex items-center justify-center gap-2"
                onClick={handleTrainAll}
                disabled={status === 'training'}
              >
                {status === 'training' ? (
                  <>
                    <Activity className="animate-pulse" size={16} />
                    Training Pipeline...
                  </>
                ) : (
                  <>
                    <Play size={16} />
                    Train All Models
                  </>
                )}
              </Button>
              
              {error && (
                <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-xl flex items-start gap-2 text-xs text-red-400">
                  <AlertCircle size={14} className="mt-0.5 shrink-0" />
                  <span>{error}</span>
                </div>
              )}
            </div>

            {/* Logs Monitor */}
            <div className="lg:col-span-2">
              <div className="rounded-xl border border-white/[0.06] bg-void/80 p-4 h-[220px] flex flex-col">
                <div className="flex items-center justify-between border-b border-white/[0.06] pb-2 mb-2 text-xs text-white/40 font-mono">
                  <span className="flex items-center gap-2">
                    <Terminal size={12} className="text-purple-400" />
                    aegis_fraud_pipeline.log
                  </span>
                  <Badge variant={status === 'training' ? 'amber' : 'green'}>
                    {status === 'training' ? 'RUNNING' : 'STANDBY'}
                  </Badge>
                </div>
                
                <div className="flex-1 overflow-y-auto space-y-1 font-mono text-[10px] text-white/70 scrollbar-thin">
                  {logs.length > 0 ? (
                    logs.map((log, i) => (
                      <div key={i} className="leading-5 border-l-2 border-purple-500/20 pl-2">
                        <span className="text-purple-500/50 mr-2">[{i + 1}]</span>
                        {log}
                      </div>
                    ))
                  ) : (
                    <div className="h-full flex items-center justify-center text-white/20 italic">
                      Console standby. Click "Train All Models" to start the 7-step pipeline.
                    </div>
                  )}
                  <div ref={logEndRef} />
                </div>
              </div>
            </div>

          </div>
        </GlassCard>
      </motion.div>

      {/* Models Grid */}
      <motion.div variants={fadeInUp} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {Aegis_MODELS_LIST.map((model) => {
          const modelStatus = getModelStatus(model.id);
          const modelMetrics = metrics[model.id];
          const isReady = modelsReady.includes(model.id);

          return (
            <GlassCard key={model.id} padding="md" className="flex flex-col justify-between group hover:border-purple-500/20 transition-all duration-300">
              <div className="space-y-4">
                
                {/* Card Header */}
                <div className="flex items-center justify-between">
                  <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${model.color} flex items-center justify-center text-white shadow-lg`}>
                    <Cpu size={20} />
                  </div>
                  
                  <div className="flex items-center gap-2">
                    <Badge variant={
                      model.badge === 'Ensemble' ? 'purple' : 
                      model.badge === 'Unsupervised' ? 'amber' : 
                      model.badge === 'Preprocessing' ? 'cyan' : 'green'
                    } size="sm">
                      {model.badge}
                    </Badge>
                    
                    {/* Status Dot */}
                    <span className={`w-2 h-2 rounded-full ${
                      modelStatus === 'ready' ? 'bg-green-500 shadow-[0_0_8px_#22c55e]' :
                      modelStatus === 'training' ? 'bg-amber-500 animate-ping' : 'bg-white/20'
                    }`} />
                  </div>
                </div>

                {/* Model Title & Desc */}
                <div>
                  <h3 className="text-base font-bold text-white leading-tight">{model.name}</h3>
                  <p className="text-[10px] text-purple-400 font-medium mt-0.5 tracking-wider uppercase">{model.type}</p>
                  <p className="text-xs text-white/50 mt-2 leading-relaxed h-[65px] overflow-hidden">{model.desc}</p>
                </div>

                {/* Dynamic Metrics Panel */}
                <div className="pt-2 border-t border-white/[0.04]">
                  {model.id === 'preprocessing' ? (
                    <div className="flex items-center justify-between text-xs py-1">
                      <span className="text-white/30">Features Selected:</span>
                      <span className="text-cyan-400 font-mono font-medium">
                        {isReady ? `${Aegis_MODELS_LIST.length - 1 + 100} Features` : 'Pending'}
                      </span>
                    </div>
                  ) : (
                    <div className="grid grid-cols-2 gap-2 text-xs py-1">
                      <div className="flex justify-between border-r border-white/[0.04] pr-2">
                        <span className="text-white/30">F1 Score:</span>
                        <span className="text-purple-400 font-mono font-medium">
                          {modelMetrics ? modelMetrics.F1.toFixed(4) : '—'}
                        </span>
                      </div>
                      <div className="flex justify-between pl-1">
                        <span className="text-white/30">ROC-AUC:</span>
                        <span className="text-green-400 font-mono font-medium">
                          {modelMetrics ? modelMetrics["ROC-AUC"].toFixed(4) : '—'}
                        </span>
                      </div>
                      <div className="flex justify-between border-r border-white/[0.04] pr-2 mt-1">
                        <span className="text-white/30">Precision:</span>
                        <span className="text-white/70 font-mono">
                          {modelMetrics ? modelMetrics.Precision.toFixed(4) : '—'}
                        </span>
                      </div>
                      <div className="flex justify-between pl-1 mt-1">
                        <span className="text-white/30">Recall:</span>
                        <span className="text-white/70 font-mono">
                          {modelMetrics ? modelMetrics.Recall.toFixed(4) : '—'}
                        </span>
                      </div>
                    </div>
                  )}
                </div>

              </div>

              {/* Download Buttons */}
              <div className="mt-4 pt-3 border-t border-white/[0.04] flex items-center justify-between">
                <span className="text-[10px] text-white/30 uppercase tracking-wider font-mono">
                  {model.id === 'preprocessing' ? 'scaler.pkl' : `model_${model.id}.pkl`}
                </span>
                
                <Button
                  size="sm"
                  variant="secondary"
                  className="flex items-center gap-1.5 px-3 py-1 text-[11px]"
                  disabled={!isReady}
                  onClick={() => handleDownload(model.id)}
                >
                  <Download size={11} />
                  Download .pkl
                </Button>
              </div>

            </GlassCard>
          );
        })}
      </motion.div>

      {/* Live Inference playground */}
      <motion.div variants={fadeInUp}>
        <GlassCard padding="lg" className="border-purple-500/20">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4 border-b border-white/[0.04] pb-4">
            <div className="flex items-center gap-2">
              <Search className="text-purple-400" size={18} />
              <h3 className="text-base font-bold text-white font-outfit">Production Predictor Playground</h3>
            </div>
            
            <div className="flex bg-void p-0.5 rounded-lg border border-white/[0.06] text-xs">
              <button
                type="button"
                className={`px-3 py-1.5 rounded-md transition-all font-medium ${
                  pipelineType === 'aegis'
                    ? 'bg-gradient-to-r from-purple-600 to-pink-600 text-white shadow-sm font-semibold'
                    : 'text-white/60 hover:text-white'
                }`}
                onClick={() => handlePipelineChange('aegis')}
              >
                7-Model Aegis Ensemble
              </button>
              <button
                type="button"
                className={`px-3 py-1.5 rounded-md transition-all font-medium ${
                  pipelineType === 'core'
                    ? 'bg-gradient-to-r from-purple-600 to-pink-600 text-white shadow-sm font-semibold'
                    : 'text-white/60 hover:text-white'
                }`}
                onClick={() => handlePipelineChange('core')}
              >
                Simulated Core Models
              </button>
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            
            {/* Input payload */}
            <div className="space-y-2">
              <label className="text-xs text-white/40 block">
                {pipelineType === 'aegis' ? '18 Aegis Features JSON Input:' : '12 Core Features JSON Input:'}
              </label>
              <textarea
                className="w-full h-[180px] bg-void border border-white/[0.06] rounded-xl p-3 font-mono text-[11px] text-white/80 focus:border-purple-500/50 focus:outline-none resize-none scrollbar-thin"
                value={predictPayload}
                onChange={(e) => setPredictPayload(e.target.value)}
              />
              <Button
                variant="primary"
                className="w-full flex items-center justify-center gap-2"
                onClick={handlePredict}
                disabled={predicting || (pipelineType === 'aegis' && !modelsReady.includes('ensemble'))}
              >
                {predicting 
                  ? 'Processing API Scoring...' 
                  : pipelineType === 'aegis' 
                    ? 'Run Ensemble Inference' 
                    : 'Run Simulated Core Inference'}
              </Button>
              {pipelineType === 'aegis' && !modelsReady.includes('ensemble') && (
                <p className="text-[10px] text-amber-500 flex items-center gap-1">
                  <AlertTriangle size={10} />
                  Please retrain models first to instantiate the production Ensemble model.
                </p>
              )}
            </div>

            {/* Results Display */}
            <div className="rounded-xl border border-white/[0.06] bg-void/50 p-4 flex flex-col justify-center min-h-[220px]">
              {predictResult ? (
                <div className="space-y-4">
                  <div className="flex justify-between items-center">
                    <div>
                      <span className="text-xs text-white/40 block">Inference Decision Label:</span>
                      <span className="text-lg font-bold text-white tracking-wide mt-1 block">
                        {predictResult.risk_label}
                      </span>
                    </div>
                    <Badge variant={predictResult.risk_label === 'FRAUD' ? 'red' : 'green'} size="md">
                      {predictResult.risk_label}
                    </Badge>
                  </div>
                  
                  {/* Gauge indicator */}
                  <div className="space-y-1">
                    <div className="flex justify-between text-xs">
                      <span className="text-white/40">Probability Score:</span>
                      <span className="font-mono text-purple-400 font-semibold">
                        {(predictResult.fraud_probability * 100).toFixed(2)}%
                      </span>
                    </div>
                    
                    <div className="h-2 w-full bg-white/[0.04] rounded-full overflow-hidden">
                      <div 
                        className={`h-full rounded-full transition-all duration-500 ${
                          predictResult.risk_label === 'FRAUD' ? 'bg-gradient-to-r from-orange-500 to-red-600' : 'bg-gradient-to-r from-emerald-500 to-teal-600'
                        }`}
                        style={{ width: `${predictResult.fraud_probability * 100}%` }}
                      />
                    </div>
                  </div>

                  <div className="pt-2 border-t border-white/[0.04] flex items-center justify-between text-[10px] text-white/30 font-mono">
                    <span>Active Pipeline: {predictResult.pipeline === 'core' ? 'Simulated Core Model' : '7-Model Aegis Ensemble'}</span>
                    <span>Scoring calibrated</span>
                  </div>
                </div>
              ) : predictError ? (
                <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-xl flex items-start gap-2 text-xs text-red-400">
                  <AlertCircle size={14} className="mt-0.5 shrink-0" />
                  <span>{predictError}</span>
                </div>
              ) : (
                <div className="text-center text-white/20 italic text-sm">
                  Paste features in JSON format and run inference to see real-time fraud probability scores.
                </div>
              )}
            </div>

          </div>
        </GlassCard>
      </motion.div>

    </motion.div>
  );
}

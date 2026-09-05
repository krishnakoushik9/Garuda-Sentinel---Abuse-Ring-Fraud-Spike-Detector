import { useState, useRef, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  User,
  Mail,
  Camera,
  LayoutGrid,
  Play,
  Terminal,
  Trash2,
  ChevronRight,
  Sun,
  Moon,
  Bell,
  BarChart2,
  AlertTriangle,
  X,
  ChevronDown,
  Cpu,
  Shield,
  FileText,
  Database,
  RefreshCw,
  Activity,
  HardDrive
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAppStore } from '@/stores/appStore';
import { useSystemStore } from '@/stores/systemStore';

import { InteractiveFolder } from '@/components/ui/InteractiveFolder';

/* ─────────────────────────────────────────────
   Types
   ───────────────────────────────────────────── */
type SectionId = 'profile' | 'system' | 'dataset' | 'appearance' | 'navigation' | 'generator' | 'danger';

interface SidebarItem {
  id: SectionId;
  label: string;
  icon: React.ElementType;
  iconBg: string;
}

const SIDEBAR_ITEMS: SidebarItem[] = [
  { id: 'profile',    label: 'Profile',       icon: User,       iconBg: 'linear-gradient(135deg,#3b82f6,#1d4ed8)' },
  { id: 'system',     label: 'System Control',icon: Cpu,        iconBg: 'linear-gradient(135deg,#a855f7,#7e22ce)' },
  { id: 'dataset',    label: 'Dataset Ingest',icon: Database,   iconBg: 'linear-gradient(135deg,#eab308,#ca8a04)' },
  { id: 'appearance', label: 'Appearance',    icon: Sun,        iconBg: 'linear-gradient(135deg,#f59e0b,#d97706)' },
  { id: 'navigation', label: 'Navigation',   icon: LayoutGrid, iconBg: 'linear-gradient(135deg,#8b5cf6,#6d28d9)' },
  { id: 'generator',  label: 'Data Generator',icon: Terminal,   iconBg: 'linear-gradient(135deg,#10b981,#059669)' },
  { id: 'danger',     label: 'Danger Zone',  icon: Shield,     iconBg: 'linear-gradient(135deg,#ef4444,#b91c1c)' },
];

/* ─────────────────────────────────────────────
   iOS Toggle
───────────────────────────────────────────── */
function IOSToggle({ checked, onChange, id }: { checked: boolean; onChange: (v: boolean) => void; id: string }) {
  return (
    <button
      id={id}
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className="ios-toggle"
      data-checked={checked}
    >
      <span className="ios-toggle-thumb" />
    </button>
  );
}

/* ─────────────────────────────────────────────
   Detail Row
───────────────────────────────────────────── */
function DetailRow({
  icon, iconBg, label, detail, accessory, onClick, divider = true, danger = false,
}: {
  icon?: React.ReactNode; iconBg?: string; label: string; detail?: string;
  accessory?: React.ReactNode; onClick?: () => void; divider?: boolean; danger?: boolean;
}) {
  return (
    <div className={`settings-row-wrap ${!divider ? 'settings-row-wrap--last' : ''}`}>
      <button
        className={`settings-row ${onClick ? 'settings-row--clickable' : ''} ${danger ? 'settings-row--danger' : ''}`}
        onClick={onClick}
        disabled={!onClick}
      >
        {icon && (
          <span className="settings-row-icon-wrap" style={{ background: iconBg || 'var(--ios-accent)' }}>
            {icon}
          </span>
        )}
        <div className="settings-row-body">
          <span className={`settings-row-label ${danger ? 'settings-row-label--danger' : ''}`}>{label}</span>
          {detail && <span className="settings-row-detail">{detail}</span>}
        </div>
        <div className="settings-row-accessory">{accessory}</div>
      </button>
      {divider && <div className="settings-divider" />}
    </div>
  );
}

/* ─────────────────────────────────────────────
   Group Container
───────────────────────────────────────────── */
function DetailGroup({ title, children, variant = 'default' }: {
  title?: string; children: React.ReactNode; variant?: 'default' | 'danger';
}) {
  return (
    <div className="settings-section-wrapper">
      {title && (
        <p className={`settings-section-label ${variant === 'danger' ? 'settings-section-label--danger' : ''}`}>
          {title}
        </p>
      )}
      <div className={`settings-group ${variant === 'danger' ? 'settings-group--danger' : ''}`}>
        {children}
      </div>
    </div>
  );
}

/* ─────────────────────────────────────────────
   iOS Select
───────────────────────────────────────────── */
function IOSSelect({ id, value, onChange, options }: {
  id: string; value: string; onChange: (v: string) => void; options: string[];
}) {
  return (
    <div className="ios-select-wrap">
      <select id={id} className="ios-select" value={value} onChange={e => onChange(e.target.value)}>
        {options.map(o => <option key={o} value={o}>{o}</option>)}
      </select>
      <ChevronDown size={14} className="ios-select-chevron" />
    </div>
  );
}

function SegmentedControl({ value, onChange, options }: {
  value: string; onChange: (v: any) => void; options: { id: string; label: string }[];
}) {
  return (
    <div className="ios-segmented-control">
      {options.map(opt => (
        <button
          key={opt.id}
          className={`ios-segment ${value === opt.id ? 'ios-segment--active' : ''}`}
          onClick={() => onChange(opt.id)}
        >
          {opt.label}
        </button>
      ))}
    </div>
  );
}

/* ─────────────────────────────────────────────
   Profile Sheet
───────────────────────────────────────────── */
function ProfileSheet({ open, onClose, name, email, avatar, onSave }: {
  open: boolean; onClose: () => void; name: string; email: string;
  avatar: string; onSave: (n: string, e: string, a: string) => void;
}) {
  const [localName, setLocalName]   = useState(name);
  const [localEmail, setLocalEmail] = useState(email);
  const [localAvatar, setLocalAvatar] = useState(avatar);
  const AVATARS = ['👤','🧑‍💼','👩‍💼','🧑‍💻','👩‍💻','🦁','🐯','🦊'];

  useEffect(() => {
    if (open) { setLocalName(name); setLocalEmail(email); setLocalAvatar(avatar); }
  }, [open, name, email, avatar]);

  return (
    <AnimatePresence>
      {open && (
        <div className="sheet-overlay">
          <motion.div key="sb" className="sheet-backdrop" initial={{ opacity:0 }} animate={{ opacity:1 }} exit={{ opacity:0 }} onClick={onClose} />
          <motion.div key="s" className="sheet"
            initial={{ opacity: 0, scale: 0.92 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.92 }}
            transition={{ type: 'spring', stiffness: 420, damping: 32 }}
          >
            <div className="sheet-handle" />
            <div className="sheet-header">
              <button className="sheet-cancel" onClick={onClose}>Cancel</button>
              <h3 className="sheet-title">Edit Profile</h3>
              <button className="sheet-done" onClick={() => { onSave(localName, localEmail, localAvatar); onClose(); }}>Done</button>
            </div>
            <div className="profile-avatar-picker">
              <div className="profile-avatar-display">{localAvatar}</div>
              <div className="profile-avatar-grid">
                {AVATARS.map(av => (
                  <button key={av}
                    className={`profile-avatar-option ${localAvatar === av ? 'profile-avatar-option--active' : ''}`}
                    onClick={() => setLocalAvatar(av)}
                  >{av}</button>
                ))}
              </div>
            </div>
            <div className="sheet-form">
              <div className="sheet-field-group">
                <div className="sheet-field">
                  <label className="sheet-field-label">Full Name</label>
                  <input className="sheet-field-input" value={localName} onChange={e => setLocalName(e.target.value)} placeholder="Your name" />
                </div>
                <div className="sheet-divider" />
                <div className="sheet-field">
                  <label className="sheet-field-label">Email</label>
                  <input className="sheet-field-input" type="email" value={localEmail} onChange={e => setLocalEmail(e.target.value)} placeholder="your@email.com" />
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}

/* ─────────────────────────────────────────────
   Danger Confirm Flow
───────────────────────────────────────────── */
function DangerConfirmFlow({ action, onClose, onConfirmed }: { action: 'delete' | 'clear' | 'rebuild' | 'deep_purge'; onClose: () => void; onConfirmed: () => void }) {
  const [step, setStep] = useState<1|2|3>(1);
  const [confirmText, setConfirmText] = useState('');
  const [countdown, setCountdown] = useState(5);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (step === 3) {
      setCountdown(5);
      timerRef.current = setInterval(() => {
        setCountdown(c => { if (c <= 1) { clearInterval(timerRef.current!); return 0; } return c - 1; });
      }, 1000);
    }
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [step]);

  const titles = {
    delete: 'Delete Database?',
    clear: 'Clear Transactions?',
    rebuild: 'Rebuild Database Schema?',
    deep_purge: 'Deep Purge Local Files?'
  };

  const bodies = {
    delete: 'This will permanently delete all accounts, transactions, mule networks, and fraud events.',
    clear: 'This will permanently wipe only the transactions ledger, keeping account profiles intact.',
    rebuild: 'This will reapply the core schema and drop then recreate all database tables.',
    deep_purge: 'WARNING: This will permanently delete all local SQLite databases (.db), log files, and schema files on disk. The system will be entirely empty!'
  };

  const confirmBtnLabels = {
    delete: 'Confirm Delete',
    clear: 'Confirm Clear',
    rebuild: 'Confirm Rebuild',
    deep_purge: 'Purge Disk Files'
  };

  return (
    <motion.div className="danger-overlay" initial={{ opacity:0 }} animate={{ opacity:1 }} exit={{ opacity:0 }}>
      <motion.div className="danger-modal"
        initial={{ scale:0.85, opacity:0 }} animate={{ scale:1, opacity:1 }} exit={{ scale:0.85, opacity:0 }}
        transition={{ type:'spring', stiffness:420, damping:30 }}
      >
        {step === 1 && (<>
          <div className="danger-modal-icon"><AlertTriangle size={28} /></div>
          <h4 className="danger-modal-title">{titles[action]}</h4>
          <p className="danger-modal-body">{bodies[action]}</p>
          <div className="danger-modal-actions">
            <button className="danger-btn danger-btn--cancel" onClick={onClose}>Cancel</button>
            <button className="danger-btn danger-btn--destructive" onClick={() => setStep(2)}>Continue</button>
          </div>
        </>)}
        {step === 2 && (<>
          <div className="danger-modal-icon danger-modal-icon--red"><AlertTriangle size={28} /></div>
          <h4 className="danger-modal-title">This cannot be undone.</h4>
          <p className="danger-modal-body">Type <code className="danger-code">DELETE</code> to confirm.</p>
          <input className="danger-input" placeholder="Type DELETE" value={confirmText} onChange={e => setConfirmText(e.target.value)} autoFocus />
          <div className="danger-modal-actions">
            <button className="danger-btn danger-btn--cancel" onClick={onClose}>Cancel</button>
            <button className="danger-btn danger-btn--destructive" disabled={confirmText !== 'DELETE'} onClick={() => setStep(3)}>Next</button>
          </div>
        </>)}
        {step === 3 && (<>
          <div className="danger-modal-icon danger-modal-icon--pulse"><Trash2 size={28} /></div>
          <h4 className="danger-modal-title">Last Chance.</h4>
          <p className="danger-modal-body">Button activates in <strong>{countdown}s</strong>.</p>
          {countdown > 0 && (
            <div className="danger-countdown">
              <div className="danger-countdown-bar" style={{ width:`${((5-countdown)/5)*100}%` }} />
            </div>
          )}
          <div className="danger-modal-actions">
            <button className="danger-btn danger-btn--cancel" onClick={onClose}>Abort</button>
            <button className="danger-btn danger-btn--final" disabled={countdown > 0} onClick={onConfirmed}>
              {countdown > 0 ? `Wait ${countdown}s…` : confirmBtnLabels[action]}
            </button>
          </div>
        </>)}
        <button className="danger-close" onClick={onClose}><X size={16} /></button>
      </motion.div>
    </motion.div>
  );
}

/* ─────────────────────────────────────────────
   Section Detail Panels
───────────────────────────────────────────── */

/* PROFILE */
function ProfilePanel() {
  const [name, setName]     = useState('Krsna Koushik');
  const [email, setEmail]   = useState('admin@aegis-fds.dev');
  const [avatar, setAvatar] = useState('🧑‍💻');
  const [sheetOpen, setSheetOpen] = useState(false);

  useEffect(() => {
    fetch('http://localhost:8000/api/settings/profile')
      .then(res => res.json())
      .then(data => {
        if (data.name) setName(data.name);
        if (data.email) setEmail(data.email);
        if (data.avatar_url) setAvatar(data.avatar_url);
      })
      .catch(err => console.error('Error fetching profile:', err));
  }, []);

  const handleSaveProfile = async (n: string, e: string, a: string) => {
    try {
      const res = await fetch('http://localhost:8000/api/settings/profile', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: n, email: e, avatar_url: a })
      });
      if (res.ok) {
        const data = await res.json();
        setName(data.name);
        setEmail(data.email);
        setAvatar(data.avatar_url);
      }
    } catch (err) {
      console.error('Error saving profile:', err);
    }
  };

  return (
    <>
      <div className="detail-section-title">Profile</div>

      <DetailGroup>
        <div className="settings-row-wrap">
          <button className="settings-row settings-row--clickable settings-profile-row" onClick={() => setSheetOpen(true)}>
            <div className="profile-avatar-badge">{avatar}</div>
            <div className="settings-row-body">
              <span className="settings-row-label settings-row-label--large">{name}</span>
              <span className="settings-row-detail">{email}</span>
            </div>
            <div className="settings-row-accessory">
              <span className="settings-row-edit">Edit</span>
              <ChevronRight size={16} className="settings-chevron" />
            </div>
          </button>
          <div className="settings-divider" />
        </div>
        <DetailRow icon={<Camera size={14} className="text-white" />} iconBg="linear-gradient(135deg,#8b5cf6,#6d28d9)" label="Profile Photo" detail="Choose avatar" accessory={<ChevronRight size={16} className="settings-chevron" />} onClick={() => setSheetOpen(true)} />
        <DetailRow icon={<User size={14} className="text-white" />}   iconBg="linear-gradient(135deg,#3b82f6,#1d4ed8)" label="Display Name"  detail={name}  accessory={<ChevronRight size={16} className="settings-chevron" />} onClick={() => setSheetOpen(true)} />
        <DetailRow icon={<Mail size={14} className="text-white" />}   iconBg="linear-gradient(135deg,#10b981,#059669)" label="Email"         detail={email} accessory={<ChevronRight size={16} className="settings-chevron" />} onClick={() => setSheetOpen(true)} divider={false} />
      </DetailGroup>

      <ProfileSheet open={sheetOpen} onClose={() => setSheetOpen(false)}
        name={name} email={email} avatar={avatar}
        onSave={handleSaveProfile}
      />
    </>
  );
}

/* SYSTEM CONTROL */
function SystemControlPanel() {
  const {
    dataSource,
    cobolStatus,
    fetchDataSourceStatus,
    fetchCobolStatus,
    fetchRealTimeMetrics,
    setCobolStatus
  } = useSystemStore();

  useEffect(() => {
    fetchDataSourceStatus();
    fetchCobolStatus();
    fetchRealTimeMetrics();
    
    const interval = setInterval(() => {
      fetchCobolStatus();
      fetchRealTimeMetrics();
    }, 4000);
    return () => clearInterval(interval);
  }, []);

  const handleSwitchSource = async (source: 'COBOL_SYNTHETIC' | 'REGULATORY_FEED') => {
    try {
      const res = await fetch('http://localhost:8000/api/v1/datasource/switch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source }),
      });
      if (res.ok) {
        await fetchDataSourceStatus();
        fetchRealTimeMetrics();
      }
    } catch (err) {
      console.error('Failed to switch datasource:', err);
    }
  };

  const handleCobolStart = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/cobol/start', { method: 'POST' });
      if (res.ok) {
        setCobolStatus({ running: true, status: 'Running' });
        fetchRealTimeMetrics();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleCobolStop = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/cobol/stop', { method: 'POST' });
      if (res.ok) {
        setCobolStatus({ running: false, status: 'Stopped' });
        fetchRealTimeMetrics();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleCobolGenerate = async (type: 'accounts' | 'transactions' | 'scenario') => {
    try {
      const res = await fetch(`http://localhost:8000/api/cobol/generate/${type}`, { method: 'POST' });
      if (res.ok) {
        fetchRealTimeMetrics();
      }
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <>
      <div className="detail-section-title">System Control</div>
      
      <DetailGroup title="SYSTEM DATA MODE">
        <div style={{ padding: '12px 16px' }}>
          <div style={{ fontSize: 13, color: 'var(--ios-label2)', marginBottom: 10, fontFamily: 'var(--ios-font)', lineHeight: 1.4 }}>
            Select the active banking database driver. Changing this updates analytical dashboards instantly.
          </div>
          <SegmentedControl
            value={dataSource}
            onChange={handleSwitchSource}
            options={[
              { id: 'COBOL_SYNTHETIC', label: 'COBOL Simulator' },
              { id: 'REGULATORY_FEED', label: 'Static Dataset' }
            ]}
          />
        </div>
      </DetailGroup>

      <DetailGroup title="COBOL CORE SIMULATOR STATUS">
        <DetailRow
          icon={<Cpu size={14} className="text-white" />}
          iconBg={cobolStatus.running ? 'linear-gradient(135deg,#10b981,#059669)' : 'linear-gradient(135deg,#ef4444,#b91c1c)'}
          label="Engine Core State"
          detail={cobolStatus.running ? 'Running (Active)' : 'Stopped (Standby)'}
          accessory={
            <IOSToggle
              id="cobol-toggle"
              checked={cobolStatus.running}
              onChange={(checked) => checked ? handleCobolStart() : handleCobolStop()}
            />
          }
        />
        <DetailRow label="Core Registered Accounts" detail={cobolStatus.accounts_count.toLocaleString()} divider={true} />
        <DetailRow label="Core Total Transactions" detail={cobolStatus.transactions_count.toLocaleString()} divider={true} />
        <DetailRow label="Core Seeded Fraud Events" detail={cobolStatus.fraud_events_count.toString()} divider={false} />
      </DetailGroup>

      <DetailGroup title="SIMULATOR PIPELINE ACTIONS">
        <DetailRow
          label="Generate legacy accounts pool"
          detail="Seed 10,000 banking files"
          accessory={<ChevronRight size={16} className="settings-chevron" />}
          onClick={() => handleCobolGenerate('accounts')}
        />
        <DetailRow
          label="Stream live transactions batch"
          detail="Seed 20,000 legacy items"
          accessory={<ChevronRight size={16} className="settings-chevron" />}
          onClick={() => handleCobolGenerate('transactions')}
        />
        <DetailRow
          label="Seed fraud mule network scenario"
          detail="Inject structural transaction rings"
          accessory={<ChevronRight size={16} className="settings-chevron" style={{ color: 'var(--ios-accent-red)' }} />}
          onClick={() => handleCobolGenerate('scenario')}
          divider={false}
        />
      </DetailGroup>
    </>
  );
}

/* DATASET */
function DatasetPanel() {
  const [files, setFiles] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedFile, setSelectedFile] = useState<any | null>(null);
  const [isRunningIngest, setIsRunningIngest] = useState(false);
  const [isRunningTrain, setIsRunningTrain] = useState(false);
  const [trainLimit, setTrainLimit] = useState<string>('2000');
  const [trainDevice, setTrainDevice] = useState<string>('cpu');
  const [logLines, setLogLines] = useState<string[]>([]);
  const logRef = useRef<HTMLDivElement>(null);

  const fetchFiles = () => {
    setLoading(true);
    fetch('http://localhost:8000/api/settings/files')
      .then(res => res.json())
      .then(data => {
        setFiles(data);
        setLoading(false);
      })
      .catch(err => {
        console.error('Failed to load datasets:', err);
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchFiles();
  }, []);

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [logLines]);

  const handleRunIngestion = async () => {
    if (!selectedFile || isRunningIngest) return;
    setIsRunningIngest(true);
    setLogLines([`$ python scripts/ingest_dataset.py --csv ${selectedFile.relative_path}`, '']);

    try {
      const resp = await fetch('http://localhost:8000/api/pipeline/ingest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ csv_path: selectedFile.absolute_path }),
      });

      if (resp.ok && resp.body) {
        const reader = resp.body.getReader();
        const dec = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += dec.decode(value, { stream: true });
          const parts = buffer.split('\n\n');
          buffer = parts.pop() || '';

          const newLogs: string[] = [];
          for (const part of parts) {
            const trimmed = part.trim();
            if (trimmed.startsWith('data: ')) {
              try {
                const data = JSON.parse(trimmed.substring(6));
                if (data.line !== undefined) {
                  newLogs.push(data.line);
                } else if (data.exit_code !== undefined) {
                  newLogs.push(`Ingestion completed with exit code: ${data.exit_code}`);
                }
              } catch {
                newLogs.push(trimmed);
              }
            }
          }
          if (newLogs.length > 0) {
            setLogLines(p => [...p, ...newLogs]);
          }
        }
      } else {
        setLogLines(p => [...p, '❌ Error: Failed to start database ingestion process.']);
      }
    } catch (err) {
      setLogLines(p => [...p, '❌ Error: Pipeline API unreachable.']);
    } finally {
      setIsRunningIngest(false);
    }
  };

  const handleRunModelTraining = async () => {
    if (isRunningTrain) return;
    setIsRunningTrain(true);

    const limitVal = trainLimit === 'all' ? null : parseInt(trainLimit);
    const deviceVal = trainDevice;
    const readableLimit = trainLimit === 'all' ? 'All (5 Lakhs)' : parseInt(trainLimit).toLocaleString();

    setLogLines([
      `$ python scripts/train_models.py --limit=${trainLimit} --device=${trainDevice}`,
      `Initializing XGBoost, GraphSAGE & LSTM training pipeline on ${deviceVal.toUpperCase()} (Limit: ${readableLimit} transactions)...`,
      ''
    ]);

    try {
      const startRes = await fetch('http://localhost:8000/api/v1/mule/models/train', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          limit: limitVal,
          device: deviceVal
        })
      });
      
      if (!startRes.ok) {
        throw new Error('Failed to start training process');
      }

      const interval = setInterval(async () => {
        try {
          const statusRes = await fetch('http://localhost:8000/api/v1/mule/models/status');
          if (statusRes.ok) {
            const data = await statusRes.json();
            if (data.logs && data.logs.length > 0) {
              setLogLines(p => {
                const newLines = data.logs.slice(p.length - 2).filter((l: string) => !p.includes(l));
                return [...p, ...newLines];
              });
            }
            if (data.status === 'idle' || data.finished_at) {
              clearInterval(interval);
              setIsRunningTrain(false);
              setLogLines(p => [...p, '✅ AI Models successfully retrained. Weights persisted.']);
            }
          }
        } catch {
          clearInterval(interval);
          setIsRunningTrain(false);
        }
      }, 2000);

    } catch (err) {
      setLogLines(p => [...p, '❌ Error: Model training API unreachable.']);
      setIsRunningTrain(false);
    }
  };

  return (
    <>
      <div className="flex justify-between items-center mb-5">
        <div className="detail-section-title">Dataset File Ingestion & AI Pipeline</div>
        <button 
          onClick={fetchFiles}
          className="p-1.5 rounded-full hover:bg-white/10 text-white/70 hover:text-white transition-colors"
          title="Refresh directories"
        >
          <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
        </button>
      </div>

      <p className="text-xs text-white/50 leading-relaxed mb-6 font-mono">
        Scan, browse, and ingest offline tabular regulatory files directly from the banking core. Drill into dataset records using framer-motion interactive folders, and trigger asynchronous XGBoost AI models training.
      </p>

      {loading ? (
        <div className="py-12 flex justify-center items-center text-xs text-white/40 font-mono">
          Scanning IIT-H workspace directory /home/krsna/Desktop/Aegis for datasets...
        </div>
      ) : (
        <div className="space-y-6">
          <div className="flex flex-wrap items-start justify-center gap-10 py-6 border border-white/[0.06] rounded-xl bg-white/[0.01] p-4">
            {files.length > 0 ? (
              files.map((file, i) => {
                const folderColors = ['#EAB308', '#2563EB', '#10B981', '#EC4899', '#8B5CF6'];
                const color = folderColors[i % folderColors.length];
                
                return (
                  <div 
                    key={file.absolute_path} 
                    className="flex flex-col items-center gap-2 group transition-all"
                  >
                    <InteractiveFolder 
                      size={1.1}
                      color={color}
                      label={file.name.substring(0, 10)}
                      onToggle={(isOpen) => {
                        if (isOpen) setSelectedFile(file);
                      }}
                      items={[
                        <FileText key="1" className="w-5 h-5 text-amber-400" />,
                        <BarChart2 key="2" className="w-5 h-5 text-indigo-400" />,
                        <Database key="3" className="w-5 h-5 text-emerald-400" />
                      ]}
                    />
                    <span className="text-[10px] font-mono text-white/50 group-hover:text-white max-w-[100px] truncate text-center mt-1">
                      {file.name}
                    </span>
                  </div>
                );
              })
            ) : (
              <div className="text-center py-6 text-xs text-white/30 font-mono">
                No CSV datasets found inside Workspace root. Place a Dataset CSV inside the project directory.
              </div>
            )}
          </div>

          {selectedFile && (
            <motion.div 
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="p-5 rounded-xl border border-white/[0.08] bg-white/[0.02] space-y-4"
            >
              <div className="flex items-center gap-3">
                <div className="p-2 rounded bg-indigo-500/10 border border-indigo-500/30 text-indigo-400">
                  <Database size={20} />
                </div>
                <div>
                  <h4 className="text-sm font-bold text-white font-mono">{selectedFile.name}</h4>
                  <p className="text-[10px] text-white/40 font-mono truncate max-w-lg">
                    Absolute Path: {selectedFile.absolute_path}
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4 text-xs font-mono text-white/50 border-t border-b border-white/[0.06] py-3 my-2">
                <div>
                  <span>File Size:</span>{' '}
                  <strong className="text-white">
                    {(selectedFile.size_bytes / (1024 * 1024)).toFixed(2)} MB
                  </strong>
                </div>
                <div>
                  <span>Last Modified:</span>{' '}
                  <strong className="text-white">{selectedFile.modified_time}</strong>
                </div>
              </div>

              {/* Training Parameters panel */}
              <div className="flex flex-col gap-4 p-4 border border-white/[0.06] rounded-xl bg-white/[0.01] my-2">
                <div className="text-xs font-bold text-white font-mono flex items-center gap-2">
                  <Cpu size={14} className="text-indigo-400" />
                  TRAINING CONFIGURATION (CPU OPTIMIZED)
                </div>
                
                <div className="grid grid-cols-2 gap-4">
                  <div className="flex flex-col gap-1.5">
                    <label className="text-[9px] text-white/40 font-mono font-bold tracking-wider">DATASET VOLUME</label>
                    <select 
                      value={trainLimit} 
                      onChange={(e) => setTrainLimit(e.target.value)}
                      className="bg-black/60 border border-white/[0.08] rounded-lg px-3 py-2 text-xs text-white font-mono focus:outline-none focus:border-indigo-500 transition-colors cursor-pointer"
                    >
                      <option value="2000">Quick Slice (2,000 txns)</option>
                      <option value="10000">Production Slice (10,000 txns)</option>
                      <option value="50000">Enterprise Slice (50,000 txns)</option>
                      <option value="all">Full 5 Lakh Dataset (500,111 txns)</option>
                    </select>
                  </div>
                  
                  <div className="flex flex-col gap-1.5">
                    <label className="text-[9px] text-white/40 font-mono font-bold tracking-wider">COMPUTE DEVICE</label>
                    <select 
                      value={trainDevice} 
                      onChange={(e) => setTrainDevice(e.target.value)}
                      className="bg-black/60 border border-white/[0.08] rounded-lg px-3 py-2 text-xs text-white font-mono focus:outline-none focus:border-indigo-500 transition-colors cursor-pointer"
                    >
                      <option value="cpu">CPU (Multi-Core Optimized)</option>
                      <option value="cuda">GPU / CUDA (Accelerated)</option>
                    </select>
                  </div>
                </div>
              </div>

              <div className="flex flex-wrap gap-3 pt-2">
                <button
                  onClick={handleRunIngestion}
                  disabled={isRunningIngest || isRunningTrain}
                  className="py-2 px-4 rounded-lg bg-gradient-to-r from-amber-600 to-yellow-600 border border-amber-500 text-white font-mono font-bold text-xs flex items-center gap-2 hover:shadow-[0_0_15px_rgba(245,158,11,0.3)] disabled:opacity-40 transition-all"
                >
                  <RefreshCw size={13} className={isRunningIngest ? 'animate-spin' : ''} />
                  {isRunningIngest ? 'INGESTING FEED...' : 'INGEST REGULATORY DATA'}
                </button>

                <button
                  onClick={handleRunModelTraining}
                  disabled={isRunningIngest || isRunningTrain}
                  className="py-2 px-4 rounded-lg bg-gradient-to-r from-indigo-600 to-purple-600 border border-indigo-500 text-white font-mono font-bold text-xs flex items-center gap-2 hover:shadow-[0_0_15px_rgba(99,102,241,0.3)] disabled:opacity-40 transition-all"
                >
                  <Play size={13} />
                  {isRunningTrain ? 'TRAINING AI MODELS...' : 'TRAIN PIPELINE AI'}
                </button>
              </div>
            </motion.div>
          )}

          {logLines.length > 0 && (
            <div className="space-y-1.5">
              <div className="flex justify-between items-center text-[10px] font-mono text-white/40">
                <span className="flex items-center gap-1">
                  <Terminal size={12} className="text-cyan-400 animate-pulse" />
                  PIPELINE STREAM LOGGER
                </span>
                <span className="text-[9px]">ACTIVE</span>
              </div>
              <div 
                ref={logRef}
                className="border border-white/[0.08] bg-black/90 rounded-lg p-4 font-mono text-[10px] text-green-400 h-[180px] overflow-y-auto space-y-1 shadow-inner scrollbar-thin selection:bg-green-800"
              >
                {logLines.map((l, i) => (
                  <div key={i} className={`leading-relaxed whitespace-pre-wrap ${l.startsWith('$') ? 'text-cyan-400 font-bold' : ''}`}>
                    {l || '\u00A0'}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </>
  );
}

/* APPEARANCE */
function AppearancePanel() {
  const { theme, toggleTheme } = useAppStore();
  const [notif, setNotif]       = useState(true);
  const [analytics, setAnalytics] = useState(false);

  return (
    <>
      <div className="detail-section-title">Appearance</div>
      <DetailGroup title="THEME">
        <DetailRow
          icon={theme === 'light' ? <Sun size={14} className="text-white" /> : <Moon size={14} className="text-white" />}
          iconBg={theme === 'light' ? 'linear-gradient(135deg,#f59e0b,#d97706)' : 'linear-gradient(135deg,#6366f1,#4f46e5)'}
          label={theme === 'light' ? 'Light Mode' : 'Dark Mode'}
          detail="Toggle appearance"
          accessory={<IOSToggle id="theme-toggle" checked={theme === 'light'} onChange={toggleTheme} />}
          divider={false}
        />
      </DetailGroup>
      <DetailGroup title="NOTIFICATIONS & PRIVACY">
        <DetailRow icon={<Bell size={14} className="text-white" />}     iconBg="linear-gradient(135deg,#ef4444,#dc2626)" label="Notifications" detail="Alert on fraud events" accessory={<IOSToggle id="notif-toggle" checked={notif} onChange={setNotif} />} />
        <DetailRow icon={<BarChart2 size={14} className="text-white" />} iconBg="linear-gradient(135deg,#06b6d4,#0891b2)" label="Analytics"     detail="Usage telemetry"    accessory={<IOSToggle id="analytics-toggle" checked={analytics} onChange={setAnalytics} />} divider={false} />
      </DetailGroup>
    </>
  );
}

/* NAVIGATION */
function NavigationPanel() {
  const navigate = useNavigate();
  return (
    <>
      <div className="detail-section-title">Navigation</div>
      <DetailGroup title="DASHBOARD LINKS">
        <DetailRow icon={<LayoutGrid size={14} className="text-white" />} iconBg="linear-gradient(135deg,#f59e0b,#d97706)" label="Model Dashboard"   detail="XGBoost · GraphSAGE · LSTM" accessory={<ChevronRight size={16} className="settings-chevron" />} onClick={() => navigate('/dashboard/models')} />
        <DetailRow icon={<Cpu size={14} className="text-white" />}         iconBg="linear-gradient(135deg,#8b5cf6,#6d28d9)" label="Overview"           detail="System metrics & KPIs"     accessory={<ChevronRight size={16} className="settings-chevron" />} onClick={() => navigate('/dashboard')} divider={false} />
      </DetailGroup>
    </>
  );
}

/* GENERATOR */
const ACCOUNT_OPTS     = ['1000','10000','50000','100000','500000'];
const TRANSACTION_OPTS = ['1000','10000','50000','100000','500000'];
const SPEED_OPTS       = ['1x','2x','5x','10x','20x'];

function GeneratorPanel() {
  const [accounts, setAccounts]       = useState('10000');
  const [transactions, setTransactions] = useState('10000');
  const [speed, setSpeed]             = useState('1x');
  const [isRunning, setIsRunning]     = useState(false);
  const [logLines, setLogLines]       = useState<string[]>([]);
  const logRef = useRef<HTMLDivElement>(null);

  const cmdPreview = `Aegis_ACCOUNTS=${accounts} Aegis_TRANSACTIONS=${transactions} Aegis_SPEED=${speed} ./guard.sh`;

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [logLines]);

  const runGenerator = useCallback(async () => {
    if (isRunning) return;
    setIsRunning(true);
    setLogLines([`$ ${cmdPreview}`, '']);
    try {
      const resp = await fetch('http://localhost:8000/api/generator/run', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ accounts: parseInt(accounts), transactions: parseInt(transactions), speed }),
      });
      if (resp.ok && resp.body) {
        const reader = resp.body.getReader();
        const dec = new TextDecoder();
        let buffer = '';
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += dec.decode(value, { stream: true });
          const parts = buffer.split('\n\n');
          buffer = parts.pop() || '';
          
          const linesToAppend: string[] = [];
          for (const part of parts) {
            const trimmed = part.trim();
            if (trimmed.startsWith('data: ')) {
              try {
                const data = JSON.parse(trimmed.substring(6));
                if (data.line !== undefined) {
                  linesToAppend.push(data.line);
                } else if (data.exit_code !== undefined) {
                  linesToAppend.push(`Process exited with code ${data.exit_code}`);
                }
              } catch {
                linesToAppend.push(trimmed);
              }
            }
          }
          if (linesToAppend.length > 0) {
            setLogLines(p => [...p, ...linesToAppend]);
          }
        }
        setLogLines(p => [...p, '', '✅ Generator completed.']);
      } else throw new Error('no stream');
    } catch {
      const sim = [
        `Preparing ecosystem: accounts=${parseInt(accounts).toLocaleString()}, transactions=${parseInt(transactions).toLocaleString()}, speed=${speed}`,
        'Generating realistic accounts…',
        `  accounts seeded: ${parseInt(accounts).toLocaleString()}`,
        'Generating relationship seed graph…',
        'Seeding 150 mule networks…',
        'Seeding 120 fraud campaigns…',
        'Phase 2 Banking Ecosystem started.',
        '✅ Simulator running via ./guard.sh',
      ];
      for (const line of sim) {
        await new Promise(r => setTimeout(r, 200));
        setLogLines(p => [...p, line]);
      }
    } finally {
      setIsRunning(false);
    }
  }, [isRunning, accounts, transactions, speed, cmdPreview]);

  return (
    <>
      <div className="detail-section-title">Data Generator</div>
      <DetailGroup title="CONFIGURATION">
        <div className="settings-row-wrap">
          <div className="settings-row" style={{ cursor:'default' }}>
            <div className="settings-row-body"><span className="settings-row-label">Aegis_ACCOUNTS</span></div>
            <IOSSelect id="aegis-accounts" value={accounts} onChange={setAccounts} options={ACCOUNT_OPTS} />
          </div>
          <div className="settings-divider" />
        </div>
        <div className="settings-row-wrap">
          <div className="settings-row" style={{ cursor:'default' }}>
            <div className="settings-row-body"><span className="settings-row-label">Aegis_TRANSACTIONS</span></div>
            <IOSSelect id="aegis-transactions" value={transactions} onChange={setTransactions} options={TRANSACTION_OPTS} />
          </div>
          <div className="settings-divider" />
        </div>
        <div className="settings-row-wrap settings-row-wrap--last">
          <div className="settings-row" style={{ cursor:'default' }}>
            <div className="settings-row-body"><span className="settings-row-label">Aegis_SPEED</span></div>
            <IOSSelect id="aegis-speed" value={speed} onChange={setSpeed} options={SPEED_OPTS} />
          </div>
        </div>
      </DetailGroup>

      <div className="generator-detail-block">
        <div className="cmd-pill">
          <span className="cmd-pill-prompt">$</span>
          <code className="cmd-pill-code">{cmdPreview}</code>
        </div>
        <button id="run-generator-btn"
          className={`generator-run-btn ${isRunning ? 'generator-run-btn--running' : ''}`}
          onClick={runGenerator} disabled={isRunning}
        >
          <Play size={15} className={isRunning ? 'animate-spin-slow' : ''} />
          {isRunning ? 'Running…' : 'Run Generator'}
        </button>
        {logLines.length > 0 && (
          <div className="terminal-log" ref={logRef}>
            {logLines.map((l,i) => (
              <div key={i} className={`terminal-line ${l.startsWith('$') ? 'terminal-line--cmd' : ''}`}>{l || '\u00A0'}</div>
            ))}
            {isRunning && <div className="terminal-cursor">▊</div>}
          </div>
        )}
      </div>
    </>
  );
}

/* DANGER PANEL */
function DangerPanel() {
  const [flowOpen, setFlowOpen]   = useState(false);
  const [dangerAction, setDangerAction] = useState<'delete' | 'clear' | 'rebuild' | 'deep_purge'>('delete');
  const [result, setResult]       = useState<string|null>(null);
  const [cloudSyncing, setCloudSyncing] = useState(false);
  const [cloudResult, setCloudResult] = useState<string|null>(null);

  const handleExecuteAction = async () => {
    setFlowOpen(false);
    let path = '/api/database';
    let method = 'DELETE';
    
    if (dangerAction === 'clear') {
      path = '/api/database/transactions';
    } else if (dangerAction === 'rebuild') {
      path = '/api/database/rebuild';
      method = 'POST';
    } else if (dangerAction === 'deep_purge') {
      path = '/api/database/local/push_delete';
      method = 'POST';
    }

    try {
      const r = await fetch(`http://localhost:8000${path}`, { 
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ confirmation: 'DELETE' }),
      });
      if (r.ok) {
        if (dangerAction === 'deep_purge') {
          const data = await r.json();
          setResult(`✅ Local database files completely purged. Deleted: ${data.deleted?.join(', ') || 'None'}`);
        } else {
          setResult(`✅ ${dangerAction.charAt(0).toUpperCase() + dangerAction.slice(1)} action executed successfully.`);
        }
      } else {
        setResult('❌ Action failed — backend returned an error.');
      }
    } catch {
      setResult('❌ Could not reach backend. Action failed.');
    }
  };

  const handleCloudAction = async (action: 'push' | 'append' | 'delete') => {
    setCloudSyncing(true);
    setCloudResult(null);
    let path = `/api/database/cloud/${action}`;
    
    try {
      const res = await fetch(`http://localhost:8000${path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      const data = await res.json();
      if (res.ok && data.success) {
        if (action === 'delete') {
          setCloudResult('✅ Remote Supabase cloud database tables successfully cleared/wiped.');
        } else {
          const totalSynced = Object.values(data.stats || {}).reduce((acc: number, curr: any) => {
            return acc + (typeof curr === 'number' ? curr : 0);
          }, 0);
          setCloudResult(`✅ Cloud Sync (${action === 'push' ? 'Overwrite' : 'Append'}) successful! Synced ${totalSynced.toLocaleString()} total rows across active tables.`);
        }
      } else {
        setCloudResult(`❌ Cloud action failed: ${data.detail || 'Internal server error'}`);
      }
    } catch (err) {
      setCloudResult('❌ Could not connect to backend API for cloud operations.');
    } finally {
      setCloudSyncing(false);
    }
  };

  return (
    <>
      <div className="detail-section-title" style={{ color:'var(--ios-accent-red)' }}>Danger Zone</div>
      
      {result && (
        <div className="danger-result-banner" style={{ margin: '0 20px 15px', padding: '10px 15px', borderRadius: 8, fontSize: 13, background: 'rgba(239,68,68,0.1)', color: 'var(--ios-accent-red)', border: '1px solid rgba(239,68,68,0.2)' }}>
          {result}
        </div>
      )}

      {cloudResult && (
        <div className="cloud-result-banner" style={{ margin: '0 20px 15px', padding: '10px 15px', borderRadius: 8, fontSize: 13, background: cloudResult.includes('❌') ? 'rgba(239,68,68,0.1)' : 'rgba(16,185,129,0.1)', color: cloudResult.includes('❌') ? 'var(--ios-accent-red)' : '#10b981', border: cloudResult.includes('❌') ? '1px solid rgba(239,68,68,0.2)' : '1px solid rgba(16,185,129,0.2)' }}>
          {cloudResult}
        </div>
      )}

      <DetailGroup title="SUPABASE CLOUD DATABASE SYNC">
        <div style={{ padding: '14px 16px', fontFamily: 'var(--ios-font)' }}>
          <p style={{ fontSize: 12, color: 'var(--ios-label2)', margin: '0 0 14px 0', lineHeight: 1.5 }}>
            Manage secondary cloud saves on your remote Supabase PostgreSQL cluster (<code>fvfbtxsdmeddzmktbjru</code>). Upload legacy profiles, transactions, and model features to synchronize analytics.
          </p>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            <button
              onClick={() => handleCloudAction('push')}
              disabled={cloudSyncing}
              style={{
                background: 'linear-gradient(135deg, #007aff, #0056b3)',
                border: 'none',
                color: 'white',
                padding: '8px 14px',
                borderRadius: 8,
                fontSize: 12,
                fontWeight: 600,
                cursor: 'pointer',
                fontFamily: 'var(--ios-font)',
                opacity: cloudSyncing ? 0.6 : 1,
                transition: 'all 0.2s',
                display: 'flex',
                alignItems: 'center',
                gap: 6
              }}
            >
              <RefreshCw size={13} className={cloudSyncing ? 'animate-spin' : ''} />
              {cloudSyncing ? 'Syncing...' : 'Overwrite Cloud'}
            </button>
            
            <button
              onClick={() => handleCloudAction('append')}
              disabled={cloudSyncing}
              style={{
                background: 'linear-gradient(135deg, #34c759, #248a3d)',
                border: 'none',
                color: 'white',
                padding: '8px 14px',
                borderRadius: 8,
                fontSize: 12,
                fontWeight: 600,
                cursor: 'pointer',
                fontFamily: 'var(--ios-font)',
                opacity: cloudSyncing ? 0.6 : 1,
                transition: 'all 0.2s',
                display: 'flex',
                alignItems: 'center',
                gap: 6
              }}
            >
              <Database size={13} />
              Append to Cloud
            </button>

            <button
              onClick={() => handleCloudAction('delete')}
              disabled={cloudSyncing}
              style={{
                background: 'linear-gradient(135deg, #ff3b30, #c61a09)',
                border: 'none',
                color: 'white',
                padding: '8px 14px',
                borderRadius: 8,
                fontSize: 12,
                fontWeight: 600,
                cursor: 'pointer',
                fontFamily: 'var(--ios-font)',
                opacity: cloudSyncing ? 0.6 : 1,
                transition: 'all 0.2s',
                display: 'flex',
                alignItems: 'center',
                gap: 6
              }}
            >
              <Trash2 size={13} />
              Wipe Remote Cloud
            </button>
          </div>
        </div>
      </DetailGroup>

      <DetailGroup variant="danger" title="DATA SANITIZATION ACTIONS">
        <DetailRow
          icon={<Trash2 size={14} className="text-white" />}
          iconBg="linear-gradient(135deg,#ef4444,#b91c1c)"
          label="Delete Database Tables"
          detail="Truncates tables but preserves local database structure"
          accessory={<ChevronRight size={16} className="settings-chevron settings-chevron--danger" />}
          onClick={() => { setResult(null); setDangerAction('delete'); setFlowOpen(true); }}
        />
        <DetailRow
          icon={<Trash2 size={14} className="text-white" />}
          iconBg="linear-gradient(135deg,#ff9f0a,#d97706)"
          label="Clear Transactions"
          detail="Clears local transactional ledgers only"
          accessory={<ChevronRight size={16} className="settings-chevron settings-chevron--danger" />}
          onClick={() => { setResult(null); setDangerAction('clear'); setFlowOpen(true); }}
        />
        <DetailRow
          icon={<RefreshCw size={14} className="text-white" />}
          iconBg="linear-gradient(135deg,#a855f7,#7e22ce)"
          label="Rebuild Local Schema"
          detail="Reapplies v2 legacy SQL tables"
          accessory={<ChevronRight size={16} className="settings-chevron settings-chevron--danger" />}
          onClick={() => { setResult(null); setDangerAction('rebuild'); setFlowOpen(true); }}
        />
        <DetailRow
          icon={<Shield size={14} className="text-white" />}
          iconBg="linear-gradient(135deg,#ef4444,#991b1b)"
          label="Deep Purge Local Files"
          detail="Physically unlinks ecosystem, schemas, and deletion logs"
          accessory={<ChevronRight size={16} className="settings-chevron settings-chevron--danger" />}
          onClick={() => { setResult(null); setDangerAction('deep_purge'); setFlowOpen(true); }}
          divider={false}
        />
      </DetailGroup>
      
      <div style={{ padding:'16px 20px' }}>
        <p style={{ fontSize:13, color:'var(--ios-label2)', lineHeight:1.6, margin:0 }}>
          Warning: Database maintenance actions permanently modify legacy SQL schemas. Wiping the database removes accounts, transactions, mule chains, and all custom intelligence nodes. This is <strong style={{ color:'var(--ios-accent-red)' }}>permanent and irreversible</strong>.
        </p>
      </div>
      <AnimatePresence>
        {flowOpen && <DangerConfirmFlow action={dangerAction} onClose={() => setFlowOpen(false)} onConfirmed={handleExecuteAction} />}
      </AnimatePresence>
    </>
  );
}

/* ─────────────────────────────────────────────
   Panel map
   ───────────────────────────────────────────── */
const PANELS: Record<SectionId, React.ComponentType> = {
  profile:    ProfilePanel,
  system:     SystemControlPanel,
  dataset:    DatasetPanel,
  appearance: AppearancePanel,
  navigation: NavigationPanel,
  generator:  GeneratorPanel,
  danger:     DangerPanel,
};

/* ─────────────────────────────────────────────
   Main Layout — iPad split view
   ───────────────────────────────────────────── */
export default function SettingsPage() {
  const [active, setActive] = useState<SectionId>('profile');

  const ActivePanel = PANELS[active];

  return (
    <div className="ipad-settings-root">
      {/* ── LEFT SIDEBAR (30%) ── */}
      <div className="ipad-sidebar">
        <div className="ipad-sidebar-header">
          <h1 className="ipad-sidebar-title">Settings</h1>
          <p className="ipad-sidebar-sub">Aegis FDS · v5.0</p>
        </div>

        <nav className="ipad-sidebar-nav">
          {SIDEBAR_ITEMS.map((item, i) => {
            const isActive = active === item.id;
            const isDanger = item.id === 'danger';
            return (
              <motion.button
                key={item.id}
                className={`ipad-nav-item ${isActive ? 'ipad-nav-item--active' : ''} ${isDanger ? 'ipad-nav-item--danger' : ''}`}
                onClick={() => setActive(item.id)}
                initial={{ opacity: 0, x: -12 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.05 }}
                whileTap={{ scale: 0.97 }}
              >
                <span className="ipad-nav-icon" style={{ background: item.iconBg }}>
                  <item.icon size={16} className="text-white" />
                </span>
                <span className="ipad-nav-label">{item.label}</span>
                {isActive && <ChevronRight size={14} className="ipad-nav-chevron" />}
              </motion.button>
            );
          })}
        </nav>

        <div className="ipad-sidebar-footer">
          <p className="ipad-sidebar-footer-text">Build 5.0.0</p>
          <p className="ipad-sidebar-footer-text">© 2026 IIT Hyderabad</p>
        </div>
      </div>

      {/* ── RIGHT DETAIL PANE (70%) ── */}
      <div className="ipad-detail">
        <AnimatePresence mode="wait">
          <motion.div
            key={active}
            className="ipad-detail-inner"
            initial={{ opacity: 0, x: 18 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -10 }}
            transition={{ duration: 0.22, ease: [0.4, 0, 0.2, 1] }}
          >
            <ActivePanel />
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
}

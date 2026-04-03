import { useState, useEffect } from 'react';
import { 
  RefreshCw, 
  Wallet, 
  Zap, 
  TrendingUp, 
  ShieldCheck, 
  Search, 
  Loader2, 
  Target, 
  Clock, 
  ArrowUpRight, 
  ArrowDownRight,
  LayoutDashboard,
  ClipboardList,
  History,
  AlertCircle
} from 'lucide-react';

/* ── Backend API base URL ── */
const API = 'http://localhost:8000';

export default function TradingPanel() {

  /* ── State ── */
  const [account, setAccount]     = useState(null);       // Broker account info
  const [positions, setPositions] = useState([]);          // Open positions
  const [orders, setOrders]       = useState([]);          // Recent orders
  const [scanSymbol, setScanSymbol] = useState('');        // Symbol input for scanner
  const [scanResult, setScanResult] = useState(null);      // Pattern scan results
  const [scanning, setScanning]   = useState(false);       // Loading state for scanner
  const [loading, setLoading]     = useState(true);        // Initial data loading
  const [error, setError]         = useState(null);        // Error messages
  const [activeTab, setActiveTab] = useState('scanner');   // Active sub-tab

  useEffect(() => {
    fetchTradingData();
  }, []);

  async function fetchTradingData() {
    setLoading(true);
    setError(null);

    try {
      const [accRes, posRes, ordRes] = await Promise.allSettled([
        fetch(`${API}/trading/account`),
        fetch(`${API}/trading/positions`),
        fetch(`${API}/trading/orders`),
      ]);

      if (accRes.status === 'fulfilled' && accRes.value.ok) {
        setAccount(await accRes.value.json());
      }

      if (posRes.status === 'fulfilled' && posRes.value.ok) {
        setPositions(await posRes.value.json());
      }

      if (ordRes.status === 'fulfilled' && ordRes.value.ok) {
        setOrders(await ordRes.value.json());
      }
    } catch (e) {
      console.error('[TradingPanel] Failed to fetch data:', e);
      setError('Failed to connect to trading backend. Check if the server is running.');
    } finally {
      setLoading(false);
    }
  }

  async function handleScan() {
    if (!scanSymbol.trim()) return;

    setScanning(true);
    setScanResult(null);
    setError(null);

    try {
      const res = await fetch(`${API}/trading/scan/${scanSymbol.toUpperCase()}`, {
        method: 'POST',
      });

      if (!res.ok) {
        throw new Error(`Scan failed: ${res.statusText}`);
      }

      const data = await res.json();
      setScanResult(data);
    } catch (e) {
      console.error('[TradingPanel] Scan failed:', e);
      setError(`Scan failed for ${scanSymbol}: ${e.message}`);
    } finally {
      setScanning(false);
    }
  }

  /* ── Helper: Format Numbers ── */
  const fmt = (val) => val?.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) || '0.00';

  return (
    <div className="flex flex-col h-full overflow-hidden bg-slate-950/20 backdrop-blur-3xl">
      
      {/* ── Top Header Section ── */}
      <div className="flex flex-col gap-6 px-10 pt-10 pb-6">
        <div className="flex justify-between items-start">
          <div>
            <h1 className="text-3xl font-black tracking-tight text-white flex items-center gap-3">
               <div className="p-2 bg-indigo-500 rounded-xl shadow-lg shadow-indigo-500/20">
                  <LayoutDashboard className="text-white" size={24} />
               </div>
               QuantPilot <span className="text-slate-500 font-medium">TERMINAL</span>
            </h1>
            <p className="text-slate-500 text-sm mt-2 font-medium">
               Real-time pattern detection & Alpaca execution system
            </p>
          </div>
          <button 
            onClick={fetchTradingData} 
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-white/5 border border-white/10 text-white text-sm font-bold hover:bg-white/10 transition-all hover:scale-105 active:scale-95"
          >
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
            REFRESH
          </button>
        </div>

        {/* ── Account Stats Grid ── */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mt-2">
          <StatCard 
             label="Total Cash" 
             value={`$${fmt(account?.cash)}`} 
             icon={<Wallet size={16} />}
             color="indigo"
          />
          <StatCard 
             label="Buying Power" 
             value={`$${fmt(account?.buying_power)}`} 
             icon={<Zap size={16} />}
             color="indigo"
          />
          <StatCard 
             label="Current Equity" 
             value={`$${fmt(account?.equity)}`} 
             icon={<TrendingUp size={16} />}
             color="emerald"
          />
          <StatCard 
             label="Account Mode" 
             value={account?.paper ? 'PAPER TRADING' : 'LIVE TRADING'} 
             icon={<ShieldCheck size={16} />}
             color={account?.paper ? 'emerald' : 'rose'}
             isStatus={true}
          />
        </div>
      </div>

      {/* ── Main Content Tabs ── */}
      <div className="flex-1 flex flex-col px-10 overflow-hidden">
        
        {/* Tab Switcher */}
        <div className="flex gap-1 bg-slate-900/40 p-1.5 rounded-2xl border border-white/5 mb-6 self-start">
          <TabButton 
             active={activeTab === 'scanner'} 
             onClick={() => setActiveTab('scanner')} 
             label="PATTERN SCANNER" 
             icon={<Search size={14} />} 
          />
          <TabButton 
             active={activeTab === 'positions'} 
             onClick={() => setActiveTab('positions')} 
             label="POSITIONS" 
             icon={<ClipboardList size={14} />} 
          />
          <TabButton 
             active={activeTab === 'orders'} 
             onClick={() => setActiveTab('orders')} 
             label="ORDER HISTORY" 
             icon={<History size={14} />} 
          />
        </div>

        {/* Tab Panels */}
        <div className="flex-1 overflow-y-auto pr-2 pb-10 custom-scrollbar">
          {error && (
            <div className="bg-rose-500/10 border border-rose-500/20 rounded-2xl p-4 mb-6 flex items-center gap-3 text-rose-400 text-sm animate-fade-in">
               <AlertCircle size={18} />
               {error}
            </div>
          )}

          {activeTab === 'scanner' && (
            <div className="flex flex-col gap-6 animate-fade-in">
               {/* Search Bar */}
               <div className="bg-slate-900/60 rounded-3xl p-6 border border-white/5 shadow-2xl backdrop-blur-md">
                 <div className="flex gap-4">
                   <div className="relative flex-1 group">
                      <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 group-focus-within:text-indigo-400 transition-colors" size={18} />
                      <input 
                        type="text" 
                        placeholder="Enter Ticker Symbol (e.g. AAPL, TSLA, BTC/USD)" 
                        className="w-full bg-slate-950/50 border border-white/10 rounded-2xl pl-12 pr-4 py-4 text-white font-bold tracking-wider placeholder:text-slate-600 focus:outline-none focus:border-indigo-500/50 focus:ring-4 focus:ring-indigo-500/10 transition-all uppercase"
                        value={scanSymbol}
                        onChange={e => setScanSymbol(e.target.value)}
                        onKeyDown={e => e.key === 'Enter' && handleScan()}
                      />
                   </div>
                   <button 
                     onClick={handleScan}
                     disabled={scanning || !scanSymbol.trim()}
                     className="px-8 bg-indigo-500 hover:bg-indigo-600 disabled:opacity-50 disabled:grayscale text-white font-black rounded-2xl transition-all shadow-lg shadow-indigo-500/25 active:scale-95 flex items-center gap-3"
                   >
                     {scanning ? <Loader2 size={18} className="animate-spin" /> : <Target size={18} />}
                     {scanning ? 'ANALYZING...' : 'RUN AI SCAN'}
                   </button>
                 </div>

                 {scanning && (
                   <div className="mt-10 flex flex-col items-center justify-center py-10 gap-4 animate-fade-in">
                      <div className="relative">
                         <div className="w-16 h-16 border-4 border-indigo-500/20 rounded-full"></div>
                         <div className="w-16 h-16 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin absolute inset-0"></div>
                      </div>
                      <div className="text-center">
                        <p className="text-white font-bold text-lg">AI Pattern Detection in Progress</p>
                        <p className="text-slate-500 text-sm mt-1 max-w-sm">Fetching technical data, rendering dynamic charts, and running YOLOv8 inference model...</p>
                      </div>
                   </div>
                 )}

                 {scanResult && !scanning && (
                   <div className="mt-8 border-t border-white/5 pt-8 animate-fade-in">
                      <div className="flex justify-between items-center mb-10">
                         <div>
                            <span className="text-[10px] font-black tracking-widest text-indigo-400 uppercase">Detection Results / {scanResult.symbol}</span>
                            <h3 className="text-2xl font-black text-white mt-1">AI Technical Verdict</h3>
                         </div>
                         <div className={`px-6 py-2 rounded-full font-black text-sm shadow-xl flex items-center gap-2 ${
                            scanResult.signal === 'BUY' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                            scanResult.signal === 'SELL' ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20' :
                            'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                         }`}>
                           <div className={`w-2 h-2 rounded-full animate-pulse ${
                              scanResult.signal === 'BUY' ? 'bg-emerald-400' :
                              scanResult.signal === 'SELL' ? 'bg-rose-400' : 'bg-amber-400'
                           }`} />
                           {scanResult.signal} SIGNAL ({scanResult.signal_confidence}% CONFIDENCE)
                         </div>
                      </div>

                      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                         {/* Detected Patterns */}
                         <div className="bg-slate-950/40 rounded-2xl p-6 border border-white/5">
                            <h4 className="text-white font-bold mb-6 flex items-center gap-2">
                               <TrendingUp size={16} className="text-indigo-400" />
                               Detected Chart Formations
                            </h4>
                            {scanResult.patterns?.length > 0 ? (
                               <div className="flex flex-col gap-4">
                                  {scanResult.patterns.map((p, i) => (
                                     <div key={i} className="flex flex-col gap-2">
                                        <div className="flex justify-between text-xs font-bold uppercase tracking-wider">
                                           <span className="text-slate-400">{p.name}</span>
                                           <span className="text-white">{p.confidence}% Probability</span>
                                        </div>
                                        <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
                                           <div 
                                              className={`h-full transition-all duration-1000 ${p.confidence > 70 ? 'bg-emerald-500' : 'bg-indigo-500'}`}
                                              style={{ width: `${p.confidence}%` }}
                                           />
                                        </div>
                                     </div>
                                  ))}
                               </div>
                            ) : (
                               <p className="text-slate-600 text-sm italic py-4">No high-probability patterns identified in this timeframe.</p>
                            )}
                         </div>

                         {/* AI Reasoning */}
                         <div className="bg-slate-950/40 rounded-2xl p-6 border border-white/5">
                            <h4 className="text-white font-bold mb-4 flex items-center gap-2">
                               <RefreshCw size={16} className="text-indigo-400" />
                               Model Logic & Rationale
                            </h4>
                            <div className="text-slate-400 text-sm leading-relaxed whitespace-pre-wrap font-medium font-mono bg-black/20 p-4 rounded-xl border border-white/5">
                               {scanResult.reasoning || "Reasoning engine offline for this detection."}
                            </div>
                         </div>
                      </div>

                      <div className="mt-8 flex justify-between items-center text-[10px] font-bold text-slate-600 tracking-widest px-2">
                         <span>ENGINE: YOLOv8-TRADING-V1</span>
                         <span>LAST SCAN: {new Date().toLocaleTimeString()}</span>
                      </div>
                   </div>
                 )}

                 {!scanResult && !scanning && (
                    <div className="py-20 flex flex-col items-center justify-center opacity-40">
                       <div className="p-8 bg-slate-950 border border-white/5 rounded-full mb-6">
                          <Target size={48} className="text-slate-600" />
                       </div>
                       <p className="text-slate-500 font-bold uppercase tracking-widest text-xs">Ready for Scan Deployment</p>
                    </div>
                 )}
               </div>
            </div>
          )}

          {activeTab === 'positions' && (
            <div className="animate-fade-in pb-10">
               <div className="bg-slate-900/60 rounded-3xl border border-white/5 overflow-hidden shadow-2xl">
                  {positions.length > 0 && !positions[0]?.error ? (
                    <table className="w-full text-left">
                       <thead>
                          <tr className="bg-white/5">
                             <th className="px-6 py-5 text-[10px] font-black text-slate-500 uppercase tracking-widest">Symbol</th>
                             <th className="px-6 py-5 text-[10px] font-black text-slate-500 uppercase tracking-widest">Quantity</th>
                             <th className="px-6 py-5 text-[10px] font-black text-slate-500 uppercase tracking-widest">Avg Price</th>
                             <th className="px-6 py-5 text-[10px] font-black text-slate-500 uppercase tracking-widest">Market Value</th>
                             <th className="px-6 py-5 text-[10px] font-black text-slate-500 uppercase tracking-widest">P&L ($)</th>
                             <th className="px-6 py-5 text-[10px] font-black text-slate-500 uppercase tracking-widest">P&L (%)</th>
                          </tr>
                       </thead>
                       <tbody className="divide-y divide-white/5">
                          {positions.map((pos, i) => (
                             <tr key={i} className="hover:bg-white/5 transition-colors group">
                                <td className="px-6 py-6 flex items-center gap-3">
                                   <div className="w-10 h-10 rounded-xl bg-slate-950 flex items-center justify-center border border-white/5 font-black text-white group-hover:border-indigo-500/30 transition-all shadow-sm">
                                      {pos.symbol[0]}
                                   </div>
                                   <div>
                                      <div className="text-white font-black text-sm">{pos.symbol}</div>
                                      <div className="text-slate-500 text-[10px] font-bold">EQUITY</div>
                                   </div>
                                </td>
                                <td className="px-6 py-6 text-sm font-bold text-slate-300">{pos.qty}</td>
                                <td className="px-6 py-6 text-sm font-bold text-slate-300 tabular-nums">${fmt(pos.avg_entry_price)}</td>
                                <td className="px-6 py-6 text-sm font-bold text-white tabular-nums">${Number(pos.market_value).toLocaleString()}</td>
                                <td className={`px-6 py-6 text-sm font-black tabular-nums ${pos.unrealized_pl >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                                   {pos.unrealized_pl >= 0 ? '+' : ''}${fmt(pos.unrealized_pl)}
                                </td>
                                <td className={`px-6 py-6`}>
                                   <div className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-[11px] font-black tabular-nums shadow-sm ${
                                      pos.unrealized_pl_pct >= 0 ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                                   }`}>
                                      {pos.unrealized_pl_pct >= 0 ? <ArrowUpRight size={12} /> : <ArrowDownRight size={12} />}
                                      {(pos.unrealized_pl_pct * 100).toFixed(2)}%
                                   </div>
                                </td>
                             </tr>
                          ))}
                       </tbody>
                    </table>
                  ) : (
                    <EmptyState 
                       icon={<Target size={40} />} 
                       title="No Active Positions" 
                       subtitle={positions[0]?.error || "Use the AI assistant to perform trades and they will appear here."} 
                    />
                  )}
               </div>
            </div>
          )}

          {activeTab === 'orders' && (
            <div className="animate-fade-in pb-10">
               <div className="bg-slate-900/60 rounded-3xl border border-white/5 overflow-hidden shadow-2xl">
                  {orders.length > 0 && !orders[0]?.error ? (
                    <table className="w-full text-left">
                       <thead>
                          <tr className="bg-white/5">
                             <th className="px-6 py-5 text-[10px] font-black text-slate-500 uppercase tracking-widest">Order Details</th>
                             <th className="px-6 py-5 text-[10px] font-black text-slate-500 uppercase tracking-widest">Side</th>
                             <th className="px-6 py-5 text-[10px] font-black text-slate-500 uppercase tracking-widest">Status</th>
                             <th className="px-6 py-5 text-[10px] font-black text-slate-500 uppercase tracking-widest">Quantity</th>
                             <th className="px-6 py-5 text-[10px] font-black text-slate-500 uppercase tracking-widest">Fill Price</th>
                             <th className="px-6 py-5 text-[10px] font-black text-slate-500 uppercase tracking-widest">Execution Time</th>
                          </tr>
                       </thead>
                       <tbody className="divide-y divide-white/5">
                          {orders.map((ord, i) => (
                             <tr key={i} className="hover:bg-white/5 transition-colors">
                                <td className="px-6 py-6">
                                   <div className="text-white font-black text-sm">{ord.symbol}</div>
                                   <div className="text-slate-500 text-[10px] font-bold uppercase tracking-wider">{ord.type} ORDER</div>
                                </td>
                                <td className={`px-6 py-6 text-[11px] font-black`}>
                                   <span className={`px-2 py-1 rounded-md border ${
                                      String(ord.side).includes('buy') ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                                   }`}>
                                      {String(ord.side).toUpperCase()}
                                   </span>
                                </td>
                                <td className="px-6 py-6">
                                   <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-lg text-[10px] font-black uppercase ${
                                      String(ord.status).includes('filled') ? 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20' : 'bg-slate-800 text-slate-400'
                                   }`}>
                                      {ord.status}
                                   </span>
                                </td>
                                <td className="px-6 py-6 text-sm font-bold text-slate-300 tabular-nums">{ord.qty}</td>
                                <td className="px-6 py-6 text-sm font-black text-white tabular-nums">
                                   {ord.filled_avg_price ? `$${fmt(Number(ord.filled_avg_price))}` : '—'}
                                </td>
                                <td className="px-6 py-6 text-[11px] font-medium text-slate-500 flex items-center gap-2">
                                   <Clock size={12} />
                                   {ord.submitted_at ? new Date(ord.submitted_at).toLocaleString() : '—'}
                                </td>
                             </tr>
                          ))}
                       </tbody>
                    </table>
                  ) : (
                    <EmptyState 
                       icon={<History size={40} />} 
                       title="History is Empty" 
                       subtitle="Your recent execution logs will be archived here for tracking and auditing." 
                    />
                  )}
               </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ── Sub-components for Cleaner Renders ── */

function StatCard({ label, value, icon, color, isStatus = false }) {
   const colors = {
      indigo: 'bg-indigo-500',
      emerald: 'bg-emerald-500',
      rose: 'bg-rose-500',
   };

   return (
      <div className="bg-slate-900/60 rounded-2xl p-5 border border-white/5 shadow-lg group hover:border-white/10 transition-all">
         <div className="flex justify-between items-center mb-3">
            <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest">{label}</span>
            <div className={`p-2 rounded-lg opacity-40 group-hover:opacity-100 transition-opacity ${colors[color] + '10'} ${'text-' + color + '-400'}`}>
               {icon}
            </div>
         </div>
         <div className={`text-xl font-black ${isStatus ? 'text-' + color + '-400' : 'text-white'} tracking-tight tabular-nums`}>
            {value}
         </div>
      </div>
   );
}

function TabButton({ active, label, icon, onClick }) {
   return (
      <button 
         onClick={onClick}
         className={`flex items-center gap-2 px-6 py-2.5 rounded-xl text-[10px] font-black tracking-widest transition-all duration-300 ${
            active ? 'bg-indigo-500 text-white shadow-lg shadow-indigo-500/20' : 'text-slate-500 hover:text-white'
         }`}
      >
         {icon}
         {label}
      </button>
   );
}

function EmptyState({ icon, title, subtitle }) {
   return (
      <div className="py-32 flex flex-col items-center justify-center text-center px-10">
         <div className="p-8 bg-slate-950 border border-white/5 rounded-full mb-6 text-slate-700">
            {icon}
         </div>
         <h4 className="text-white font-black text-lg">{title}</h4>
         <p className="text-slate-500 text-sm mt-1 max-w-xs">{subtitle}</p>
      </div>
   );
}

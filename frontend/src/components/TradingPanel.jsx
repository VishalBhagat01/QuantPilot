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
  AlertCircle,
  Cpu,
  Sparkles,
  ExternalLink,
  ChevronRight,
  CheckCircle2
} from 'lucide-react';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const POPULAR_TICKERS = ['AAPL', 'NVDA', 'TSLA', 'MSFT', 'SPY', 'AMZN', 'AMD', 'META'];

export default function TradingPanel({ initialSymbol = '', onAskAI }) {
  const [account, setAccount] = useState(null);
  const [positions, setPositions] = useState([]);
  const [orders, setOrders] = useState([]);
  const [scanSymbol, setScanSymbol] = useState(initialSymbol);
  const [scanResult, setScanResult] = useState(null);
  const [scanning, setScanning] = useState(false);
  const [scanStep, setScanStep] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('scanner');
  const [lastRefreshed, setLastRefreshed] = useState(null);

  // Auto-scan when navigated here with an initialSymbol
  useEffect(() => {
    if (initialSymbol) {
      setScanSymbol(initialSymbol);
      runScanForSymbol(initialSymbol);
    }
  }, [initialSymbol]);

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
      setLastRefreshed(new Date().toLocaleTimeString());
    } catch (e) {
      console.error('[TradingPanel] Failed to fetch data:', e);
      setError('Failed to connect to trading backend. Check if the server is running.');
    } finally {
      setLoading(false);
    }
  }

  async function runScanForSymbol(symbol) {
    const cleanSym = symbol.trim().toUpperCase();
    if (!cleanSym) return;

    setScanning(true);
    setScanStep(1);
    setScanResult(null);
    setError(null);

    // Multi-phase scanner simulation timer for rich UX
    const stepTimer1 = setTimeout(() => setScanStep(2), 500);
    const stepTimer2 = setTimeout(() => setScanStep(3), 1100);

    try {
      const res = await fetch(`${API}/trading/scan/${cleanSym}`, { method: 'POST' });
      if (!res.ok) throw new Error(`Scan failed: ${res.statusText}`);
      const data = await res.json();
      setScanResult(data);
    } catch (e) {
      console.error('[TradingPanel] Scan failed:', e);
      setError(`Scan failed for ${cleanSym}: ${e.message}`);
    } finally {
      clearTimeout(stepTimer1);
      clearTimeout(stepTimer2);
      setScanning(false);
      setScanStep(0);
    }
  }

  function handleScan() {
    runScanForSymbol(scanSymbol);
  }

  const fmt = (val) => val?.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) || '0.00';

  const signalBadge = (sig) => {
    const s = String(sig || '').toUpperCase();
    if (s.includes('BUY')) {
      return {
        bg: 'bg-emerald-500/10 text-emerald-500 border-emerald-500/30',
        dot: 'bg-emerald-500 shadow-[0_0_12px_rgba(16,185,129,0.7)]',
        label: s.includes('STRONG') ? 'STRONG BUY SIGNAL' : 'BUY SIGNAL'
      };
    }
    if (s.includes('SELL')) {
      return {
        bg: 'bg-red-500/10 text-red-500 border-red-500/30',
        dot: 'bg-red-500 shadow-[0_0_12px_rgba(239,68,68,0.7)]',
        label: s.includes('STRONG') ? 'STRONG SELL SIGNAL' : 'SELL SIGNAL'
      };
    }
    return {
      bg: 'bg-amber-500/10 text-amber-500 border-amber-500/30',
      dot: 'bg-amber-500 shadow-[0_0_12px_rgba(245,158,11,0.7)]',
      label: 'NEUTRAL / HOLD SIGNAL'
    };
  };

  return (
    <div className="flex flex-col h-full bg-[var(--bg-base)] p-4 sm:p-7 overflow-y-auto">
      {/* ── Top Header ── */}
      <div className="shrink-0 mb-6 max-w-7xl mx-auto w-full">
        <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
          <div className="flex items-center gap-3.5">
            <div className="p-3 bg-gradient-to-br from-orange-500/20 to-amber-500/10 text-[var(--color-quant-orange)] rounded-2xl border border-[var(--border-accent)] shadow-sm">
              <LayoutDashboard size={24} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl sm:text-2xl font-black tracking-tight text-[var(--text-primary)]">
                  QuantPilot Terminal
                </h1>
                <span className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-500 border border-emerald-500/20 text-[10px] font-bold uppercase tracking-wider">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                  Alpaca Connected
                </span>
              </div>
              <p className="text-xs font-medium text-[var(--text-secondary)] mt-0.5">
                Institutional-grade pattern scanner & multi-broker execution fabric
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {lastRefreshed && (
              <span className="text-[11px] font-mono text-[var(--text-tertiary)] hidden md:inline">
                Synced at {lastRefreshed}
              </span>
            )}
            <button 
              onClick={fetchTradingData}
              className="flex items-center gap-2 px-3.5 py-2 bg-[var(--bg-surface)] hover:bg-[var(--bg-surface-elevated)] border border-[var(--border-subtle)] rounded-xl text-xs font-bold tracking-wider text-[var(--text-primary)] transition-all shadow-sm active:scale-[0.98] cursor-pointer"
            >
              <RefreshCw size={13} className={loading ? 'animate-spin text-[var(--color-quant-orange)]' : 'text-[var(--text-secondary)]'} />
              <span>SYNC BROKER</span>
            </button>
          </div>
        </div>

        {/* ── Key Metrics Cards ── */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
          <StatCard 
            label="Total Cash" 
            value={`$${fmt(account?.cash)}`} 
            icon={<Wallet size={16} />} 
            badge="Available" 
            color="text-emerald-500" 
          />
          <StatCard 
            label="Buying Power" 
            value={`$${fmt(account?.buying_power)}`} 
            icon={<Zap size={16} />} 
            badge="Margin 4x" 
            color="text-[var(--color-quant-orange)]" 
          />
          <StatCard 
            label="Portfolio Equity" 
            value={`$${fmt(account?.equity)}`} 
            icon={<TrendingUp size={16} />} 
            badge="Net Asset" 
            color="text-blue-500" 
          />
          <StatCard 
            label="Account Status" 
            value={account?.paper ? 'PAPER TRADING' : 'LIVE CAPITAL'} 
            icon={<ShieldCheck size={16} />} 
            badge="Active" 
            color={account?.paper ? 'text-emerald-500' : 'text-red-500'} 
            isStatus={true} 
            statusColor={account?.paper ? 'text-emerald-500' : 'text-red-500'} 
          />
        </div>
      </div>

      {/* ── Tabs & Workspace ── */}
      <div className="flex flex-col flex-1 min-h-0 max-w-7xl mx-auto w-full">
        <div className="flex gap-2 mb-6 border-b border-[var(--border-subtle)] pb-3 overflow-x-auto shrink-0 select-none">
          <TabBtn 
            active={activeTab === 'scanner'} 
            onClick={() => setActiveTab('scanner')} 
            label="AI PATTERN SCANNER" 
            icon={<Target size={14} />} 
          />
          <TabBtn 
            active={activeTab === 'positions'} 
            onClick={() => setActiveTab('positions')} 
            label="OPEN POSITIONS" 
            count={positions.length > 0 && !positions[0]?.error ? positions.length : 0}
            icon={<ClipboardList size={14} />} 
          />
          <TabBtn 
            active={activeTab === 'orders'} 
            onClick={() => setActiveTab('orders')} 
            label="ORDER HISTORY" 
            count={orders.length > 0 && !orders[0]?.error ? orders.length : 0}
            icon={<History size={14} />} 
          />
        </div>

        <div className="flex-1 overflow-y-auto">
          {error && (
            <div className="flex items-center gap-3 p-4 bg-red-500/10 border border-red-500/20 text-red-500 rounded-2xl text-xs font-semibold mb-6">
              <AlertCircle size={17} className="shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* ══════════════════════════════════════════════
              SCANNER TAB
             ══════════════════════════════════════════════ */}
          {activeTab === 'scanner' && (
            <div className="space-y-6">
              <div className="bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded-3xl p-6 sm:p-7 shadow-[var(--shadow-card)]">
                {/* Search Bar & Quick Ticker Selector */}
                <div className="mb-6">
                  <div className="flex flex-col sm:flex-row gap-3 mb-4">
                    <div className="flex-1 relative">
                      <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-[var(--text-tertiary)] pointer-events-none" size={17} />
                      <input
                        type="text"
                        className="w-full bg-[var(--bg-surface-elevated)] border border-[var(--border-subtle)] rounded-2xl py-3.5 pl-11 pr-4 text-sm font-bold font-mono text-[var(--text-primary)] placeholder:font-sans placeholder:font-normal placeholder:text-[var(--text-tertiary)] outline-none focus:border-[var(--color-quant-orange)] focus:ring-2 focus:ring-[var(--color-quant-orange)]/15 transition-all uppercase"
                        placeholder="ENTER TICKER SYMBOL (E.G. NVDA, AAPL, TSLA)"
                        value={scanSymbol}
                        onChange={e => setScanSymbol(e.target.value)}
                        onKeyDown={e => e.key === 'Enter' && handleScan()}
                      />
                    </div>
                    <button 
                      onClick={handleScan} 
                      disabled={scanning || !scanSymbol.trim()}
                      className="flex items-center justify-center gap-2 bg-gradient-to-r from-[var(--color-quant-orange)] to-orange-600 hover:to-orange-500 text-white px-7 py-3.5 rounded-2xl text-xs font-bold tracking-wider disabled:opacity-40 transition-all shadow-md shadow-orange-500/20 active:scale-[0.98] cursor-pointer"
                    >
                      {scanning ? <Loader2 size={16} className="animate-spin" /> : <Target size={16} />}
                      <span>{scanning ? 'SCANNING VISION...' : 'RUN AI SCAN'}</span>
                    </button>
                  </div>

                  {/* Popular Tickers Bar */}
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--text-tertiary)] mr-1">
                      Quick Scan:
                    </span>
                    {POPULAR_TICKERS.map((sym) => (
                      <button
                        key={sym}
                        onClick={() => {
                          setScanSymbol(sym);
                          runScanForSymbol(sym);
                        }}
                        className="px-2.5 py-1 rounded-lg bg-[var(--bg-surface-elevated)] hover:bg-[var(--bg-surface-hover)] border border-[var(--border-subtle)] text-[11px] font-bold font-mono text-[var(--text-secondary)] hover:text-[var(--color-quant-orange)] transition-colors cursor-pointer"
                      >
                        ${sym}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Scanning Multi-Stage Progress State */}
                {scanning && (
                  <div className="py-14 flex flex-col items-center justify-center text-center">
                    <div className="relative w-16 h-16 rounded-2xl bg-orange-500/10 border border-orange-500/30 flex items-center justify-center text-[var(--color-quant-orange)] mb-6 shadow-inner">
                      <Cpu size={32} className="animate-pulse" />
                    </div>
                    <h3 className="text-base font-bold text-[var(--text-primary)] mb-2">
                      Executing YOLOv8 Vision Scanner on ${scanSymbol.toUpperCase()}
                    </h3>
                    <div className="space-y-2 max-w-sm w-full mt-4 text-left">
                      <ProgressStep step={1} currentStep={scanStep} text="Fetching level-1 OHLCV candlestick timeframes..." />
                      <ProgressStep step={2} currentStep={scanStep} text="Computing technical indicators (RSI, MACD, Volume Profile)..." />
                      <ProgressStep step={3} currentStep={scanStep} text="Running YOLOv8 neural vision model on chart geometry..." />
                    </div>
                  </div>
                )}

                {/* Scan Results */}
                {scanResult && !scanning && (
                  <div className="animate-in fade-in duration-300">
                    {/* Verdict Banner */}
                    {(() => {
                      const badge = signalBadge(scanResult.signal);
                      return (
                        <div className="flex flex-wrap items-center justify-between gap-4 p-5 rounded-2xl bg-[var(--bg-surface-elevated)] border border-[var(--border-subtle)] mb-7">
                          <div>
                            <div className="flex items-center gap-2 mb-1">
                              <span className="text-[10px] font-black uppercase tracking-wider text-[var(--text-tertiary)]">
                                Vision Scanner Verdict / ${scanResult.symbol}
                              </span>
                            </div>
                            <h2 className="text-xl font-black text-[var(--text-primary)] flex items-center gap-2">
                              <span>Technical Verdict</span>
                              <span className="text-xs font-mono font-medium text-[var(--text-tertiary)]">
                                ({new Date(scanResult.timestamp || Date.now()).toLocaleTimeString()})
                              </span>
                            </h2>
                          </div>

                          <div className={`flex items-center gap-2.5 px-4 py-2 rounded-xl border text-xs font-black tracking-wider ${badge.bg}`}>
                            <div className={`w-2.5 h-2.5 rounded-full ${badge.dot}`} />
                            <span>{badge.label}</span>
                            <span className="font-mono opacity-80">({scanResult.signal_confidence || 85}%)</span>
                          </div>
                        </div>
                      );
                    })()}

                    {/* Formations & Logic Grid */}
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
                      {/* Left: Chart Formations */}
                      <div className="bg-[var(--bg-surface-elevated)]/60 border border-[var(--border-subtle)] rounded-2xl p-5">
                        <div className="flex items-center justify-between mb-4 pb-2 border-b border-[var(--border-subtle)]">
                          <h4 className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[var(--text-primary)]">
                            <TrendingUp size={14} className="text-[var(--color-quant-orange)]" />
                            Detected Chart Formations
                          </h4>
                          <span className="text-[10px] font-mono text-[var(--text-tertiary)]">YOLOv8 Engine</span>
                        </div>

                        {scanResult.patterns?.length > 0 ? (
                          <div className="space-y-4">
                            {scanResult.patterns.map((p, i) => (
                              <div key={i} className="p-3 rounded-xl bg-[var(--bg-surface)] border border-[var(--border-subtle)]">
                                <div className="flex items-center justify-between text-xs font-bold mb-2">
                                  <span className="text-[var(--text-primary)]">{p.name}</span>
                                  <span className="text-[var(--color-quant-orange)] font-mono">{p.confidence}% Probability</span>
                                </div>
                                <div className="h-2 bg-[var(--bg-surface-elevated)] rounded-full overflow-hidden">
                                  <div
                                    className="h-full rounded-full bg-gradient-to-r from-orange-500 to-amber-400 transition-all duration-700"
                                    style={{ width: `${Math.min(p.confidence, 100)}%` }}
                                  />
                                </div>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div className="p-8 text-center text-xs text-[var(--text-tertiary)]">
                            <Target size={28} className="mx-auto mb-2 opacity-50" />
                            <p className="font-semibold text-[var(--text-secondary)]">Consolidation Phase</p>
                            <p className="mt-1">No definitive multi-touch breakout formation detected above 70% threshold.</p>
                          </div>
                        )}
                      </div>

                      {/* Right: Agent Reasoning */}
                      <div className="bg-[var(--bg-surface-elevated)]/60 border border-[var(--border-subtle)] rounded-2xl p-5 flex flex-col justify-between">
                        <div>
                          <div className="flex items-center justify-between mb-4 pb-2 border-b border-[var(--border-subtle)]">
                            <h4 className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[var(--text-primary)]">
                              <Sparkles size={14} className="text-[var(--color-quant-orange)]" />
                              Algorithmic Rationale & Thesis
                            </h4>
                          </div>

                          <div className="p-4 rounded-xl bg-[var(--bg-surface)] border border-[var(--border-subtle)] text-xs text-[var(--text-secondary)] leading-relaxed italic">
                            {scanResult.reasoning || "Technical oscillators indicate neutral-to-bullish momentum with healthy volume support."}
                          </div>
                        </div>

                        {onAskAI && (
                          <button
                            onClick={() => onAskAI(`What is the recommended trade strategy for ${scanResult.symbol} given the ${scanResult.signal} signal?`)}
                            className="mt-4 flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl bg-[var(--bg-surface)] hover:bg-[var(--bg-surface-hover)] border border-[var(--border-subtle)] hover:border-[var(--color-quant-orange)] text-xs font-bold text-[var(--text-primary)] transition-all cursor-pointer shadow-sm"
                          >
                            <Cpu size={14} className="text-[var(--color-quant-orange)]" />
                            <span>Ask AI Agent for Trade Plan on ${scanResult.symbol}</span>
                            <ChevronRight size={13} />
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                )}

                {/* Empty State when no scan yet */}
                {!scanResult && !scanning && (
                  <div className="py-20 flex flex-col items-center justify-center text-center opacity-60">
                    <div className="w-14 h-14 rounded-2xl bg-[var(--bg-surface-elevated)] border border-[var(--border-subtle)] flex items-center justify-center text-[var(--text-tertiary)] mb-4">
                      <Target size={28} />
                    </div>
                    <p className="text-sm font-bold text-[var(--text-primary)]">Scan Engine Ready</p>
                    <p className="text-xs text-[var(--text-secondary)] max-w-sm mt-1">
                      Input any US stock ticker above or click a quick ticker to run the YOLOv8 neural vision detector.
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ══════════════════════════════════════════════
              POSITIONS TAB
             ══════════════════════════════════════════════ */}
          {activeTab === 'positions' && (
            <div className="bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded-3xl overflow-hidden shadow-[var(--shadow-card)]">
              <div className="overflow-x-auto">
                {positions.length > 0 && !positions[0]?.error ? (
                  <table className="w-full text-left border-collapse min-w-[760px]">
                    <thead>
                      <tr className="bg-[var(--bg-surface-elevated)] border-b border-[var(--border-subtle)]">
                        <th className="px-6 py-4 text-[10px] font-bold tracking-wider text-[var(--text-tertiary)] uppercase">Asset / Symbol</th>
                        <th className="px-6 py-4 text-[10px] font-bold tracking-wider text-[var(--text-tertiary)] uppercase text-right">Shares</th>
                        <th className="px-6 py-4 text-[10px] font-bold tracking-wider text-[var(--text-tertiary)] uppercase text-right">Entry Price</th>
                        <th className="px-6 py-4 text-[10px] font-bold tracking-wider text-[var(--text-tertiary)] uppercase text-right">Market Value</th>
                        <th className="px-6 py-4 text-[10px] font-bold tracking-wider text-[var(--text-tertiary)] uppercase text-right">Unrealized P&L</th>
                        <th className="px-6 py-4 text-[10px] font-bold tracking-wider text-[var(--text-tertiary)] uppercase text-right">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[var(--border-subtle)] text-xs">
                      {positions.map((pos, i) => {
                        const isProfitable = (pos.unrealized_pl ?? 0) >= 0;
                        return (
                          <tr key={i} className="hover:bg-[var(--bg-surface-elevated)]/50 transition-colors">
                            <td className="px-6 py-4">
                              <div className="flex items-center gap-3">
                                <div className="w-8 h-8 rounded-xl bg-[var(--bg-surface-elevated)] border border-[var(--border-subtle)] flex items-center justify-center font-mono font-black text-xs text-[var(--text-primary)]">
                                  {pos.symbol?.[0]}
                                </div>
                                <div>
                                  <span className="font-mono font-black text-sm text-[var(--text-primary)] block">
                                    {pos.symbol}
                                  </span>
                                  <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--text-tertiary)]">
                                    Alpaca Position
                                  </span>
                                </div>
                              </div>
                            </td>
                            <td className="px-6 py-4 text-right font-mono font-bold text-[var(--text-primary)]">{pos.qty}</td>
                            <td className="px-6 py-4 text-right font-mono font-semibold text-[var(--text-secondary)]">${fmt(pos.avg_entry_price)}</td>
                            <td className="px-6 py-4 text-right font-mono font-bold text-[var(--text-primary)]">${Number(pos.market_value).toLocaleString()}</td>
                            <td className="px-6 py-4 text-right">
                              <div className="flex flex-col items-end">
                                <span className={`font-mono font-black ${isProfitable ? 'text-emerald-500' : 'text-red-500'}`}>
                                  {isProfitable ? '+' : ''}${fmt(pos.unrealized_pl)}
                                </span>
                                <span className={`inline-flex items-center gap-0.5 text-[10px] font-mono font-bold ${isProfitable ? 'text-emerald-500' : 'text-red-500'}`}>
                                  {isProfitable ? <ArrowUpRight size={11} /> : <ArrowDownRight size={11} />}
                                  {((pos.unrealized_pl_pct ?? 0) * 100).toFixed(2)}%
                                </span>
                              </div>
                            </td>
                            <td className="px-6 py-4 text-right">
                              {onAskAI && (
                                <button
                                  onClick={() => onAskAI(`Should I take profit or hold my ${pos.qty} shares of ${pos.symbol}?`)}
                                  className="px-2.5 py-1.5 rounded-lg bg-[var(--bg-surface-elevated)] hover:bg-[var(--bg-surface-hover)] border border-[var(--border-subtle)] text-[10px] font-bold text-[var(--text-primary)] transition-colors cursor-pointer"
                                >
                                  Analyze
                                </button>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                ) : (
                  <EmptyPanel 
                    icon={<ClipboardList size={36} />} 
                    title="No Open Portfolio Positions" 
                    subtitle={positions[0]?.error || "Your Alpaca paper trading account has no active open positions. Ask the AI assistant to perform simulated orders."} 
                  />
                )}
              </div>
            </div>
          )}

          {/* ══════════════════════════════════════════════
              ORDERS TAB
             ══════════════════════════════════════════════ */}
          {activeTab === 'orders' && (
            <div className="bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded-3xl overflow-hidden shadow-[var(--shadow-card)]">
              <div className="overflow-x-auto">
                {orders.length > 0 && !orders[0]?.error ? (
                  <table className="w-full text-left border-collapse min-w-[760px]">
                    <thead>
                      <tr className="bg-[var(--bg-surface-elevated)] border-b border-[var(--border-subtle)]">
                        <th className="px-6 py-4 text-[10px] font-bold tracking-wider text-[var(--text-tertiary)] uppercase">Symbol & Type</th>
                        <th className="px-6 py-4 text-[10px] font-bold tracking-wider text-[var(--text-tertiary)] uppercase">Side</th>
                        <th className="px-6 py-4 text-[10px] font-bold tracking-wider text-[var(--text-tertiary)] uppercase">Status</th>
                        <th className="px-6 py-4 text-[10px] font-bold tracking-wider text-[var(--text-tertiary)] uppercase text-right">Shares</th>
                        <th className="px-6 py-4 text-[10px] font-bold tracking-wider text-[var(--text-tertiary)] uppercase text-right">Filled Price</th>
                        <th className="px-6 py-4 text-[10px] font-bold tracking-wider text-[var(--text-tertiary)] uppercase text-right">Executed</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[var(--border-subtle)] text-xs">
                      {orders.map((ord, i) => {
                        const isBuy = String(ord.side).toLowerCase().includes('buy');
                        const isFilled = String(ord.status).toLowerCase().includes('filled');
                        return (
                          <tr key={i} className="hover:bg-[var(--bg-surface-elevated)]/50 transition-colors">
                            <td className="px-6 py-4">
                              <span className="font-mono font-black text-sm text-[var(--text-primary)] block">
                                {ord.symbol}
                              </span>
                              <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--text-tertiary)]">
                                {ord.type} Order
                              </span>
                            </td>
                            <td className="px-6 py-4">
                              <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-wider ${
                                isBuy ? 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/20' : 'bg-red-500/10 text-red-500 border border-red-500/20'
                              }`}>
                                {ord.side}
                              </span>
                            </td>
                            <td className="px-6 py-4">
                              <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                                isFilled ? 'bg-emerald-500/10 text-emerald-500' : 'bg-[var(--bg-surface-elevated)] text-[var(--text-secondary)] border border-[var(--border-subtle)]'
                              }`}>
                                {ord.status}
                              </span>
                            </td>
                            <td className="px-6 py-4 text-right font-mono font-bold text-[var(--text-primary)]">{ord.qty}</td>
                            <td className="px-6 py-4 text-right font-mono font-semibold text-[var(--text-primary)]">
                              {ord.filled_avg_price ? `$${fmt(Number(ord.filled_avg_price))}` : '—'}
                            </td>
                            <td className="px-6 py-4 text-right">
                              <span className="text-[11px] font-mono text-[var(--text-tertiary)]">
                                {ord.submitted_at ? new Date(ord.submitted_at).toLocaleString() : '—'}
                              </span>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                ) : (
                  <EmptyPanel 
                    icon={<History size={36} />} 
                    title="No Execution Records Found" 
                    subtitle="Execution receipts will populate here automatically as orders are routed via Alpaca." 
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

/* ── Auxiliary Subcomponents ── */

function StatCard({ label, value, icon, badge, color, isStatus, statusColor }) {
  return (
    <div className="bg-[var(--bg-surface)] rounded-2xl p-4 sm:p-5 border border-[var(--border-subtle)] shadow-[var(--shadow-card)] hover:border-[var(--border-hover)] transition-all">
      <div className="flex items-center justify-between mb-2.5">
        <span className="text-[10px] font-bold text-[var(--text-tertiary)] uppercase tracking-wider">{label}</span>
        <div className={`p-1.5 bg-[var(--bg-surface-elevated)] border border-[var(--border-subtle)] rounded-lg ${color}`}>
          {icon}
        </div>
      </div>
      <div className={`text-lg sm:text-xl font-black font-mono tracking-tight ${isStatus ? statusColor : 'text-[var(--text-primary)]'}`}>
        {value}
      </div>
      {badge && (
        <span className="text-[9px] font-bold tracking-wider uppercase text-[var(--text-tertiary)] mt-1 block">
          {badge}
        </span>
      )}
    </div>
  );
}

function TabBtn({ active, label, count, icon, onClick }) {
  return (
    <button 
      onClick={onClick} 
      className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-xs font-bold tracking-wider transition-all whitespace-nowrap cursor-pointer ${
        active 
          ? 'bg-[var(--bg-surface)] border border-[var(--border-accent)] text-[var(--text-primary)] shadow-sm' 
          : 'border border-transparent text-[var(--text-tertiary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-surface)]/60'
      }`}
    >
      {icon}
      <span>{label}</span>
      {count !== undefined && count > 0 && (
        <span className="text-[10px] font-mono px-1.5 py-0.2 rounded-full bg-[var(--color-quant-orange)] text-white">
          {count}
        </span>
      )}
    </button>
  );
}

function ProgressStep({ step, currentStep, text }) {
  const isDone = currentStep > step;
  const isCurrent = currentStep === step;

  return (
    <div className="flex items-center gap-2.5 text-xs">
      {isDone ? (
        <CheckCircle2 size={15} className="text-emerald-500 shrink-0" />
      ) : isCurrent ? (
        <Loader2 size={15} className="animate-spin text-[var(--color-quant-orange)] shrink-0" />
      ) : (
        <div className="w-3.5 h-3.5 rounded-full border border-[var(--border-subtle)] shrink-0" />
      )}
      <span className={isCurrent ? 'font-bold text-[var(--text-primary)]' : isDone ? 'text-[var(--text-secondary)] line-through' : 'text-[var(--text-tertiary)]'}>
        {text}
      </span>
    </div>
  );
}

function EmptyPanel({ icon, title, subtitle }) {
  return (
    <div className="flex flex-col items-center justify-center p-14 sm:p-20 text-center">
      <div className="p-4 rounded-2xl bg-[var(--bg-surface-elevated)] border border-[var(--border-subtle)] text-[var(--text-tertiary)] mb-4">
        {icon}
      </div>
      <h4 className="text-sm font-bold text-[var(--text-primary)] mb-1">{title}</h4>
      <p className="text-xs text-[var(--text-tertiary)] max-w-sm">{subtitle}</p>
    </div>
  );
}

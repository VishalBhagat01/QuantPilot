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
import './TradingPanel.css';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function TradingPanel() {

  const [account, setAccount]     = useState(null);
  const [positions, setPositions] = useState([]);
  const [orders, setOrders]       = useState([]);
  const [scanSymbol, setScanSymbol] = useState('');
  const [scanResult, setScanResult] = useState(null);
  const [scanning, setScanning]   = useState(false);
  const [loading, setLoading]     = useState(true);
  const [error, setError]         = useState(null);
  const [activeTab, setActiveTab] = useState('scanner');

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
      const res = await fetch(`${API}/trading/scan/${scanSymbol.toUpperCase()}`, { method: 'POST' });
      if (!res.ok) throw new Error(`Scan failed: ${res.statusText}`);
      setScanResult(await res.json());
    } catch (e) {
      console.error('[TradingPanel] Scan failed:', e);
      setError(`Scan failed for ${scanSymbol}: ${e.message}`);
    } finally {
      setScanning(false);
    }
  }

  const fmt = (val) => val?.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) || '0.00';

  const signalClass = (sig) => sig === 'BUY' ? 'buy' : sig === 'SELL' ? 'sell' : 'hold';

  return (
    <div className="trading-panel">

      {/* ── Header ── */}
      <div className="tp-header">
        <div className="tp-header-top">
          <div>
            <h1 className="tp-title">
              <div className="tp-title-icon">
                <LayoutDashboard size={22} />
              </div>
              QuantPilot <span className="tp-title-accent">TERMINAL</span>
            </h1>
            <p className="tp-subtitle">Real-time pattern detection & Alpaca execution system</p>
          </div>
          <button className="tp-refresh-btn" onClick={fetchTradingData}>
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            REFRESH
          </button>
        </div>

        {/* ── Stats ── */}
        <div className="tp-stats-grid">
          <StatCard label="Total Cash" value={`$${fmt(account?.cash)}`} icon={<Wallet size={15} />} color="green" />
          <StatCard label="Buying Power" value={`$${fmt(account?.buying_power)}`} icon={<Zap size={15} />} color="gold" />
          <StatCard label="Current Equity" value={`$${fmt(account?.equity)}`} icon={<TrendingUp size={15} />} color="emerald" />
          <StatCard label="Account Mode" value={account?.paper ? 'PAPER TRADING' : 'LIVE TRADING'} icon={<ShieldCheck size={15} />} color={account?.paper ? 'emerald' : 'rose'} isStatus />
        </div>
      </div>

      {/* ── Tabs & Content ── */}
      <div className="tp-content">
        <div className="tp-tabs">
          <TabBtn active={activeTab === 'scanner'} onClick={() => setActiveTab('scanner')} label="PATTERN SCANNER" icon={<Search size={13} />} />
          <TabBtn active={activeTab === 'positions'} onClick={() => setActiveTab('positions')} label="POSITIONS" icon={<ClipboardList size={13} />} />
          <TabBtn active={activeTab === 'orders'} onClick={() => setActiveTab('orders')} label="ORDER HISTORY" icon={<History size={13} />} />
        </div>

        <div className="tp-panel">
          {error && (
            <div className="tp-error">
              <AlertCircle size={16} />
              {error}
            </div>
          )}

          {/* ── Scanner Tab ── */}
          {activeTab === 'scanner' && (
            <div className="animate-fade-in">
              <div className="tp-scanner-card">
                <div className="tp-scanner-row">
                  <div className="tp-scanner-input-wrap">
                    <Search className="tp-scanner-input-icon" size={16} />
                    <input
                      type="text"
                      className="tp-scanner-input"
                      placeholder="Enter Ticker Symbol (e.g. AAPL, TSLA, BTC/USD)"
                      value={scanSymbol}
                      onChange={e => setScanSymbol(e.target.value)}
                      onKeyDown={e => e.key === 'Enter' && handleScan()}
                    />
                  </div>
                  <button className="tp-scan-btn" onClick={handleScan} disabled={scanning || !scanSymbol.trim()}>
                    {scanning ? <Loader2 size={16} className="animate-spin" /> : <Target size={16} />}
                    {scanning ? 'ANALYZING...' : 'RUN AI SCAN'}
                  </button>
                </div>

                {scanning && (
                  <div className="tp-scan-loading">
                    <div className="tp-spinner-ring">
                      <div className="tp-spinner-ring-bg" />
                      <div className="tp-spinner-ring-active" />
                    </div>
                    <p className="tp-scan-loading-title">AI Pattern Detection in Progress</p>
                    <p className="tp-scan-loading-sub">Fetching technical data, rendering dynamic charts, and running YOLOv8 inference model...</p>
                  </div>
                )}

                {scanResult && !scanning && (
                  <div className="tp-results">
                    <div className="tp-results-header">
                      <div className="tp-results-meta">
                        <span className="tp-results-label">Detection Results / {scanResult.symbol}</span>
                        <h3 className="tp-results-title">AI Technical Verdict</h3>
                      </div>
                      <div className={`tp-signal-badge ${signalClass(scanResult.signal)}`}>
                        <div className={`tp-signal-dot ${signalClass(scanResult.signal)}`} />
                        {scanResult.signal} SIGNAL ({scanResult.signal_confidence}% CONFIDENCE)
                      </div>
                    </div>

                    <div className="tp-results-grid">
                      <div className="tp-result-section">
                        <h4 className="tp-result-section-title">
                          <TrendingUp size={15} />
                          Detected Chart Formations
                        </h4>
                        {scanResult.patterns?.length > 0 ? (
                          <div className="tp-pattern-list">
                            {scanResult.patterns.map((p, i) => (
                              <div key={i} className="tp-pattern-item">
                                <div className="tp-pattern-meta">
                                  <span className="tp-pattern-name">{p.name}</span>
                                  <span className="tp-pattern-conf">{p.confidence}% Probability</span>
                                </div>
                                <div className="tp-pattern-bar-track">
                                  <div
                                    className={`tp-pattern-bar-fill ${p.confidence > 70 ? 'high' : 'low'}`}
                                    style={{ width: `${p.confidence}%` }}
                                  />
                                </div>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <p className="tp-no-patterns">No high-probability patterns identified in this timeframe.</p>
                        )}
                      </div>

                      <div className="tp-result-section">
                        <h4 className="tp-result-section-title">
                          <RefreshCw size={15} />
                          Model Logic & Rationale
                        </h4>
                        <div className="tp-reasoning-box">
                          {scanResult.reasoning || "Reasoning engine offline for this detection."}
                        </div>
                      </div>
                    </div>

                    <div className="tp-engine-footer">
                      <span>ENGINE: YOLOv8-TRADING-V1</span>
                      <span>LAST SCAN: {new Date().toLocaleTimeString()}</span>
                    </div>
                  </div>
                )}

                {!scanResult && !scanning && (
                  <div className="tp-scanner-idle">
                    <div className="tp-idle-icon">
                      <Target size={40} />
                    </div>
                    <p className="tp-idle-text">Ready for Scan Deployment</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ── Positions Tab ── */}
          {activeTab === 'positions' && (
            <div className="animate-fade-in">
              <div className="tp-table-wrap">
                {positions.length > 0 && !positions[0]?.error ? (
                  <table className="tp-table">
                    <thead>
                      <tr>
                        <th>Symbol</th>
                        <th>Quantity</th>
                        <th>Avg Price</th>
                        <th>Market Value</th>
                        <th>P&L ($)</th>
                        <th>P&L (%)</th>
                      </tr>
                    </thead>
                    <tbody>
                      {positions.map((pos, i) => (
                        <tr key={i}>
                          <td>
                            <div className="tp-pos-symbol-cell">
                              <div className="tp-pos-avatar">{pos.symbol[0]}</div>
                              <div>
                                <div className="tp-pos-symbol">{pos.symbol}</div>
                                <div className="tp-pos-type">EQUITY</div>
                              </div>
                            </div>
                          </td>
                          <td className="tp-text-bold tp-text-tabular">{pos.qty}</td>
                          <td className="tp-text-bold tp-text-tabular">${fmt(pos.avg_entry_price)}</td>
                          <td className="tp-text-white tp-text-tabular">${Number(pos.market_value).toLocaleString()}</td>
                          <td className={`tp-text-tabular ${pos.unrealized_pl >= 0 ? 'tp-profit' : 'tp-loss'}`}>
                            {pos.unrealized_pl >= 0 ? '+' : ''}${fmt(pos.unrealized_pl)}
                          </td>
                          <td>
                            <span className={`tp-pnl-badge ${pos.unrealized_pl_pct >= 0 ? 'positive' : 'negative'}`}>
                              {pos.unrealized_pl_pct >= 0 ? <ArrowUpRight size={11} /> : <ArrowDownRight size={11} />}
                              {(pos.unrealized_pl_pct * 100).toFixed(2)}%
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <EmptyState icon={<Target size={36} />} title="No Active Positions" subtitle={positions[0]?.error || "Use the AI assistant to perform trades and they will appear here."} />
                )}
              </div>
            </div>
          )}

          {/* ── Orders Tab ── */}
          {activeTab === 'orders' && (
            <div className="animate-fade-in">
              <div className="tp-table-wrap">
                {orders.length > 0 && !orders[0]?.error ? (
                  <table className="tp-table">
                    <thead>
                      <tr>
                        <th>Order Details</th>
                        <th>Side</th>
                        <th>Status</th>
                        <th>Quantity</th>
                        <th>Fill Price</th>
                        <th>Execution Time</th>
                      </tr>
                    </thead>
                    <tbody>
                      {orders.map((ord, i) => (
                        <tr key={i}>
                          <td>
                            <div className="tp-pos-symbol">{ord.symbol}</div>
                            <div className="tp-pos-type">{ord.type} ORDER</div>
                          </td>
                          <td>
                            <span className={`tp-side-badge ${String(ord.side).includes('buy') ? 'buy' : 'sell'}`}>
                              {String(ord.side).toUpperCase()}
                            </span>
                          </td>
                          <td>
                            <span className={`tp-status-badge ${String(ord.status).includes('filled') ? 'filled' : 'other'}`}>
                              {ord.status}
                            </span>
                          </td>
                          <td className="tp-text-bold tp-text-tabular">{ord.qty}</td>
                          <td className="tp-text-white tp-text-tabular">
                            {ord.filled_avg_price ? `$${fmt(Number(ord.filled_avg_price))}` : '—'}
                          </td>
                          <td>
                            <div className="tp-time-cell">
                              <Clock size={12} />
                              {ord.submitted_at ? new Date(ord.submitted_at).toLocaleString() : '—'}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <EmptyState icon={<History size={36} />} title="History is Empty" subtitle="Your recent execution logs will be archived here for tracking and auditing." />
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ── Sub-components ── */

function StatCard({ label, value, icon, color, isStatus = false }) {
  return (
    <div className="tp-stat-card">
      <div className="tp-stat-header">
        <span className="tp-stat-label">{label}</span>
        <div className={`tp-stat-icon ${color}`}>{icon}</div>
      </div>
      <div className={`tp-stat-value ${isStatus ? `status-${color}` : ''}`}>{value}</div>
    </div>
  );
}

function TabBtn({ active, label, icon, onClick }) {
  return (
    <button onClick={onClick} className={`tp-tab-btn ${active ? 'active' : ''}`}>
      {icon}
      {label}
    </button>
  );
}

function EmptyState({ icon, title, subtitle }) {
  return (
    <div className="tp-empty-state">
      <div className="tp-empty-icon">{icon}</div>
      <h4 className="tp-empty-title">{title}</h4>
      <p className="tp-empty-sub">{subtitle}</p>
    </div>
  );
}

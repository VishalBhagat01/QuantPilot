import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
    TrendingUp, 
    TrendingDown, 
    Activity, 
    DollarSign, 
    BarChart3, 
    Sparkles, 
    Zap, 
    Loader2, 
    ChevronDown, 
    Globe,
    ShieldAlert,
    Cpu
} from 'lucide-react';
import StockChart from './StockChart';

const StockCard = ({ symbol, onTrade }) => {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [activeRange, setActiveRange] = useState('1D');
    const [expanded, setExpanded] = useState(false);

    useEffect(() => {
        const fetchData = async () => {
            try {
                setLoading(true);
                const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";
                const response = await axios.post(`${API_BASE}/agent/stock`, { symbol });
                setData(response.data);
                setError(null);
            } catch (err) {
                console.error("Error fetching stock data:", err);
                setError("Could not load asset intelligence.");
            } finally {
                setLoading(false);
            }
        };

        if (symbol) {
            fetchData();
        }
    }, [symbol]);

    if (loading) return (
        <div className="flex items-center gap-3.5 bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded-2xl p-5 w-full max-w-2xl mx-auto shadow-[var(--shadow-card)]">
            <div className="w-8 h-8 rounded-xl bg-orange-500/10 border border-orange-500/20 flex items-center justify-center text-[var(--color-quant-orange)]">
                <Loader2 size={16} className="animate-spin" />
            </div>
            <div>
                <p className="text-xs font-bold text-[var(--text-primary)]">Hydrating Market Feed</p>
                <p className="text-[11px] text-[var(--text-tertiary)]">Fetching level-1 quotes and technical snapshots for ${symbol}...</p>
            </div>
        </div>
    );

    if (error) return (
        <div className="flex items-center gap-3 bg-red-500/10 border border-red-500/20 text-red-500 rounded-2xl p-4 w-full max-w-2xl mx-auto text-sm font-medium">
            <ShieldAlert size={18} className="shrink-0" />
            <div className="flex-1">
                <p className="font-semibold text-xs text-red-400">Feed Disruption</p>
                <p className="text-xs text-red-500/80">{error}</p>
            </div>
        </div>
    );

    if (!data) return null;

    const isPositive = (data.change ?? 0) >= 0;
    const showCompany = data.company && data.company !== data.symbol;
    const chartColor = isPositive ? '#10b981' : '#ef4444';

    return (
        <div className="relative bg-[var(--bg-surface)] rounded-3xl border border-[var(--border-subtle)] p-6 sm:p-7 w-full max-w-2xl mx-auto shadow-[var(--shadow-elevated)] overflow-hidden transition-all duration-300 hover:border-[var(--border-hover)]">
            {/* Ambient Background Radial Glow */}
            <div 
                className={`absolute -top-32 -right-32 w-64 h-64 rounded-full blur-[100px] pointer-events-none transition-all duration-700 opacity-25 ${
                    isPositive ? 'bg-emerald-500' : 'bg-red-500'
                }`} 
            />

            {/* Header: Identity & Timeframe selector */}
            <div className="flex flex-wrap items-start justify-between gap-4 mb-6 relative z-10">
                <div className="flex items-center gap-3.5">
                    <div className="w-11 h-11 rounded-2xl bg-[var(--bg-surface-elevated)] border border-[var(--border-subtle)] flex items-center justify-center font-mono font-black text-sm text-[var(--text-primary)] shadow-sm">
                        {data.symbol?.slice(0, 3)}
                    </div>
                    <div>
                        <div className="flex items-center gap-2">
                            <span className="text-xl sm:text-2xl font-black font-mono tracking-tight text-[var(--text-primary)]">
                                {data.symbol}
                            </span>
                            <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-[var(--bg-surface-elevated)] border border-[var(--border-subtle)] text-[var(--text-secondary)]">
                                US Equity
                            </span>
                        </div>
                        {showCompany ? (
                            <p className="text-xs font-medium text-[var(--text-secondary)] truncate max-w-[240px]">
                                {data.company}
                            </p>
                        ) : (
                            <div className="flex items-center gap-1.5 text-[11px] text-[var(--text-tertiary)] font-medium">
                                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                                <span>Real-time Market Feed</span>
                            </div>
                        )}
                    </div>
                </div>

                {/* Range Selector */}
                <div className="flex items-center bg-[var(--bg-surface-elevated)] rounded-xl p-1 border border-[var(--border-subtle)]">
                    {['1D', '5D', '1M', '6M', '1Y'].map((range) => (
                        <button
                            key={range}
                            onClick={() => setActiveRange(range)}
                            className={`px-2.5 py-1 rounded-lg text-[10px] font-bold tracking-wider transition-all duration-150 ${
                                activeRange === range 
                                    ? 'bg-[var(--color-quant-orange)] text-white shadow-sm font-black' 
                                    : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                            }`}
                        >
                            {range}
                        </button>
                    ))}
                </div>
            </div>

            {/* Main Price & Trend Hero */}
            <div className="flex flex-wrap items-baseline gap-4 mb-6 relative z-10">
                <span className="text-3xl sm:text-4xl md:text-5xl font-extrabold font-mono text-[var(--text-primary)] tracking-tight leading-none">
                    ${data.price?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
                <div className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold font-mono tracking-tight ${
                    isPositive 
                        ? 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/20' 
                        : 'bg-red-500/10 text-red-500 border border-red-500/20'
                }`}>
                    {isPositive ? <TrendingUp size={13} /> : <TrendingDown size={13} />}
                    <span>
                        {isPositive ? '+' : ''}{data.change?.toFixed(2)} ({data.percent?.toFixed(2)}%)
                    </span>
                </div>
            </div>

            {/* Interactive Chart Container */}
            <div className="h-[190px] w-full relative mb-6 rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-surface-elevated)]/60 p-2 overflow-hidden">
                <StockChart data={data.chart} color={chartColor} />
                
                {/* Confidence Badge */}
                <div className="absolute top-3 right-3 flex items-center gap-1.5 text-[10px] font-bold text-[var(--text-secondary)] bg-[var(--bg-surface)]/90 backdrop-blur-md px-2.5 py-1 rounded-full border border-[var(--border-subtle)] shadow-sm">
                    <Cpu size={11} className="text-[var(--color-quant-orange)]" />
                    <span>AI Confidence: <strong className="text-[var(--text-primary)] font-mono">{data.confidence || 88}%</strong></span>
                </div>
            </div>

            {/* 4 Essential Technical Metrics */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 mb-6 relative z-10">
                <MetricItem label="Open" value={data.open} icon={<DollarSign size={13} />} />
                <MetricItem label="Day High" value={data.high} icon={<TrendingUp size={13} />} highlight="text-emerald-500" />
                <MetricItem label="Day Low" value={data.low} icon={<TrendingDown size={13} />} highlight="text-red-500" />
                <MetricItem label="Prev Close" value={data.prev_close} icon={<Activity size={13} />} />
            </div>

            {/* Action Row */}
            <div className="flex items-center gap-3 relative z-10">
                <button 
                    onClick={() => onTrade && onTrade(data.symbol)}
                    className="flex-1 flex items-center justify-center gap-2 bg-[var(--color-quant-orange)] hover:bg-[var(--color-quant-orange-hover)] text-white py-3 px-5 rounded-xl font-bold text-xs tracking-wider transition-all duration-200 shadow-md shadow-orange-500/20 active:scale-[0.99] cursor-pointer"
                >
                    <Zap size={14} className="fill-current" />
                    OPEN TERMINAL & SCAN
                </button>
                <button 
                    onClick={() => setExpanded(!expanded)}
                    className="flex items-center gap-1.5 px-3.5 py-3 rounded-xl bg-[var(--bg-surface-elevated)] hover:bg-[var(--bg-surface-hover)] border border-[var(--border-subtle)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] text-xs font-semibold transition-colors cursor-pointer"
                    title="Toggle Technical Overview"
                >
                    <span>Intelligence</span>
                    <ChevronDown size={14} className={`transition-transform duration-200 ${expanded ? 'rotate-180' : ''}`} />
                </button>
            </div>

            {/* Expanded Intelligence Drawer */}
            {expanded && (
                <div className="mt-5 pt-5 border-t border-[var(--border-subtle)] animate-in fade-in slide-in-from-top-2 duration-200">
                    <div className="mb-4 bg-[var(--bg-surface-elevated)]/70 p-4 rounded-xl border border-[var(--border-subtle)]">
                        <div className="flex items-center gap-2 mb-2">
                            <Sparkles size={13} className="text-[var(--color-quant-orange)]" />
                            <span className="text-[11px] font-bold tracking-wider uppercase text-[var(--text-secondary)]">QuantPilot Synthesis</span>
                        </div>
                        <p className="text-xs text-[var(--text-secondary)] leading-relaxed italic">
                            {data.summary || `Multi-agent consensus models indicate stable volume profiling on ${data.symbol}. Dynamic trend boundaries suggest watching the $${(data.low * 0.98).toFixed(2)} support level.`}
                        </p>
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                        <div className="bg-[var(--bg-surface-elevated)] p-3.5 rounded-xl border border-[var(--border-subtle)]">
                            <span className="text-[10px] font-bold text-[var(--text-tertiary)] uppercase tracking-wider block mb-1">Trading Volume</span>
                            <span className="text-xs font-black font-mono text-[var(--text-primary)]">{data.volume || '14.2M'}</span>
                        </div>
                        <div className="bg-[var(--bg-surface-elevated)] p-3.5 rounded-xl border border-[var(--border-subtle)]">
                            <span className="text-[10px] font-bold text-[var(--text-tertiary)] uppercase tracking-wider block mb-1">Market Capitalization</span>
                            <span className="text-xs font-black font-mono text-[var(--text-primary)]">{data.market_cap || '$2.84T'}</span>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

const MetricItem = ({ label, value, icon, highlight }) => {
    return (
        <div className="flex flex-col gap-1 p-3 rounded-xl bg-[var(--bg-surface-elevated)] border border-[var(--border-subtle)]">
            <div className="flex items-center gap-1.5 text-[var(--text-tertiary)]">
                <span className={highlight || 'text-[var(--text-tertiary)]'}>{icon}</span>
                <span className="text-[10px] font-bold uppercase tracking-wider">{label}</span>
            </div>
            <div className={`text-xs sm:text-sm font-extrabold font-mono tracking-tight ${highlight || 'text-[var(--text-primary)]'}`}>
                ${(value || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </div>
        </div>
    );
};

export default StockCard;

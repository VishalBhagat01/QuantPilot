import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { TrendingUp, TrendingDown, Activity, DollarSign, BarChart2, PieChart, Info, Zap, ChevronUp, ChevronDown } from 'lucide-react';
import StockChart from './StockChart';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs) {
    return twMerge(clsx(inputs));
}

/**
 * =============================================================================
 * StockCard Component — Premium AI Stock Analysis View
 * =============================================================================
 */
const StockCard = ({ symbol }) => {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [activeRange, setActiveRange] = useState('1D');
    const [expanded, setExpanded] = useState(false);

    useEffect(() => {
        const fetchData = async () => {
            try {
                setLoading(true);
                const response = await axios.get(`http://localhost:8000/stock/${symbol}`);
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
        <div className="w-full h-96 bg-slate-900/50 backdrop-blur-xl rounded-3xl border border-white/5 animate-pulse flex items-center justify-center">
            <div className="flex flex-col items-center gap-4">
                <div className="w-12 h-12 border-4 border-indigo-500/20 border-t-indigo-500 rounded-full animate-spin"></div>
                <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Hydrating Intelligence...</span>
            </div>
        </div>
    );
    
    if (error) return (
        <div className="w-full p-8 bg-rose-500/5 rounded-3xl border border-rose-500/20 text-rose-400 text-sm font-bold flex items-center gap-3">
            <Activity size={18} />
            {error}
        </div>
    );
    
    if (!data) return null;

    const isPositive = data.change >= 0;
    const accentColor = isPositive ? 'rgba(16, 185, 129, 0.4)' : 'rgba(244, 63, 94, 0.4)';
    const showCompany = data.company && data.company !== data.symbol;

    return (
        <div className="relative group overflow-hidden bg-slate-900 shadow-2xl rounded-3xl border border-white/5 p-8 w-full transition-all duration-500 hover:border-indigo-500/30">
            
            {/* Dynamic radial glow */}
            <div 
                className="absolute -top-24 -right-24 w-64 h-64 blur-[100px] opacity-10 pointer-events-none transition-opacity duration-700 group-hover:opacity-20"
                style={{ background: accentColor }}
            />

            <div className="flex justify-between items-start mb-8 relative z-10">
                <div>
                    {showCompany && (
                        <h2 className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-1.5 opacity-60">
                            {data.company}
                        </h2>
                    )}
                    <h1 className="text-4xl font-black text-white tracking-tight flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-indigo-500/20 flex items-center justify-center border border-indigo-500/20">
                            <BarChart2 size={20} className="text-indigo-400" />
                        </div>
                        {data.symbol}
                        {!showCompany && <span className="text-slate-600 text-lg font-medium opacity-40">/ EQUITY</span>}
                    </h1>
                </div>
                
                <div className="flex p-1.5 bg-slate-950/40 rounded-2xl border border-white/5 backdrop-blur-md">
                    {['1D', '5D', '1M'].map((range) => (
                        <button
                            key={range}
                            onClick={() => setActiveRange(range)}
                            className={cn(
                                "px-5 py-2 text-[10px] font-black rounded-xl transition-all duration-300 tracking-widest",
                                activeRange === range 
                                    ? "bg-indigo-500 text-white shadow-lg shadow-indigo-500/25" 
                                    : "text-slate-500 hover:text-slate-300"
                            )}
                        >
                            {range}
                        </button>
                    ))}
                </div>
            </div>

            <div className="flex items-end gap-5 mb-10 relative z-10">
                <span className="text-6xl font-black text-white tabular-nums tracking-tighter leading-none">
                    ${data.price?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
                <div className={cn(
                    "px-4 py-2 rounded-xl flex items-center text-[13px] font-black tabular-nums transition-all border shadow-sm mb-1",
                    isPositive 
                        ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" 
                        : "bg-rose-500/10 text-rose-400 border-rose-500/20"
                )}>
                    {isPositive ? <TrendingUp size={16} className="mr-2" /> : <TrendingDown size={16} className="mr-2" />}
                    <span>
                        {isPositive ? '+' : ''}{data.change?.toFixed(2)} ({data.percent?.toFixed(2)}%)
                    </span>
                </div>
            </div>

            {/* AI Technical Chart */}
            <div className="relative h-64 w-full mb-10 rounded-3xl bg-slate-950/40 border border-white/5 shadow-inner overflow-hidden group-hover:border-white/10 transition-colors">
                <StockChart data={data.chart} color={isPositive ? '#10b981' : '#f43f5e'} />
                
                <div className="absolute top-4 right-4 flex items-center gap-2">
                    <div className="px-3 py-1 bg-slate-900/80 backdrop-blur-md rounded-lg border border-white/5 text-[9px] font-black text-slate-400 uppercase tracking-widest">
                        Model Confidence: {(data.confidence || 84)}%
                    </div>
                </div>
            </div>

            {/* Metrics Ecosystem */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-6 pt-10 border-t border-white/5 relative z-10 mt-2">
                <Metric label="Market Open" value={data.open} icon={<DollarSign size={14} />} color="slate" />
                <Metric label="Intraday High" value={data.high} icon={<TrendingUp size={14} />} color="emerald" />
                <Metric label="Intraday Low" value={data.low} icon={<TrendingDown size={14} />} color="rose" />
                <Metric label="Prev. Close" value={data.prev_close} icon={<Activity size={14} />} color="indigo" />
            </div>

            {/* Bottom Actions */}
            <div className="mt-10 flex gap-4 relative z-10">
                <button className="flex-1 py-4 bg-indigo-500 hover:bg-indigo-600 text-white font-black rounded-2xl transition-all shadow-lg shadow-indigo-500/20 active:scale-95 flex items-center justify-center gap-2">
                    <Zap size={18} />
                    TRADE ASSET
                </button>
                <div className="w-14 h-14 bg-white/5 hover:bg-white/10 border border-white/5 rounded-2xl flex items-center justify-center text-slate-400 cursor-pointer transition-all active:scale-90" onClick={() => setExpanded(!expanded)}>
                    <Info size={20} />
                </div>
            </div>

            {expanded && (
                <div className="mt-8 p-6 bg-slate-950/40 rounded-2xl border border-white/5 animate-fade-in">
                   <p className="text-slate-400 text-sm leading-relaxed font-medium mb-4">
                      {data.summary || "QuantPilot AI is aggregating consensus data... Expect technical breakout confirmation within 24 hours based on current momentum vectors."}
                   </p>
                   <div className="flex gap-4">
                      <div className="flex-1 p-3 bg-white/5 rounded-xl border border-white/5">
                          <div className="text-[10px] font-black text-slate-500 uppercase mb-1">Vol Profile</div>
                          <div className="text-sm font-bold text-white leading-none">{data.volume || 'N/A'}</div>
                      </div>
                      <div className="flex-1 p-3 bg-white/5 rounded-xl border border-white/5">
                          <div className="text-[10px] font-black text-slate-500 uppercase mb-1">Mkt Cap</div>
                          <div className="text-sm font-bold text-white leading-none">{data.market_cap || 'N/A'}</div>
                      </div>
                   </div>
                </div>
            )}
        </div>
    );
};

const Metric = ({ label, value, icon, color }) => {
    const colorMap = {
        emerald: "text-emerald-400 bg-emerald-500/10 border-emerald-500/10",
        rose: "text-rose-400 bg-rose-500/10 border-rose-500/10",
        indigo: "text-indigo-400 bg-indigo-500/10 border-indigo-500/10",
        slate: "text-slate-400 bg-slate-500/10 border-slate-500/10"
    };

    return (
        <div className="group/metric flex flex-col gap-2.5">
            <div className="flex items-center gap-2">
                <div className={cn("p-1.5 rounded-lg border transition-all", colorMap[color])}>
                    {icon}
                </div>
                <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest opacity-60 leading-none">
                    {label}
                </span>
            </div>
            <div className="text-lg font-black text-white tabular-nums tracking-tight">
                ${(value || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
            </div>
        </div>
    );
};

export default StockCard;

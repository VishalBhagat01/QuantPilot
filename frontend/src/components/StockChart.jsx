import React from 'react';
import {
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    Area,
    AreaChart
} from 'recharts';
import { AreaChart as ChartIcon } from 'lucide-react';

const StockChart = ({ data, color = '#ff6600' }) => {
    if (!data || data.length === 0) {
        return (
            <div className="flex flex-col items-center justify-center h-full w-full opacity-60">
                <div className="p-3 rounded-2xl bg-[var(--bg-surface-elevated)] border border-[var(--border-subtle)] text-[var(--text-tertiary)] mb-3">
                    <ChartIcon size={24} />
                </div>
                <div className="text-center">
                    <p className="text-xs font-semibold tracking-wide text-[var(--text-primary)]">Live Chart Synchronizing</p>
                    <p className="text-[11px] text-[var(--text-tertiary)] mt-0.5">Historical markers loading from broker feed...</p>
                </div>
            </div>
        );
    }

    const minPrice = Math.min(...data.map(d => d.price || 0));
    const maxPrice = Math.max(...data.map(d => d.price || 0));
    const padding = (maxPrice - minPrice) * 0.1 || 1;

    return (
        <div className="w-full h-full relative select-none">
            <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={data} margin={{ top: 8, right: 6, left: 6, bottom: 0 }}>
                    <defs>
                        <linearGradient id={`chartGradient-${color.replace('#', '')}`} x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor={color} stopOpacity={0.28} />
                            <stop offset="60%" stopColor={color} stopOpacity={0.06} />
                            <stop offset="100%" stopColor={color} stopOpacity={0.0} />
                        </linearGradient>
                    </defs>

                    <CartesianGrid
                        strokeDasharray="4 4"
                        vertical={false}
                        stroke="var(--border-subtle)"
                        strokeOpacity={0.6}
                    />

                    <XAxis 
                        dataKey="time" 
                        hide={true} 
                    />
                    <YAxis 
                        domain={[minPrice - padding, maxPrice + padding]} 
                        hide={true} 
                    />

                    <Tooltip
                        contentStyle={{
                            backgroundColor: 'var(--bg-surface)',
                            borderColor: 'var(--border-subtle)',
                            borderRadius: '12px',
                            padding: '8px 14px',
                            boxShadow: 'var(--shadow-elevated)',
                            backdropFilter: 'blur(8px)',
                        }}
                        itemStyle={{
                            color: 'var(--text-primary)',
                            fontSize: '12px',
                            fontWeight: '700',
                            fontFamily: 'var(--font-mono)',
                        }}
                        labelStyle={{ 
                            color: 'var(--text-tertiary)',
                            fontSize: '10px',
                            fontWeight: '600',
                            textTransform: 'uppercase',
                            letterSpacing: '0.05em',
                            marginBottom: '2px'
                        }}
                        cursor={{ 
                            stroke: color, 
                            strokeWidth: 1.5, 
                            strokeDasharray: '3 3',
                            strokeOpacity: 0.6
                        }}
                        formatter={(value) => [`$${Number(value).toFixed(2)}`, 'Price']}
                    />

                    <Area
                        type="monotone"
                        dataKey="price"
                        stroke={color}
                        fillOpacity={1}
                        fill={`url(#chartGradient-${color.replace('#', '')})`}
                        strokeWidth={2.2}
                        animationDuration={900}
                        dot={false}
                        activeDot={{
                            r: 5,
                            fill: color,
                            stroke: 'var(--bg-surface)',
                            strokeWidth: 2,
                            boxShadow: `0 0 10px ${color}`
                        }}
                    />
                </AreaChart>
            </ResponsiveContainer>
        </div>
    );
};

export default StockChart;

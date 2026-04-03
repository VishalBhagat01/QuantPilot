import React from 'react';
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    Area,
    AreaChart
} from 'recharts';
import { AreaChart as ChartIcon } from 'lucide-react';

/**
 * =============================================================================
 * StockChart Component — High-Contrast Intraday Visualization
 * =============================================================================
 */
const StockChart = ({ data, color }) => {
    
    // Empty/Loading State with high-contrast centered design
    if (!data || data.length === 0) {
        return (
            <div className="h-full flex flex-col items-center justify-center text-slate-600 gap-3 border-2 border-dashed border-white/5 rounded-3xl m-4">
                <div className="p-4 bg-white/5 rounded-full text-slate-700 animate-pulse">
                    <ChartIcon size={32} />
                </div>
                <div className="text-center">
                    <p className="text-xs font-black uppercase tracking-widest text-slate-500">No Chart Data</p>
                    <p className="text-[10px] text-slate-700 tracking-tight">Historical markers currently unavailable</p>
                </div>
            </div>
        );
    }

    return (
        <div className="w-full h-full transition-opacity duration-700">
            <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={data} margin={{ top: 20, right: 0, left: 0, bottom: 0 }}>
                    <defs>
                        <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor={color} stopOpacity={0.4} />
                            <stop offset="95%" stopColor={color} stopOpacity={0} />
                        </linearGradient>
                    </defs>
                    
                    <CartesianGrid 
                        strokeDasharray="4 4" 
                        vertical={false} 
                        stroke="#ffffff" 
                        strokeOpacity={0.03} 
                    />
                    
                    <XAxis
                        dataKey="time"
                        hide={true}
                    />
                    
                    <YAxis
                        domain={['auto', 'auto']}
                        hide={true}
                    />
                    
                    <Tooltip
                        contentStyle={{
                            backgroundColor: '#0f172a',
                            border: '1px solid rgba(255,255,255,0.05)',
                            borderRadius: '16px',
                            padding: '12px',
                            boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.5)',
                            backdropFilter: 'blur(10px)'
                        }}
                        itemStyle={{ 
                            color: '#fff', 
                            fontSize: '14px', 
                            fontWeight: 'bold',
                            fontFamily: 'tabular-nums' 
                        }}
                        labelStyle={{ 
                            display: 'none' 
                        }}
                        cursor={{ stroke: '#ffffff20', strokeWidth: 1 }}
                        formatter={(value) => [`$${value.toFixed(2)}`, 'Price']}
                    />
                    
                    <Area
                        type="monotone"
                        dataKey="price"
                        stroke={color}
                        fillOpacity={1}
                        fill="url(#colorPrice)"
                        strokeWidth={3}
                        animationDuration={1500}
                    />
                </AreaChart>
            </ResponsiveContainer>
        </div>
    );
};

export default StockChart;

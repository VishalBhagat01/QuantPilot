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
import './StockChart.css';

const StockChart = ({ data, color }) => {

    if (!data || data.length === 0) {
        return (
            <div className="chart-empty">
                <div className="chart-empty-icon">
                    <ChartIcon size={28} />
                </div>
                <div className="chart-empty-text">
                    <p className="chart-empty-title">No Chart Data</p>
                    <p className="chart-empty-sub">Historical markers currently unavailable</p>
                </div>
            </div>
        );
    }

    return (
        <div className="chart-wrapper">
            <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={data} margin={{ top: 20, right: 0, left: 0, bottom: 0 }}>
                    <defs>
                        <linearGradient id="colorPrice" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor={color} stopOpacity={0.35} />
                            <stop offset="95%" stopColor={color} stopOpacity={0} />
                        </linearGradient>
                    </defs>

                    <CartesianGrid
                        strokeDasharray="4 4"
                        vertical={false}
                        stroke="#ffffff"
                        strokeOpacity={0.03}
                    />

                    <XAxis dataKey="time" hide={true} />
                    <YAxis domain={['auto', 'auto']} hide={true} />

                    <Tooltip
                        contentStyle={{
                            backgroundColor: '#0a0e17',
                            border: '1px solid rgba(255,255,255,0.06)',
                            borderRadius: '12px',
                            padding: '10px 14px',
                            boxShadow: '0 16px 32px rgba(0, 0, 0, 0.5)',
                        }}
                        itemStyle={{
                            color: '#fff',
                            fontSize: '13px',
                            fontWeight: '700',
                        }}
                        labelStyle={{ display: 'none' }}
                        cursor={{ stroke: '#ffffff15', strokeWidth: 1 }}
                        formatter={(value) => [`$${value.toFixed(2)}`, 'Price']}
                    />

                    <Area
                        type="monotone"
                        dataKey="price"
                        stroke={color}
                        fillOpacity={1}
                        fill="url(#colorPrice)"
                        strokeWidth={2.5}
                        animationDuration={1500}
                    />
                </AreaChart>
            </ResponsiveContainer>
        </div>
    );
};

export default StockChart;

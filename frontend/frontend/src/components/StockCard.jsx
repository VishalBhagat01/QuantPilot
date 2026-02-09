import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { TrendingUp, TrendingDown, Activity, DollarSign, BarChart2, PieChart } from 'lucide-react';
import StockChart from './StockChart';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs) {
    return twMerge(clsx(inputs));
}

const StockCard = ({ symbol }) => {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchData = async () => {
            setLoading(true);
            try {
                const response = await axios.post('http://localhost:8000/agent/stock', { symbol });
                if (response.data && response.data.price !== undefined) {
                    setData(response.data);
                } else {
                    setError('No data found for this symbol');
                }
            } catch (err) {
                if (err.response && err.response.status === 429) {
                    setError('Rate limit exceeded (Quota). Please wait a moment and try again.');
                } else {
                    setError('Failed to reach the dashboard server');
                }
            } finally {
                setLoading(false);
            }
        };

        if (symbol) fetchData();
    }, [symbol]);

    if (loading) return (
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 w-full animate-pulse">
            <div className="h-6 w-32 bg-gray-800 rounded mb-4" />
            <div className="h-10 w-48 bg-gray-800 rounded mb-6" />
            <div className="h-48 w-full bg-gray-800 rounded" />
        </div>
    );

    if (error) return (
        <div className="bg-gray-900 border border-red-900/50 rounded-2xl p-6 w-full text-red-400">
            {error}
        </div>
    );

    if (!data) return null;

    const isPositive = data.change >= 0;
    const color = isPositive ? '#10b981' : '#ef4444';

    return (
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 w-full shadow-2xl text-gray-100">
            <div className="flex justify-between items-start mb-4">
                <div>
                    <h2 className="text-sm font-medium text-gray-400 uppercase tracking-wider">{data.company}</h2>
                    <h1 className="text-3xl font-bold mt-1">{data.symbol}</h1>
                </div>
                <div className="flex gap-2">
                    {['1D', '5D', '1M'].map((range) => (
                        <button
                            key={range}
                            className={cn(
                                "px-3 py-1 text-xs font-semibold rounded-md transition-colors",
                                range === '1D' ? "bg-blue-600 text-white" : "bg-gray-800 text-gray-400 hover:bg-gray-700"
                            )}
                        >
                            {range}
                        </button>
                    ))}
                </div>
            </div>

            <div className="flex items-baseline gap-3 mb-2">
                <span className="text-4xl font-bold">${data.price?.toFixed(2)}</span>
                <div className={cn("flex items-center text-sm font-medium", isPositive ? "text-green-400" : "text-red-400")}>
                    {isPositive ? <TrendingUp size={16} className="mr-1" /> : <TrendingDown size={16} className="mr-1" />}
                    <span>{isPositive ? '+' : ''}{data.change?.toFixed(2)} ({data.percent?.toFixed(2)}%)</span>
                </div>
            </div>

            <StockChart data={data.chart} color={color} />

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6 pt-6 border-t border-gray-800">
                <Metric label="Open" value={data.open} icon={<DollarSign size={14} />} />
                <Metric label="High" value={data.high} icon={<TrendingUp size={14} />} />
                <Metric label="Low" value={data.low} icon={<TrendingDown size={14} />} />
                <Metric label="Prev Close" value={data.prev_close} icon={<Activity size={14} />} />
                <Metric label="Volume" value={formatLargeNumber(data.volume)} icon={<BarChart2 size={14} />} />
                <Metric label="Mkt Cap" value={formatLargeNumber(data.market_cap)} icon={<PieChart size={14} />} />
            </div>
        </div>
    );
};

const Metric = ({ label, value, icon }) => (
    <div className="flex flex-col">
        <span className="text-[10px] text-gray-500 uppercase font-bold flex items-center gap-1 mb-1">
            {icon} {label}
        </span>
        <span className="text-sm font-semibold text-gray-200">
            {typeof value === 'number' ? value.toLocaleString() : (value || 'N/A')}
        </span>
    </div>
);

function formatLargeNumber(num) {
    if (!num) return 'N/A';
    if (num >= 1e12) return (num / 1e12).toFixed(2) + 'T';
    if (num >= 1e9) return (num / 1e9).toFixed(2) + 'B';
    if (num >= 1e6) return (num / 1e6).toFixed(2) + 'M';
    return num.toLocaleString();
}

export default StockCard;

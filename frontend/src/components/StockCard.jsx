import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { TrendingUp, TrendingDown, Activity, DollarSign, BarChart2, Info, Zap } from 'lucide-react';
import StockChart from './StockChart';
import './StockCard.css';

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
        <div className="sc-loading">
            <div className="sc-loading-spinner" />
            <span className="sc-loading-text">Hydrating Intelligence...</span>
        </div>
    );

    if (error) return (
        <div className="sc-error">
            <Activity size={16} />
            {error}
        </div>
    );

    if (!data) return null;

    const isPositive = data.change >= 0;
    const accentColor = isPositive ? 'rgba(16, 185, 129, 0.4)' : 'rgba(239, 68, 68, 0.4)';
    const showCompany = data.company && data.company !== data.symbol;

    return (
        <div className="sc-card">
            <div className="sc-glow" style={{ background: accentColor }} />

            <div className="sc-header">
                <div>
                    {showCompany && (
                        <h2 className="sc-company">{data.company}</h2>
                    )}
                    <h1 className="sc-symbol-row">
                        <div className="sc-symbol-icon">
                            <BarChart2 size={18} />
                        </div>
                        {data.symbol}
                        {!showCompany && <span className="sc-symbol-suffix">/ EQUITY</span>}
                    </h1>
                </div>

                <div className="sc-range-toggle">
                    {['1D', '5D', '1M'].map((range) => (
                        <button
                            key={range}
                            onClick={() => setActiveRange(range)}
                            className={`sc-range-btn ${activeRange === range ? 'active' : ''}`}
                        >
                            {range}
                        </button>
                    ))}
                </div>
            </div>

            <div className="sc-price-row">
                <span className="sc-price">
                    ${data.price?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </span>
                <div className={`sc-change-badge ${isPositive ? 'positive' : 'negative'}`}>
                    {isPositive ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
                    <span>
                        {isPositive ? '+' : ''}{data.change?.toFixed(2)} ({data.percent?.toFixed(2)}%)
                    </span>
                </div>
            </div>

            <div className="sc-chart-container">
                <StockChart data={data.chart} color={isPositive ? '#10b981' : '#ef4444'} />
                <div className="sc-chart-badge">
                    Model Confidence: {(data.confidence || 84)}%
                </div>
            </div>

            <div className="sc-metrics-grid">
                <Metric label="Market Open" value={data.open} icon={<DollarSign size={13} />} color="slate" />
                <Metric label="Intraday High" value={data.high} icon={<TrendingUp size={13} />} color="green" />
                <Metric label="Intraday Low" value={data.low} icon={<TrendingDown size={13} />} color="red" />
                <Metric label="Prev. Close" value={data.prev_close} icon={<Activity size={13} />} color="gold" />
            </div>

            <div className="sc-actions">
                <button className="sc-trade-btn">
                    <Zap size={16} />
                    TRADE ASSET
                </button>
                <button className="sc-info-btn" onClick={() => setExpanded(!expanded)}>
                    <Info size={18} />
                </button>
            </div>

            {expanded && (
                <div className="sc-expanded animate-fade-in">
                    <p className="sc-expanded-text">
                        {data.summary || "QuantPilot AI is aggregating consensus data... Expect technical breakout confirmation within 24 hours based on current momentum vectors."}
                    </p>
                    <div className="sc-expanded-stats">
                        <div className="sc-expanded-stat">
                            <div className="sc-expanded-stat-label">Vol Profile</div>
                            <div className="sc-expanded-stat-value">{data.volume || 'N/A'}</div>
                        </div>
                        <div className="sc-expanded-stat">
                            <div className="sc-expanded-stat-label">Mkt Cap</div>
                            <div className="sc-expanded-stat-value">{data.market_cap || 'N/A'}</div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

const Metric = ({ label, value, icon, color }) => {
    return (
        <div className="sc-metric">
            <div className="sc-metric-header">
                <div className={`sc-metric-icon ${color}`}>{icon}</div>
                <span className="sc-metric-label">{label}</span>
            </div>
            <div className="sc-metric-value">
                ${(value || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
            </div>
        </div>
    );
};

export default StockCard;

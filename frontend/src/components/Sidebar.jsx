import React, { useState } from 'react';
import { 
    Plus, 
    MessageSquare, 
    X, 
    Trash2, 
    Sparkles, 
    Search,
    ShieldCheck, 
    Terminal,
    ChevronRight,
    TrendingUp
} from 'lucide-react';

export default function Sidebar({ 
    threads, 
    activeThreadId, 
    onSelectThread, 
    onNewChat, 
    isOpen, 
    onClose, 
    onDeleteThread 
}) {
    const [searchFilter, setSearchFilter] = useState('');

    const filteredThreads = (threads || []).filter(t => 
        (t.title || '').toLowerCase().includes(searchFilter.toLowerCase())
    );

    return (
        <aside 
            className={`fixed lg:static inset-y-0 left-0 w-[290px] bg-[var(--bg-surface)] border-r border-[var(--border-subtle)] flex flex-col z-50 transform transition-transform duration-300 ease-out shadow-2xl lg:shadow-none select-none ${
                isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
            }`}
        >
            {/* ── Brand Header ── */}
            <div className="flex items-center justify-between px-5 h-16 border-b border-[var(--border-subtle)] shrink-0">
                <div className="flex items-center gap-2.5">
                    <div className="relative w-8 h-8 rounded-xl bg-gradient-to-br from-[var(--color-quant-orange)] to-amber-600 flex items-center justify-center text-white shadow-md shadow-orange-500/25">
                        <Terminal size={17} className="stroke-[2.5]" />
                        <span className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-emerald-500 ring-2 ring-[var(--bg-surface)]" />
                    </div>
                    <div>
                        <div className="flex items-center gap-1.5">
                            <span className="font-extrabold text-sm tracking-tight text-[var(--text-primary)]">
                                QuantPilot
                            </span>
                            <span className="text-[9px] font-black uppercase tracking-wider px-1.5 py-0.2 rounded bg-orange-500/10 text-[var(--color-quant-orange)] border border-orange-500/20">
                                AI
                            </span>
                        </div>
                        <p className="text-[10px] font-semibold text-[var(--text-tertiary)] uppercase tracking-wider">
                            Trading Intelligence
                        </p>
                    </div>
                </div>

                <button 
                    className="lg:hidden p-1.5 rounded-lg text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-surface-elevated)] transition-colors" 
                    onClick={onClose}
                    aria-label="Close sidebar"
                >
                    <X size={18} />
                </button>
            </div>

            {/* ── New Chat CTA ── */}
            <div className="p-4 shrink-0 space-y-3">
                <button 
                    onClick={onNewChat}
                    className="w-full flex items-center justify-between bg-gradient-to-r from-[var(--color-quant-orange)] to-orange-600 hover:to-orange-500 text-white py-2.5 px-4 rounded-xl font-bold text-xs tracking-wider transition-all duration-200 shadow-md shadow-orange-500/20 active:scale-[0.98] group cursor-pointer"
                >
                    <div className="flex items-center gap-2">
                        <Plus size={16} className="stroke-[2.5] transition-transform duration-200 group-hover:rotate-90" />
                        <span>NEW ANALYSIS</span>
                    </div>
                    <span className="text-[10px] font-mono bg-white/20 px-1.5 py-0.5 rounded text-white/90">
                        ⌘N
                    </span>
                </button>

                {/* Search filter for past conversations */}
                <div className="relative">
                    <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-tertiary)] pointer-events-none" />
                    <input 
                        type="text"
                        placeholder="Search past threads..."
                        value={searchFilter}
                        onChange={(e) => setSearchFilter(e.target.value)}
                        className="w-full bg-[var(--bg-surface-elevated)] border border-[var(--border-subtle)] rounded-lg py-1.5 pl-8 pr-3 text-xs text-[var(--text-primary)] placeholder:text-[var(--text-tertiary)] outline-none focus:border-[var(--color-quant-orange)] transition-colors"
                    />
                </div>
            </div>

            {/* ── Conversation History List ── */}
            <div className="flex-1 overflow-y-auto px-3 py-1 space-y-1">
                <div className="flex items-center justify-between px-3 py-1.5">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--text-tertiary)]">
                        Conversation History
                    </span>
                    <span className="text-[10px] font-mono text-[var(--text-tertiary)]">
                        {filteredThreads.length}
                    </span>
                </div>

                {filteredThreads.map((thread) => {
                    const isActive = activeThreadId === thread.id;
                    return (
                        <div
                            key={thread.id}
                            onClick={() => {
                                onSelectThread(thread.id);
                                if (window.innerWidth <= 1024) onClose();
                            }}
                            className={`group relative flex items-center justify-between px-3 py-2.5 rounded-xl cursor-pointer transition-all duration-150 ${
                                isActive 
                                    ? 'bg-[var(--bg-surface-elevated)] border border-[var(--border-accent)] shadow-sm' 
                                    : 'hover:bg-[var(--bg-surface-elevated)]/60 border border-transparent'
                            }`}
                        >
                            {/* Active left indicator strip */}
                            {isActive && (
                                <div className="absolute left-0 top-2 bottom-2 w-1 rounded-r-full bg-[var(--color-quant-orange)]" />
                            )}

                            <div className="flex items-center gap-2.5 overflow-hidden min-w-0 pr-2">
                                <MessageSquare 
                                    size={14} 
                                    className={`shrink-0 transition-colors ${
                                        isActive 
                                            ? 'text-[var(--color-quant-orange)]' 
                                            : 'text-[var(--text-tertiary)] group-hover:text-[var(--text-secondary)]'
                                    }`} 
                                />
                                <span className={`text-xs truncate transition-colors ${
                                    isActive 
                                        ? 'font-bold text-[var(--text-primary)]' 
                                        : 'font-medium text-[var(--text-secondary)] group-hover:text-[var(--text-primary)]'
                                }`}>
                                    {thread.title || 'Untitled Session'}
                                </span>
                            </div>

                            <button
                                className={`p-1.5 rounded-lg text-[var(--text-tertiary)] hover:text-red-500 hover:bg-red-500/10 transition-all duration-150 ${
                                    isActive ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'
                                }`}
                                onClick={(e) => {
                                    e.stopPropagation();
                                    onDeleteThread(thread.id);
                                }}
                                title="Delete Conversation"
                            >
                                <Trash2 size={13} />
                            </button>
                        </div>
                    );
                })}

                {filteredThreads.length === 0 && (
                    <div className="px-4 py-10 text-center text-xs text-[var(--text-tertiary)]">
                        <p>{searchFilter ? 'No matching threads found.' : 'No recent analyses recorded.'}</p>
                    </div>
                )}
            </div>

            {/* ── System Telemetry Pill ── */}
            <div className="px-4 py-2 shrink-0">
                <div className="bg-[var(--bg-surface-elevated)]/70 border border-[var(--border-subtle)] rounded-xl p-3 flex items-center justify-between text-[11px]">
                    <div className="flex items-center gap-2 text-[var(--text-secondary)]">
                        <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                        <span className="font-semibold">LangGraph Swarm</span>
                    </div>
                    <span className="text-[10px] font-mono text-[var(--text-tertiary)] uppercase">
                        Online
                    </span>
                </div>
            </div>

            {/* ── User Profile Footer ── */}
            <div className="p-4 border-t border-[var(--border-subtle)] shrink-0">
                <div className="flex items-center gap-3 p-2 rounded-xl hover:bg-[var(--bg-surface-elevated)] transition-colors">
                    <div className="relative w-9 h-9 rounded-xl bg-gradient-to-tr from-orange-500 to-amber-400 text-white font-black flex items-center justify-center text-xs shadow-sm shrink-0">
                        VB
                        <span className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-emerald-500 ring-2 ring-[var(--bg-surface)]" />
                    </div>
                    <div className="flex flex-col min-w-0 flex-1">
                        <span className="font-bold text-xs text-[var(--text-primary)] truncate">
                            Vishal Bhagat
                        </span>
                        <div className="flex items-center gap-1">
                            <span className="text-[10px] font-bold text-[var(--color-quant-orange)] uppercase tracking-wider">
                                Hedge Fund Pro
                            </span>
                        </div>
                    </div>
                </div>
            </div>
        </aside>
    );
}

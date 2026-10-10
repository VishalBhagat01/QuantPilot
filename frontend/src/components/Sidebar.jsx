import React, { useState, useEffect, useRef } from 'react';
import { 
    Plus, 
    MessageSquare, 
    X, 
    Trash2, 
    Search,
    User,
    Edit2,
    Check,
} from 'lucide-react';
import Logo from './Logo';

export default function Sidebar({ 
    user,
    threads, 
    activeThreadId, 
    onSelectThread, 
    onNewChat, 
    isOpen, 
    onClose, 
    onDeleteThread 
}) {
    const [searchFilter, setSearchFilter] = useState('');
    const [isEditingName, setIsEditingName] = useState(false);
    
    const defaultName = user?.name || user?.email?.split('@')[0] || 'Pro Trader';
    const [customName, setCustomName] = useState(
        localStorage.getItem('quantpilot_custom_name') || defaultName
    );
    const nameInputRef = useRef(null);

    useEffect(() => {
        if (isEditingName) {
            nameInputRef.current?.focus();
        }
    }, [isEditingName]);

    const handleNameSave = () => {
        setIsEditingName(false);
        const finalName = customName.trim() || defaultName;
        setCustomName(finalName);
        localStorage.setItem('quantpilot_custom_name', finalName);
    };

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
                    <div className="relative w-8 h-8 rounded-xl bg-[var(--color-quant-orange)] flex items-center justify-center overflow-hidden shadow-md shadow-orange-500/25">
                        <Logo size={28} />
                    </div>
                    <div>
                        <div className="flex items-center gap-1.5">
                            <span className="font-display text-lg font-semibold tracking-tight text-[var(--text-primary)]">
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

            {/* ── Account Footer ── */}
            <div className="shrink-0 p-4 border-t border-[var(--border-subtle)] bg-[var(--bg-surface)]/50">
                <div className="flex items-center gap-3 p-2 -m-2 rounded-xl transition-colors">
                    <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-[var(--color-quant-orange)] to-orange-400 flex items-center justify-center text-white shadow-sm shrink-0 overflow-hidden">
                        {user?.avatar_url ? (
                            <img src={user.avatar_url} alt="Avatar" className="w-full h-full object-cover" />
                        ) : (
                            <User size={15} className="stroke-[2.5]" />
                        )}
                    </div>
                    <div className="flex flex-col flex-1 min-w-0">
                        {isEditingName ? (
                            <div className="flex items-center gap-1 w-full">
                                <input
                                    ref={nameInputRef}
                                    type="text"
                                    value={customName}
                                    onChange={(e) => setCustomName(e.target.value)}
                                    onBlur={handleNameSave}
                                    onKeyDown={(e) => e.key === 'Enter' && handleNameSave()}
                                    className="text-xs font-bold text-[var(--text-primary)] bg-[var(--bg-surface-elevated)] border border-[var(--color-quant-orange)] rounded px-1.5 py-0.5 outline-none w-full max-w-[120px]"
                                    placeholder="Enter name"
                                />
                                <button onMouseDown={(e) => e.preventDefault()} onClick={handleNameSave} className="text-emerald-500 p-0.5 hover:bg-emerald-500/10 rounded cursor-pointer">
                                    <Check size={12} strokeWidth={3} />
                                </button>
                            </div>
                        ) : (
                            <div className="flex items-center gap-1 group/name cursor-pointer w-fit" onClick={() => setIsEditingName(true)} title="Click to edit name">
                                <span className="text-xs font-bold text-[var(--text-primary)] truncate max-w-[120px]">{customName}</span>
                                <Edit2 size={10} className="text-[var(--text-tertiary)] opacity-0 group-hover/name:opacity-100 transition-opacity" />
                            </div>
                        )}
                        <span className="text-[10px] text-[var(--text-tertiary)] truncate">{user?.email || 'Pro Plan'}</span>
                    </div>
                </div>
            </div>
        </aside>
    );
}

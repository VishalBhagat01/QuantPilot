import React from 'react';
import { Plus, MessageSquare, X, Trash2, Home, BarChart2, Settings, User } from 'lucide-react';

export default function Sidebar({ threads, activeThreadId, onSelectThread, onNewChat, isOpen, onClose, onDeleteThread }) {
    return (
        <div className={`sidebar ${isOpen ? 'open' : ''}`}>
            <div className="sidebar-header">
                <div className="flex items-center gap-2 px-2">
                    <div className="w-6 h-6 rounded bg-indigo-500/20 flex items-center justify-center">
                        <BarChart2 size={14} className="text-indigo-400" />
                    </div>
                    <span className="font-bold text-xs tracking-widest text-slate-400 uppercase">Menu</span>
                </div>
                <button className="lg:hidden text-slate-500" onClick={onClose}>
                    <X size={20} />
                </button>
            </div>

            <button className="new-chat-btn mb-6" onClick={onNewChat}>
                <Plus size={18} />
                New Analysis
            </button>

            <div className="threads-list px-1">
                <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-3 px-3">Recent History</div>
                {threads.map((thread) => (
                    <div
                        key={thread.id}
                        className={`thread-item-container ${activeThreadId === thread.id ? 'active' : ''}`}
                    >
                        <div
                            className="thread-item"
                            onClick={() => {
                                onSelectThread(thread.id);
                                if (window.innerWidth <= 768) onClose();
                            }}
                        >
                            <MessageSquare size={16} className={activeThreadId === thread.id ? 'text-indigo-400' : 'text-slate-500'} />
                            <span className="truncate">{thread.title}</span>
                        </div>
                        <button
                            className="delete-thread-btn"
                            onClick={(e) => {
                                e.stopPropagation();
                                onDeleteThread(thread.id);
                            }}
                            title="Delete Chat"
                        >
                            <Trash2 size={14} />
                        </button>
                    </div>
                ))}

                {threads.length === 0 && (
                    <div className="px-4 py-8 text-center">
                        <p className="text-xs text-slate-600 italic">No recent chats</p>
                    </div>
                )}
            </div>

            <div className="sidebar-footer">
                <div className="user-profile bg-white/5 rounded-2xl p-3 border border-white/5">
                    <div className="avatar">V</div>
                    <div className="flex flex-col">
                        <span className="user-name">Vishal Bhagat</span>
                        <span className="text-[10px] text-slate-500 font-medium">Premium Member</span>
                    </div>
                    <Settings size={16} className="ml-auto text-slate-500 cursor-pointer hover:text-white transition-colors" />
                </div>
            </div>
        </div>
    );
}

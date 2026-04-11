import React from 'react';
import { Plus, MessageSquare, X, Trash2, BarChart2, Settings } from 'lucide-react';

export default function Sidebar({ threads, activeThreadId, onSelectThread, onNewChat, isOpen, onClose, onDeleteThread }) {
    return (
        <div className={`sidebar ${isOpen ? 'open' : ''}`}>
            <div className="sidebar-header">
                <div className="sidebar-brand">
                    <div className="sidebar-brand-icon">
                        <BarChart2 size={14} />
                    </div>
                    <span className="sidebar-brand-text">Menu</span>
                </div>
                <button className="sidebar-close-btn" onClick={onClose}>
                    <X size={18} />
                </button>
            </div>

            <button className="new-chat-btn" onClick={onNewChat}>
                <Plus size={16} />
                New Analysis
            </button>

            <div className="threads-list">
                <div className="threads-section-label">Recent History</div>
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
                            <MessageSquare size={15} className="thread-icon" />
                            <span className="thread-title">{thread.title}</span>
                        </div>
                        <button
                            className="delete-thread-btn"
                            onClick={(e) => {
                                e.stopPropagation();
                                onDeleteThread(thread.id);
                            }}
                            title="Delete Chat"
                        >
                            <Trash2 size={13} />
                        </button>
                    </div>
                ))}

                {threads.length === 0 && (
                    <div className="empty-threads">
                        <p>No recent chats</p>
                    </div>
                )}
            </div>

            <div className="sidebar-footer">
                <div className="user-profile">
                    <div className="avatar">V</div>
                    <div className="user-info">
                        <span className="user-name">Vishal Bhagat</span>
                        <span className="user-role">Premium Member</span>
                    </div>
                    <button className="settings-btn">
                        <Settings size={15} />
                    </button>
                </div>
            </div>
        </div>
    );
}

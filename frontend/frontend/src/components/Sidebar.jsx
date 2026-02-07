import React from 'react';
import { Plus, MessageSquare, X, Trash2 } from 'lucide-react';

export default function Sidebar({ threads, activeThreadId, onSelectThread, onNewChat, isOpen, onClose, onDeleteThread }) {
    return (
        <div className={`sidebar ${isOpen ? 'open' : ''}`}>
            <div className="sidebar-header">
                <button className="new-chat-btn" onClick={onNewChat}>
                    <Plus size={18} />
                    New Chat
                </button>
                <button className="close-sidebar-btn" onClick={onClose}>
                    <X size={20} />
                </button>
            </div>

            <div className="threads-list">
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
                            <MessageSquare size={16} />
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
                            <Trash2 size={14} />
                        </button>
                    </div>
                ))}
            </div>

            <div className="sidebar-footer">
                <div className="user-profile">
                    <div className="avatar">V</div>
                    <span className="user-name">Vishal Bhagat</span>
                </div>
            </div>
        </div>
    );
}

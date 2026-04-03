import { useState, useRef, useEffect } from "react"
import axios from "axios"
import ReactMarkdown from 'react-markdown'
import { Send, Bot, User, Menu, PlusCircle, Loader2, Wrench, CheckCircle2, ChevronDown, ChevronUp, MessageSquare, BarChart2 } from 'lucide-react'
import Sidebar from "./components/Sidebar"
import StockCard from "./components/StockCard"
// NEW: Import the TradingPanel for pattern detection & broker features
import TradingPanel from "./components/TradingPanel"
import "./App.css"

const API_BASE = "http://localhost:8000"

export default function App() {
  const [input, setInput] = useState("")
  const [messages, setMessages] = useState([
    { role: "assistant", content: "Hello! I am your Stock AI Assistant. Ask me about any stock price, news, or analysis." }
  ])
  const [threads, setThreads] = useState([])
  const [activeThreadId, setActiveThreadId] = useState(null)
  const [loading, setLoading] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  // NEW: Track which view is active — 'chat' (default) or 'trading'
  const [activeView, setActiveView] = useState('chat')
  const chatEndRef = useRef(null)

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  useEffect(() => {
    fetchThreads()
  }, [])

  const fetchThreads = async () => {
    try {
      const res = await axios.get(`${API_BASE}/threads`)
      setThreads(res.data)
    } catch (err) {
      console.error("Failed to fetch threads", err)
    }
  }

  const handleSelectThread = async (id) => {
    setActiveThreadId(id)
    setLoading(true)
    try {
      const res = await axios.get(`${API_BASE}/threads/${id}`)
      setMessages(res.data.messages)
    } catch (err) {
      console.error("Failed to fetch thread history", err)
    }
    setLoading(false)
  }

  const handleNewChat = () => {
    setActiveThreadId(null)
    setMessages([
      { role: "assistant", content: "Hello again! How can I help you with the stock market today?" }
    ])
    if (window.innerWidth <= 768) setSidebarOpen(false)
  }

  const handleDeleteThread = async (id) => {
    if (!window.confirm("Are you sure you want to delete this conversation?")) return;

    try {
      await axios.delete(`${API_BASE}/threads/${id}`)
      if (activeThreadId === id) {
        handleNewChat()
      }
      fetchThreads()
    } catch (err) {
      console.error("Failed to delete thread", err)
      alert("Error: Could not delete the conversation.")
    }
  }

  const sendMessage = async () => {
    if (!input.trim()) return

    const userMessage = { role: "user", content: input }
    setMessages(prev => [...prev, userMessage])
    const query = input
    setInput("")
    setLoading(true)

    try {
      const res = await axios.post(`${API_BASE}/analyze`, {
        query: query,
        thread_id: activeThreadId
      })

      const aiMessage = { role: "assistant", content: res.data.response }
      setMessages(prev => [...prev, aiMessage])

      if (res.data.thread_id && !activeThreadId) {
        setActiveThreadId(res.data.thread_id)
        fetchThreads()
      }
    } catch (err) {
      console.error("Analysis failed:", err)
      setMessages(prev => [...prev, {
        role: "assistant",
        content: "Error: Could not reach the AI. Please ensure the backend server is running."
      }])
    }

    setLoading(false)
  }

  return (
    <div className="app-container">
      <Sidebar
        threads={threads}
        activeThreadId={activeThreadId}
        onSelectThread={handleSelectThread}
        onNewChat={handleNewChat}
        onDeleteThread={handleDeleteThread}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      {sidebarOpen && <div className="sidebar-overlay" onClick={() => setSidebarOpen(false)} />}

      <main className="chat-main">
        <header className="mobile-header">
          <button className="menu-btn" onClick={() => setSidebarOpen(true)}>
            <Menu size={20} />
          </button>
          
          <div className="flex items-center gap-3 ml-2 lg:ml-0">
             <div className="w-8 h-8 rounded-lg bg-indigo-500/20 flex items-center justify-center border border-indigo-500/30">
                <Bot size={18} className="text-indigo-400" />
             </div>
             <span className="font-bold text-white tracking-tight">QuantPilot AI</span>
          </div>

          {/* ── NEW: View toggle buttons (Chat vs Trading) ── */}
          <div className="flex bg-slate-900/50 backdrop-blur-md rounded-xl p-1 border border-white/5 ml-auto mr-4">
            <button
              onClick={() => setActiveView('chat')}
              className={`px-4 py-1.5 rounded-lg text-[10px] font-bold transition-all duration-300 flex items-center gap-2 ${
                activeView === 'chat' 
                  ? 'bg-indigo-500 text-white shadow-lg' 
                  : 'text-slate-500 hover:text-slate-300'
              }`}
            >
              <MessageSquare size={14} />
              CHAT
            </button>
            <button
              onClick={() => setActiveView('trading')}
              className={`px-4 py-1.5 rounded-lg text-[10px] font-bold transition-all duration-300 flex items-center gap-2 ${
                activeView === 'trading' 
                  ? 'bg-indigo-500 text-white shadow-lg' 
                  : 'text-slate-500 hover:text-slate-300'
              }`}
            >
              <BarChart2 size={14} />
              TERMINAL
            </button>
          </div>

          <button className="p-2 hover:bg-white/5 rounded-lg transition-colors lg:hidden" onClick={handleNewChat}>
            <PlusCircle size={20} className="text-slate-400" />
          </button>
        </header>

        <div className="flex-1 relative overflow-hidden">
          {activeView === 'trading' ? (
            <div className="trading-view-container h-full">
              <TradingPanel />
            </div>
          ) : (
            <div className="h-full flex flex-col">
              <div className="chat-history">
                {messages.map((msg, idx) => (
                  <div key={idx} className={`message ${msg.role} animate-fade-in`}>
                    <div className="icon">
                      {msg.role === 'user' ? <User size={20} /> : <Bot size={20} />}
                    </div>
                    <div className="bubble">
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                      {msg.content.includes("DASHBOARD:") && (
                        <div className="mt-8">
                          <StockCard symbol={msg.content.split("DASHBOARD:")[1].trim().split(" ")[0].split("\n")[0]} />
                        </div>
                      )}
                    </div>
                  </div>
                ))}

                {loading && (
                  <div className="message assistant animate-fade-in">
                    <div className="icon"><Bot size={20} /></div>
                    <div className="bubble loading">
                      <div className="flex items-center gap-3 bg-slate-900/50 rounded-2xl px-6 py-4 border border-white/5">
                        <Loader2 size={18} className="animate-spin text-indigo-400" />
                        <span className="text-sm font-medium text-slate-400">Analyzing market data...</span>
                      </div>
                    </div>
                  </div>
                )}

                <div ref={chatEndRef} />
              </div>

              <div className="input-container">
                <div className="input-box">
                  <input
                    placeholder="Ask me anything about stocks..."
                    value={input}
                    onChange={e => setInput(e.target.value)}
                    onKeyPress={e => e.key === "Enter" && sendMessage()}
                  />
                  <button className="send-btn" onClick={sendMessage} disabled={loading || !input.trim()}>
                    {loading ? <Loader2 size={20} className="animate-spin" /> : <Send size={20} />}
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}

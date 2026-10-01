import { useState, useRef, useEffect } from "react"
import axios from "axios"
import ReactMarkdown from 'react-markdown'
import { supabase } from './supabaseClient'
import Auth from './components/Auth'
import { 
  Send, 
  Bot, 
  User, 
  Menu, 
  PlusCircle, 
  Loader2, 
  MessageSquare, 
  BarChart3, 
  TrendingUp, 
  Zap, 
  Search, 
  DollarSign, 
  Sun, 
  Moon,
  Copy,
  Check,
  Terminal,
  Cpu,
  Sparkles,
  ArrowRight,
  ShieldCheck,
  Activity
} from 'lucide-react'
import Sidebar from "./components/Sidebar"
import StockCard from "./components/StockCard"
import TradingPanel from "./components/TradingPanel"

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000"

export default function App() {
  const [session, setSession] = useState(null)
  const [input, setInput] = useState("")
  const [messages, setMessages] = useState([
    { 
      role: "assistant", 
      content: "Welcome to **QuantPilot AI**. I am your institutional financial intelligence assistant. Ask me for real-time market data, technical indicator analysis, YOLOv8 chart pattern scans, or simulated trade execution." 
    }
  ])
  const [threads, setThreads] = useState([])
  const [activeThreadId, setActiveThreadId] = useState(null)
  const [loading, setLoading] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [activeView, setActiveView] = useState('chat')
  const [selectedTradeSymbol, setSelectedTradeSymbol] = useState('')
  const [copiedIdx, setCopiedIdx] = useState(null)
  const [isDarkMode, setIsDarkMode] = useState(() => {
    const saved = localStorage.getItem('quantpilot_theme')
    if (saved) return saved === 'dark'
    return true // Default dark mode
  })
  
  const chatEndRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session)
      if (session) {
        axios.defaults.headers.common['Authorization'] = `Bearer ${session.access_token}`;
      }
    })

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session)
      if (session) {
        axios.defaults.headers.common['Authorization'] = `Bearer ${session.access_token}`;
      } else {
        delete axios.defaults.headers.common['Authorization'];
      }
    })

    return () => subscription.unsubscribe()
  }, [])

  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.remove('light')
      document.documentElement.classList.add('dark')
      localStorage.setItem('quantpilot_theme', 'dark')
    } else {
      document.documentElement.classList.add('light')
      document.documentElement.classList.remove('dark')
      localStorage.setItem('quantpilot_theme', 'light')
    }
  }, [isDarkMode])

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  const fetchThreads = async () => {
    try {
      const res = await axios.get(`${API_BASE}/threads`)
      setThreads(res.data)
    } catch (err) {
      console.error("Failed to fetch threads", err)
    }
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  useEffect(() => {
    let isMounted = true
    const loadInitialThreads = async () => {
      try {
        const res = await axios.get(`${API_BASE}/threads`)
        if (isMounted) setThreads(res.data)
      } catch (err) {
        console.error("Failed to fetch initial threads", err)
      }
    }
    loadInitialThreads()
    return () => {
      isMounted = false
    }
  }, [])

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
      { 
        role: "assistant", 
        content: "New intelligence session initialized. How can I assist your portfolio today?" 
      }
    ])
    if (window.innerWidth <= 1024) setSidebarOpen(false)
    inputRef.current?.focus()
  }

  const handleDeleteThread = async (id) => {
    if (!window.confirm("Permanently archive and delete this analysis thread?")) return;

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

  const executeQuery = async (queryText) => {
    if (!queryText.trim()) return

    const userMessage = { role: "user", content: queryText }
    setMessages(prev => [...prev, userMessage])
    setInput("")
    setLoading(true)

    try {
      const res = await axios.post(`${API_BASE}/analyze`, {
        query: queryText,
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
        content: "Network or Agent Disruption: Could not reach the backend execution agent. Please verify that the FastAPI server is running."
      }])
    }

    setLoading(false)
  }

  const sendMessage = () => {
    if (input.trim() && !loading) {
      executeQuery(input)
    }
  }

  const handleQuickAction = (query) => {
    executeQuery(query)
  }

  const copyMessage = (content, idx) => {
    navigator.clipboard.writeText(content)
    setCopiedIdx(idx)
    setTimeout(() => setCopiedIdx(null), 2000)
  }

  const isWelcomeState = messages.length <= 1 && !loading

  if (!session) {
    return <Auth />
  }

  return (
    <div className="flex h-screen w-screen overflow-hidden relative bg-[var(--bg-base)] text-[var(--text-primary)]">
      {/* ── Sidebar ── */}
      <Sidebar
        threads={threads}
        activeThreadId={activeThreadId}
        onSelectThread={handleSelectThread}
        onNewChat={handleNewChat}
        onDeleteThread={handleDeleteThread}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      {/* Mobile Backdrop */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 lg:hidden transition-opacity" 
          onClick={() => setSidebarOpen(false)} 
        />
      )}

      {/* ── Main App Shell ── */}
      <main className="flex-1 flex flex-col relative h-full min-w-0 bg-[var(--bg-base)]">
        {/* Top Navbar */}
        <header className="flex items-center justify-between px-4 sm:px-7 h-16 bg-[var(--bg-surface-glass)] backdrop-blur-xl border-b border-[var(--border-subtle)] z-30 shrink-0">
          <div className="flex items-center gap-3">
            <button 
              className="lg:hidden p-2 rounded-xl hover:bg-[var(--bg-surface-elevated)] border border-[var(--border-subtle)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors cursor-pointer" 
              onClick={() => setSidebarOpen(true)}
              aria-label="Open sidebar"
            >
              <Menu size={18} />
            </button>

            <div className="flex items-center gap-2.5">
              <div className="relative w-8 h-8 rounded-xl bg-gradient-to-tr from-[var(--color-quant-orange)] to-amber-500 text-white flex items-center justify-center shadow-md shadow-orange-500/20">
                <Bot size={17} />
              </div>
              <div>
                <span className="font-extrabold text-sm sm:text-base tracking-tight text-[var(--text-primary)]">
                  QuantPilot
                </span>
                <div className="hidden md:flex items-center gap-1.5 text-[10px] text-emerald-500 font-bold uppercase tracking-wider">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                  <span>US Markets Active</span>
                </div>
              </div>
            </div>
          </div>

          {/* Central Segmented Pill Switcher */}
          <div className="flex items-center bg-[var(--bg-surface-elevated)] rounded-2xl p-1 border border-[var(--border-subtle)] shadow-inner">
            <button
              onClick={() => setActiveView('chat')}
              className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-bold tracking-wider transition-all duration-200 cursor-pointer ${
                activeView === 'chat' 
                  ? 'bg-[var(--bg-surface)] text-[var(--color-quant-orange)] border border-[var(--border-subtle)] shadow-sm' 
                  : 'text-[var(--text-tertiary)] hover:text-[var(--text-primary)]'
              }`}
            >
              <MessageSquare size={13} />
              <span>AI AGENT</span>
            </button>
            <button
              onClick={() => setActiveView('trading')}
              className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-xs font-bold tracking-wider transition-all duration-200 cursor-pointer ${
                activeView === 'trading' 
                  ? 'bg-[var(--bg-surface)] text-[var(--color-quant-orange)] border border-[var(--border-subtle)] shadow-sm' 
                  : 'text-[var(--text-tertiary)] hover:text-[var(--text-primary)]'
              }`}
            >
              <BarChart3 size={13} />
              <span>TERMINAL</span>
            </button>
          </div>

          {/* Right Controls */}
          <div className="flex items-center gap-2">
            <button 
              className="p-2 rounded-xl text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-surface-elevated)] border border-[var(--border-subtle)] transition-colors cursor-pointer"
              onClick={() => setIsDarkMode(!isDarkMode)}
              title={isDarkMode ? "Switch to Light Mode" : "Switch to Dark Mode"}
              aria-label="Toggle Theme"
            >
              {isDarkMode ? <Sun size={17} className="text-amber-400" /> : <Moon size={17} />}
            </button>

            <button 
              className="p-2 rounded-xl text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-surface-elevated)] border border-[var(--border-subtle)] transition-colors hidden sm:flex cursor-pointer" 
              onClick={handleNewChat}
              title="Start New Analysis"
              aria-label="New Chat"
            >
              <PlusCircle size={17} />
            </button>
            <button
              className="p-2 rounded-xl text-red-400 hover:text-red-500 hover:bg-red-500/10 border border-[var(--border-subtle)] transition-colors hidden sm:flex cursor-pointer ml-2"
              onClick={() => supabase.auth.signOut()}
              title="Sign Out"
              aria-label="Sign Out"
            >
              <span className="text-xs font-bold tracking-wider px-1">LOGOUT</span>
            </button>
          </div>
        </header>

        {/* ── Viewport Container ── */}
        <div className="flex-1 relative overflow-hidden">
          {activeView === 'trading' ? (
            <div className="h-full overflow-hidden animate-in fade-in duration-300">
              <TradingPanel 
                initialSymbol={selectedTradeSymbol} 
                onAskAI={(prompt) => {
                  setActiveView('chat')
                  executeQuery(prompt)
                }}
              />
            </div>
          ) : (
            <div className="h-full flex flex-col">
              {/* Message Feed */}
              <div className="flex-1 overflow-y-auto pt-6 pb-[190px] px-3 sm:px-6">
                {isWelcomeState && (
                  <div className="flex flex-col items-center justify-center pt-8 sm:pt-14 px-4 text-center max-w-3xl mx-auto animate-in fade-in duration-500">
                    {/* Glowing Logo Halo */}
                    <div className="relative mb-6">
                      <div className="absolute inset-0 bg-orange-500/20 rounded-3xl blur-2xl transform scale-150 pointer-events-none" />
                      <div className="relative w-16 h-16 rounded-3xl bg-gradient-to-tr from-[var(--color-quant-orange)] to-amber-500 flex items-center justify-center text-white shadow-xl shadow-orange-500/30">
                        <Terminal size={32} className="stroke-[2.5]" />
                      </div>
                    </div>

                    <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-orange-500/10 border border-orange-500/20 text-[var(--color-quant-orange)] text-[11px] font-bold uppercase tracking-wider mb-3">
                      <Sparkles size={12} />
                      <span>Autonomous Equity Intelligence</span>
                    </div>

                    <h1 className="text-2xl sm:text-4xl font-extrabold tracking-tight mb-3 text-[var(--text-primary)]">
                      Welcome to <span className="bg-gradient-to-r from-orange-500 to-amber-400 bg-clip-text text-transparent">QuantPilot</span>
                    </h1>

                    <p className="text-xs sm:text-sm text-[var(--text-secondary)] max-w-lg leading-relaxed mb-9">
                      Real-time equity intelligence, level-1 broker feeds, YOLOv8 chart pattern detection, and autonomous trading agent orchestration.
                    </p>

                    {/* Quick-Prompt Cards Grid */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5 w-full text-left">
                      <PromptCard
                        icon={<DollarSign size={16} className="text-blue-500" />}
                        title="Live Quotes & Trend"
                        description="What is the price and trend of NVDA?"
                        onClick={() => handleQuickAction("What is the price of NVDA?")}
                      />
                      <PromptCard
                        icon={<TrendingUp size={16} className="text-emerald-500" />}
                        title="Deep Technical Audit"
                        description="Give me a full technical analysis of TSLA"
                        onClick={() => handleQuickAction("Give me a full technical analysis of TSLA")}
                      />
                      <PromptCard
                        icon={<Search size={16} className="text-amber-500" />}
                        title="Vision Pattern Scan"
                        description="Scan AAPL for YOLOv8 chart patterns"
                        onClick={() => handleQuickAction("Scan AAPL for chart patterns")}
                      />
                      <PromptCard
                        icon={<ShieldCheck size={16} className="text-purple-500" />}
                        title="Portfolio & Cash Check"
                        description="Show my open positions and buying power"
                        onClick={() => handleQuickAction("Show my open positions and account status")}
                      />
                    </div>
                  </div>
                )}

                {/* Messages List */}
                {messages.map((msg, idx) => {
                  const isUser = msg.role === 'user'
                  return (
                    <div 
                      key={idx} 
                      className={`flex px-2 sm:px-6 py-5 gap-3.5 sm:gap-4 max-w-4xl mx-auto w-full animate-in fade-in slide-in-from-bottom-2 duration-200 ${
                        isUser ? 'justify-end' : 'justify-start'
                      }`}
                    >
                      {/* Assistant Avatar */}
                      {!isUser && (
                        <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-[var(--color-quant-orange)] to-amber-500 text-white flex items-center justify-center shrink-0 mt-0.5 shadow-sm shadow-orange-500/20">
                          <Bot size={16} />
                        </div>
                      )}

                      {/* Content Bubble */}
                      <div className={`relative group max-w-[85%] sm:max-w-[78%] ${
                        isUser 
                          ? 'bg-gradient-to-br from-[var(--color-quant-orange)] to-orange-600 text-white rounded-2xl rounded-tr-sm px-4 sm:px-5 py-3 shadow-md shadow-orange-500/15' 
                          : 'bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded-2xl rounded-tl-sm px-5 py-4 shadow-[var(--shadow-card)] text-[var(--text-primary)] w-full'
                      }`}>
                        {isUser ? (
                          <p className="text-sm font-medium leading-relaxed whitespace-pre-wrap">
                            {msg.content}
                          </p>
                        ) : (
                          <div className="prose text-sm">
                            <ReactMarkdown>{msg.content}</ReactMarkdown>

                            {/* Embedded StockCard if DASHBOARD: is returned by agent */}
                            {msg.content.includes("DASHBOARD:") && (
                              <div className="mt-5">
                                <StockCard 
                                  symbol={msg.content.split("DASHBOARD:")[1].trim().split(" ")[0].split("\n")[0]}
                                  onTrade={(symbol) => {
                                    setSelectedTradeSymbol(symbol);
                                    setActiveView('trading');
                                  }}
                                />
                              </div>
                            )}

                            {/* Copy button & telemetry */}
                            <div className="mt-3 pt-2.5 border-t border-[var(--border-subtle)] flex items-center justify-between text-[11px] text-[var(--text-tertiary)]">
                              <span className="font-mono text-[10px]">QuantPilot Engine</span>
                              <button
                                onClick={() => copyMessage(msg.content, idx)}
                                className="flex items-center gap-1 hover:text-[var(--text-primary)] transition-colors p-1 rounded cursor-pointer"
                                title="Copy response to clipboard"
                              >
                                {copiedIdx === idx ? (
                                  <>
                                    <Check size={12} className="text-emerald-500" />
                                    <span className="text-emerald-500 text-[10px]">Copied</span>
                                  </>
                                ) : (
                                  <>
                                    <Copy size={12} />
                                    <span className="text-[10px]">Copy</span>
                                  </>
                                )}
                              </button>
                            </div>
                          </div>
                        )}
                      </div>

                      {/* User Avatar */}
                      {isUser && (
                        <div className="w-8 h-8 rounded-xl bg-[var(--bg-surface-elevated)] border border-[var(--border-subtle)] text-[var(--text-primary)] font-black text-xs flex items-center justify-center shrink-0 mt-0.5 shadow-sm">
                          <User size={15} />
                        </div>
                      )}
                    </div>
                  )
                })}

                {/* Loading indicator */}
                {loading && (
                  <div className="flex px-2 sm:px-6 py-5 gap-3.5 sm:gap-4 max-w-4xl mx-auto w-full animate-in fade-in duration-200">
                    <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-[var(--color-quant-orange)] to-amber-500 text-white flex items-center justify-center shrink-0 shadow-sm">
                      <Bot size={16} />
                    </div>
                    <div className="bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded-2xl rounded-tl-sm px-4 sm:px-5 py-3.5 shadow-sm inline-flex items-center gap-3">
                      <Loader2 size={16} className="animate-spin text-[var(--color-quant-orange)]" />
                      <span className="text-xs font-semibold text-[var(--text-secondary)]">
                        Synthesizing financial telemetry & agent consensus...
                      </span>
                    </div>
                  </div>
                )}

                <div ref={chatEndRef} />
              </div>

              {/* ── Docked Bottom Command Bar ── */}
              <div className="absolute bottom-0 left-0 right-0 px-3 sm:px-6 pb-5 pt-10 bg-gradient-to-t from-[var(--bg-base)] via-[var(--bg-base)]/90 to-transparent pointer-events-none z-20">
                <div className="max-w-3xl mx-auto pointer-events-auto">
                  {/* Floating Input Box */}
                  <div className="flex items-center bg-[var(--bg-surface-glass)] backdrop-blur-2xl rounded-2xl pl-5 pr-2 py-1.5 border border-[var(--border-subtle)] shadow-[var(--shadow-elevated)] transition-all focus-within:border-[var(--color-quant-orange)] focus-within:ring-2 focus-within:ring-orange-500/15">
                    <input
                      ref={inputRef}
                      className="flex-1 bg-transparent border-0 text-[var(--text-primary)] text-sm outline-none py-3 placeholder:text-[var(--text-tertiary)]"
                      placeholder="Ask QuantPilot about any stock (e.g. 'Analyze TSLA', 'Quote AAPL', 'Buy 5 NVDA')..."
                      value={input}
                      onChange={e => setInput(e.target.value)}
                      onKeyDown={e => e.key === "Enter" && !e.shiftKey && sendMessage()}
                    />
                    <button 
                      onClick={sendMessage} 
                      disabled={loading || !input.trim()}
                      className="bg-gradient-to-r from-[var(--color-quant-orange)] to-orange-600 hover:to-orange-500 text-white p-3 rounded-xl flex items-center justify-center transition-all disabled:opacity-30 disabled:cursor-not-allowed shadow-md shadow-orange-500/20 active:scale-[0.96] ml-2 cursor-pointer"
                      aria-label="Send query"
                    >
                      {loading ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
                    </button>
                  </div>

                  <div className="flex items-center justify-between px-3 mt-2 text-[10px] text-[var(--text-tertiary)] select-none">
                    <span>Press <kbd className="font-mono bg-[var(--bg-surface-elevated)] border border-[var(--border-subtle)] px-1 py-0.5 rounded text-[9px]">Enter ↵</kbd> to submit</span>
                    <span className="hidden sm:inline">LLM Model dynamic switching active via .env</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}

function PromptCard({ icon, title, description, onClick }) {
  return (
    <button
      onClick={onClick}
      className="p-4 rounded-2xl bg-[var(--bg-surface)] hover:bg-[var(--bg-surface-elevated)] border border-[var(--border-subtle)] hover:border-[var(--border-accent)] transition-all text-left group shadow-sm cursor-pointer"
    >
      <div className="flex items-center gap-2 mb-1.5">
        <div className="p-1.5 rounded-lg bg-[var(--bg-surface-elevated)] group-hover:bg-[var(--bg-surface)] border border-[var(--border-subtle)] transition-colors">
          {icon}
        </div>
        <span className="text-xs font-bold text-[var(--text-primary)] group-hover:text-[var(--color-quant-orange)] transition-colors">
          {title}
        </span>
      </div>
      <p className="text-xs text-[var(--text-secondary)] line-clamp-1">
        {description}
      </p>
    </button>
  )
}

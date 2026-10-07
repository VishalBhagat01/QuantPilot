import { useState, useRef, useEffect } from "react"
import axios from "axios"
import ReactMarkdown from 'react-markdown'
import Auth from './components/Auth'
import TermsGate from './components/TermsGate'
import { 
  initializeAuth, 
  exchangeCodeForSession, 
  signOut, 
  getStoredTokens, 
  clearSession,
  checkTermsAccepted,
  acceptTerms,
  getStoredUser
} from './authApi'
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
  const [user, setUser] = useState(null)
  const [authLoading, setAuthLoading] = useState(true)
  const [termsAccepted, setTermsAccepted] = useState(false)
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

  // ── Initialize Auth from Backend ──
  useEffect(() => {
    const init = async () => {
      // Check if this is an OAuth callback (URL has ?code= parameter)
      const params = new URLSearchParams(window.location.search)
      const code = params.get('code')
      
      if (code) {
        try {
          const session = await exchangeCodeForSession(code)
          setUser(session.user)
          // Check if terms were accepted already
          const accepted = await checkTermsAccepted()
          setTermsAccepted(accepted)
          // Clean the URL
          window.history.replaceState({}, document.title, window.location.pathname)
        } catch (err) {
          console.error("OAuth callback failed:", err)
          clearSession()
        }
        setAuthLoading(false)
        return
      }

      // Normal init: check for stored session
      try {
        const { user: existingUser, termsAccepted: accepted } = await initializeAuth()
        if (existingUser) {
          setUser(existingUser)
          setTermsAccepted(accepted)
        }
      } catch (err) {
        console.error("Auth init failed:", err)
        clearSession()
      }
      setAuthLoading(false)
    }

    init()
  }, [])

  // ── Theme Management ──
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
    if (user && termsAccepted) {
      fetchThreads()
    } else {
      setThreads([])
      setActiveThreadId(null)
      setMessages([
        { 
          role: "assistant", 
          content: "Welcome to **QuantPilot AI**. I am your institutional financial intelligence assistant. Ask me for real-time market data, technical indicator analysis, YOLOv8 chart pattern scans, or simulated trade execution." 
        }
      ])
    }
  }, [user, termsAccepted])

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

  const copyMessage = (content, idx) => {
    navigator.clipboard.writeText(content)
    setCopiedIdx(idx)
    setTimeout(() => setCopiedIdx(null), 2000)
  }

  const handleSignOut = async () => {
    await signOut()
    setUser(null)
    setTermsAccepted(false)
  }

  const handleTermsAccepted = async () => {
    try {
      await acceptTerms()
      setTermsAccepted(true)
    } catch (err) {
      console.error("Failed to accept terms:", err)
    }
  }

  const isWelcomeState = messages.length <= 1 && !loading

  // ── Auth Loading ──
  if (authLoading) {
    return (
      <div className="flex flex-col items-center justify-center h-screen bg-[var(--bg-base)] text-[var(--text-primary)]">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-[var(--color-quant-orange)] border-2 border-[var(--border-subtle)] flex items-center justify-center shadow-[var(--shadow-sm)]">
            <Terminal size={20} className="text-white" />
          </div>
          <span className="font-display text-2xl font-black tracking-tight">quantpilot</span>
        </div>
        <Loader2 size={24} className="animate-spin text-[var(--color-quant-orange)]" />
        <p className="mt-3 font-mono text-xs text-[var(--text-tertiary)]">Initializing session...</p>
      </div>
    )
  }

  // ── Show Login if No User ──
  if (!user) {
    return <Auth />
  }

  // ── Show Terms Gate if Terms Not Accepted ──
  if (!termsAccepted) {
    return <TermsGate onAccept={handleTermsAccepted} onDecline={handleSignOut} />
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
        <header className="flex items-center justify-between px-4 sm:px-7 h-16 bg-[var(--bg-base)] border-b-2 border-[var(--border-subtle)] z-30 shrink-0">
          <div className="flex items-center gap-4 sm:gap-6 lg:gap-8">
            <button 
              className="lg:hidden flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border-2 border-[var(--border-subtle)] bg-[var(--bg-surface)] text-[var(--text-primary)] shadow-[var(--shadow-sm)]" 
              onClick={() => setSidebarOpen(true)}
              aria-label="Open sidebar"
            >
              <Menu size={18} />
            </button>

            <div className="flex items-center gap-2.5 group cursor-default">
              <div className="w-8 h-8 rounded-xl bg-[var(--color-quant-orange)] border-2 border-[var(--border-subtle)] flex items-center justify-center shadow-[var(--shadow-sm)] group-hover:rotate-6 transition-transform">
                <Terminal size={16} className="text-white" />
              </div>
              <div className="flex items-center gap-2">
                <span className="font-display text-base sm:text-lg tracking-tight font-black text-[var(--text-primary)]">
                  quantpilot
                </span>
                <span className="hidden sm:inline-block text-[10px] font-mono font-bold px-2 py-0.5 rounded-full bg-[var(--bg-surface-elevated)] border border-[var(--border-subtle)] text-[var(--text-primary)]">
                  [agent]
                </span>
              </div>
            </div>
          </div>

          {/* Central Segmented Pill Switcher */}
          <div className="flex items-center gap-2 bg-[var(--bg-surface-elevated)] rounded-full p-1 border-2 border-[var(--border-subtle)] shadow-[var(--shadow-sm)]">
            <button
              onClick={() => setActiveView('chat')}
              className={`flex items-center gap-1.5 px-4 py-1.5 rounded-full text-xs font-mono font-bold tracking-tight transition-all duration-200 cursor-pointer ${
                activeView === 'chat' 
                  ? 'bg-[var(--text-primary)] text-[var(--bg-base)] shadow-[var(--shadow-sm)]' 
                  : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-surface-hover)]'
              }`}
            >
              <MessageSquare size={14} />
              <span>Agent</span>
            </button>
            <button
              onClick={() => setActiveView('trading')}
              className={`flex items-center gap-1.5 px-4 py-1.5 rounded-full text-xs font-mono font-bold tracking-tight transition-all duration-200 cursor-pointer ${
                activeView === 'trading' 
                  ? 'bg-[var(--text-primary)] text-[var(--bg-base)] shadow-[var(--shadow-sm)]' 
                  : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-surface-hover)]'
              }`}
            >
              <BarChart3 size={14} />
              <span>Terminal</span>
            </button>
          </div>

          {/* Right Controls */}
          <div className="flex items-center gap-2">
            <button 
              className="flex h-9 w-9 items-center justify-center rounded-xl text-[var(--text-primary)] bg-[var(--bg-surface)] hover:bg-[var(--bg-surface-hover)] border-2 border-[var(--border-subtle)] shadow-[var(--shadow-sm)] transition-colors cursor-pointer"
              onClick={() => setIsDarkMode(!isDarkMode)}
              title={isDarkMode ? "Switch to Light Mode" : "Switch to Dark Mode"}
              aria-label="Toggle Theme"
            >
              {isDarkMode ? <Sun size={17} className="text-[var(--color-quant-orange)]" /> : <Moon size={17} />}
            </button>

            <button 
              className="flex h-9 w-9 items-center justify-center rounded-xl text-[var(--text-primary)] bg-[var(--bg-surface)] hover:bg-[var(--bg-surface-hover)] border-2 border-[var(--border-subtle)] shadow-[var(--shadow-sm)] transition-colors hidden sm:flex cursor-pointer" 
              onClick={handleNewChat}
              title="Start New Analysis"
              aria-label="New Chat"
            >
              <PlusCircle size={17} />
            </button>
            <button
              className="px-4 py-1.5 h-9 rounded-full bg-[var(--color-quant-orange)] text-white hover:bg-orange-600 border-2 border-[var(--border-subtle)] shadow-[var(--shadow-sm)] transition-colors hidden sm:flex cursor-pointer items-center ml-2"
              onClick={handleSignOut}
              title="Sign Out"
              aria-label="Sign Out"
            >
              <span className="text-xs font-mono font-bold tracking-tight">Logout</span>
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
                  <div className="flex flex-col items-center justify-center pt-16 sm:pt-24 px-4 text-center max-w-3xl mx-auto">
                    <div className="inline-flex items-center gap-2 rounded-full border-2 border-[var(--border-subtle)] bg-[var(--text-primary)] px-3.5 py-1 text-[11px] font-mono font-black uppercase text-[var(--bg-base)] shadow-[var(--shadow-sm)] mb-6">
                      <span className="h-2 w-2 rounded-full bg-[var(--color-quant-orange)]"></span>
                      QuantPilot Terminal
                    </div>
                    <h1 className="font-display text-4xl sm:text-6xl font-black uppercase tracking-tight text-[var(--text-primary)] mb-4">
                      Financial Intelligence
                    </h1>
                    <p className="font-mono text-sm sm:text-base text-[var(--text-secondary)] max-w-lg leading-relaxed mb-10">
                      Real-time equity intelligence, level-1 broker feeds, YOLOv8 chart pattern detection, and autonomous trading orchestration.
                    </p>
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
                        <div className="w-8 h-8 rounded-xl bg-[var(--bg-surface)] border-2 border-[var(--border-subtle)] text-[var(--text-primary)] flex items-center justify-center shrink-0 mt-0.5 shadow-[var(--shadow-sm)]">
                          <Bot size={16} />
                        </div>
                      )}

                      {/* Content Bubble */}
                      <div className={`relative group max-w-[85%] sm:max-w-[78%] ${
                        isUser 
                          ? 'bg-[var(--color-quant-orange)] text-white rounded-[20px] border-2 border-[var(--border-subtle)] px-4 sm:px-5 py-3 shadow-[var(--shadow-card)]' 
                          : 'bg-[var(--bg-surface-elevated)] border-2 border-[var(--border-subtle)] rounded-[20px] px-5 py-4 shadow-[var(--shadow-card)] text-[var(--text-primary)] w-full'
                      }`}>
                        {isUser ? (
                          <p className="text-sm font-mono leading-relaxed whitespace-pre-wrap">
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
                        <div className="w-8 h-8 rounded-xl bg-[var(--bg-surface)] border-2 border-[var(--border-subtle)] text-[var(--text-primary)] font-black text-xs flex items-center justify-center shrink-0 mt-0.5 shadow-[var(--shadow-sm)]">
                          <User size={15} />
                        </div>
                      )}
                    </div>
                  )
                })}

                {/* Loading indicator */}
                {loading && (
                  <div className="flex px-2 sm:px-6 py-5 gap-3.5 sm:gap-4 max-w-4xl mx-auto w-full animate-in fade-in duration-200">
                    <div className="w-8 h-8 rounded-xl bg-[var(--bg-surface)] border-2 border-[var(--border-subtle)] text-[var(--text-primary)] flex items-center justify-center shrink-0 mt-0.5 shadow-[var(--shadow-sm)]">
                      <Bot size={16} />
                    </div>
                    <div className="bg-[var(--bg-surface-elevated)] border-2 border-[var(--border-subtle)] rounded-[20px] px-4 sm:px-5 py-3.5 shadow-[var(--shadow-card)] inline-flex items-center gap-3">
                      <Loader2 size={16} className="animate-spin text-[var(--text-primary)]" />
                      <span className="text-xs font-mono font-bold text-[var(--text-secondary)]">
                        Thinking...
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
                  <div className="flex items-center bg-[var(--bg-surface)] rounded-2xl pl-5 pr-2 py-1.5 border-2 border-[var(--border-subtle)] shadow-[var(--shadow-elevated)] transition-all focus-within:-translate-y-1">
                    <input
                      ref={inputRef}
                      className="flex-1 bg-transparent border-0 text-[var(--text-primary)] font-mono text-sm outline-none py-3 placeholder:text-[var(--text-tertiary)]"
                      placeholder="Ask QuantPilot..."
                      value={input}
                      onChange={e => setInput(e.target.value)}
                      onKeyDown={e => e.key === "Enter" && !e.shiftKey && sendMessage()}
                    />
                    <button 
                      onClick={sendMessage} 
                      disabled={loading || !input.trim()}
                      className="bg-[var(--color-quant-orange)] hover:bg-orange-600 text-white p-3 rounded-xl flex items-center justify-center transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-[var(--shadow-sm)] active:translate-y-[2px] active:translate-x-[2px] active:shadow-none ml-2 cursor-pointer border-2 border-[var(--border-subtle)]"
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

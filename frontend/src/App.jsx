import { useState, useRef, useEffect } from "react"
import axios from "axios"
import ReactMarkdown from 'react-markdown'
import { Send, Bot, User, Menu, PlusCircle, Loader2, MessageSquare, BarChart2, TrendingUp, Zap, Search, DollarSign } from 'lucide-react'
import Sidebar from "./components/Sidebar"
import StockCard from "./components/StockCard"
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

  const handleQuickAction = (query) => {
    setInput(query)
  }

  const isWelcomeState = messages.length <= 1 && !loading

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
            <Menu size={18} />
          </button>

          <div className="header-brand">
            <div className="header-brand-icon">
              <Bot size={18} />
            </div>
            <span className="header-brand-name">QuantPilot AI</span>
          </div>

          <div className="view-toggle">
            <button
              onClick={() => setActiveView('chat')}
              className={`view-toggle-btn ${activeView === 'chat' ? 'active' : ''}`}
            >
              <MessageSquare size={13} />
              CHAT
            </button>
            <button
              onClick={() => setActiveView('trading')}
              className={`view-toggle-btn ${activeView === 'trading' ? 'active' : ''}`}
            >
              <BarChart2 size={13} />
              TERMINAL
            </button>
          </div>

          <button className="header-new-chat-btn" onClick={handleNewChat}>
            <PlusCircle size={20} />
          </button>
        </header>

        <div style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
          {activeView === 'trading' ? (
            <div className="trading-view-container">
              <TradingPanel />
            </div>
          ) : (
            <div className="chat-view">
              <div className="chat-history">
                {isWelcomeState && (
                  <div className="welcome-screen">
                    <div className="welcome-logo">
                      <Bot size={32} />
                    </div>
                    <h1 className="welcome-title">
                      Welcome to <span className="text-gradient-mixed">QuantPilot</span>
                    </h1>
                    <p className="welcome-subtitle">
                      Your AI-powered stock analysis assistant. Get real-time quotes, technical analysis, pattern detection, and automated trading signals.
                    </p>
                    <div className="welcome-chips">
                      <button className="welcome-chip" onClick={() => handleQuickAction("What is the price of AAPL?")}>
                        <DollarSign size={15} className="welcome-chip-icon" />
                        AAPL Stock Price
                      </button>
                      <button className="welcome-chip" onClick={() => handleQuickAction("Give me a full analysis of TSLA")}>
                        <TrendingUp size={15} className="welcome-chip-icon" />
                        Analyze TSLA
                      </button>
                      <button className="welcome-chip" onClick={() => handleQuickAction("Show me today's top gainers")}>
                        <Zap size={15} className="welcome-chip-icon" />
                        Top Gainers
                      </button>
                      <button className="welcome-chip" onClick={() => handleQuickAction("Scan NVDA for chart patterns")}>
                        <Search size={15} className="welcome-chip-icon" />
                        Scan NVDA Patterns
                      </button>
                    </div>
                  </div>
                )}

                {messages.map((msg, idx) => (
                  <div key={idx} className={`message ${msg.role} animate-fade-in`}>
                    <div className="icon">
                      {msg.role === 'user' ? <User size={18} /> : <Bot size={18} />}
                    </div>
                    <div className="bubble">
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                      {msg.content.includes("DASHBOARD:") && (
                        <div style={{ marginTop: '24px' }}>
                          <StockCard 
                            symbol={msg.content.split("DASHBOARD:")[1].trim().split(" ")[0].split("\n")[0]}
                            onTrade={(symbol) => setActiveView('trading')}
                          />
                        </div>
                      )}
                    </div>
                  </div>
                ))}

                {loading && (
                  <div className="message assistant animate-fade-in">
                    <div className="icon"><Bot size={18} /></div>
                    <div className="bubble">
                      <div className="loading-indicator">
                        <Loader2 size={16} className="loading-spinner" />
                        <span className="loading-text">Analyzing market data...</span>
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
                    onKeyDown={e => e.key === "Enter" && sendMessage()}
                  />
                  <button className="send-btn" onClick={sendMessage} disabled={loading || !input.trim()}>
                    {loading ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
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

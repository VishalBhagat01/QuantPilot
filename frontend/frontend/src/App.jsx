import { useState, useRef, useEffect } from "react"
import axios from "axios"
import ReactMarkdown from 'react-markdown'
import { Send, Bot, User, Menu, PlusCircle } from 'lucide-react'
import Sidebar from "./components/Sidebar"
import StockCard from "./components/StockCard"
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
  const [loadingText, setLoadingText] = useState("Analyzing...")
  const [sidebarOpen, setSidebarOpen] = useState(false)
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

  useEffect(() => {
    let interval
    if (loading && !activeThreadId) {
      const texts = [
        "Thinking...",
        "Fetching stock data...",
        "Analyzing market news...",
        "Computing insights...",
        "Formatting response..."
      ]
      let i = 0
      interval = setInterval(() => {
        setLoadingText(texts[i % texts.length])
        i++
      }, 3000)
    } else {
      setLoadingText("Analyzing...")
    }
    return () => clearInterval(interval)
  }, [loading, activeThreadId])

  const sendMessage = async () => {
    if (!input.trim()) return

    const userMessage = { role: "user", content: input }
    setMessages(prev => [...prev, userMessage])
    setInput("")
    setLoading(true)

    try {
      const res = await axios.post(`${API_BASE}/analyze`, {
        query: input,
        thread_id: activeThreadId
      })

      const aiMessage = { role: "assistant", content: res.data.response }
      setMessages(prev => [...prev, aiMessage])

      if (!activeThreadId) {
        setActiveThreadId(res.data.thread_id)
        fetchThreads()
      }
    } catch (err) {
      setMessages(prev => [...prev, { role: "assistant", content: "Error: Could not reach the AI. Please ensure the backend server is running." }])
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
            <Menu size={24} />
          </button>
          <span className="current-thread-title">
            {threads.find(t => t.id === activeThreadId)?.title || "New Chat"}
          </span>
          <button className="mobile-new-chat-btn" onClick={handleNewChat}>
            <PlusCircle size={24} />
          </button>
        </header>

        <div className="chat-history">
          {messages.map((msg, idx) => (
            <div key={idx} className={`message ${msg.role}`}>
              <div className="icon">
                {msg.role === 'user' ? <User size={20} color="white" /> : <Bot size={20} color="white" />}
              </div>
              <div className="bubble">
                <ReactMarkdown>{msg.content}</ReactMarkdown>
                {msg.content.includes("DASHBOARD:") && (
                  <div className="mt-4">
                    <StockCard symbol={msg.content.split("DASHBOARD:")[1].trim().split(" ")[0]} />
                  </div>
                )}
              </div>
            </div>
          ))}
          {loading && !messages.find(m => m.role === 'assistant' && (m.content === loadingText || m.content?.includes("Thinking"))) && (
            <div className="message assistant">
              <div className="icon"><Bot size={20} color="white" /></div>
              <div className="bubble loading">
                <span className="text">{loadingText}</span>
                <div className="dots">
                  <span className="dot"></span>
                  <span className="dot"></span>
                  <span className="dot"></span>
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
            <button className="send-btn" onClick={sendMessage} disabled={loading}>
              <Send size={20} />
            </button>
          </div>
        </div>
      </main>
    </div>
  )
}

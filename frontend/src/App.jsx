
import { useState } from 'react'
import './App.css'

// Use Render backend URL in production.
// Use Vite proxy during local development.
const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || ''
).replace(/\/+$/, '')

function App() {
  const [message, setMessage] = useState('')
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)

  const sendMessage = async () => {
    if (!message.trim() || loading) return

    const userMessage = message.trim()

    setMessages((prev) => [
      ...prev,
      { role: 'user', text: userMessage }
    ])

    setMessage('')
    setLoading(true)

    try {
      const chatUrl = API_BASE_URL
        ? `${API_BASE_URL}/chat`
        : '/api/chat'

      const response = await fetch(chatUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ message: userMessage })
      })

      const responseText = await response.text()
      let data = {}

      if (responseText.trim()) {
        try {
          data = JSON.parse(responseText)
        } catch {
          throw new Error(
            `Invalid server response (HTTP ${response.status}): ${responseText.slice(0, 200)}`
          )
        }
      }

      if (!response.ok) {
        throw new Error(
          data.error || `Server error: ${response.status}`
        )
      }

      if (!data.reply) {
        throw new Error(
          data.error || 'Backend returned an empty response.'
        )
      }

      setMessages((prev) => [
        ...prev,
        { role: 'assistant', text: data.reply }
      ])

    } catch (error) {
      console.error('AskNova Error:', error)

      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          text: error.message || 'Unknown error occurred.'
        }
      ])

    } finally {
      setLoading(false)
    }
  }

  const newChat = () => {
    setMessages([])
    setMessage('')
    setLoading(false)
  }

  return (
    <div className="app-container">
      <aside className="sidebar">
        <h2 className="logo">✦ AskNova AI</h2>

        <button className="new-chat-btn" onClick={newChat}>
          + New Chat
        </button>

        <div className="sidebar-bottom">
          <p>⚙ Settings</p>
          <p>© 2026 AskNova AI</p>
        </div>
      </aside>

      <main className="chat-area">
        <header className="topbar">
          <h3>AI Assistant</h3>
          <span className="status">● Online</span>
        </header>

        {messages.length === 0 ? (
          <section className="welcome-section">
            <div className="nova-icon">✦</div>

            <h1>Welcome to AskNova AI</h1>

            <p>
              Your intelligent AI assistant.
              Ask anything and explore new ideas.
            </p>

            <div className="suggestions">
              <div className="suggestion-card">
                What is Artificial Intelligence?
              </div>

              <div className="suggestion-card">
                Explain React in simple words.
              </div>

              <div className="suggestion-card">
                Give me interview questions.
              </div>

              <div className="suggestion-card">
                How does Machine Learning work?
              </div>
            </div>
          </section>
        ) : (
          <section className="messages-container">
            {messages.map((msg, index) => (
              <div
                key={index}
                className={`message ${msg.role}`}
              >
                <strong>
                  {msg.role === 'user' ? 'You' : '✦ AskNova AI'}
                </strong>

                <p>{msg.text}</p>
              </div>
            ))}

            {loading && (
              <div className="loading-text">
                ✦ AskNova AI is thinking...
              </div>
            )}
          </section>
        )}

        <form
          className="input-container"
          onSubmit={(e) => {
            e.preventDefault()
            sendMessage()
          }}
        >
          <input
            type="text"
            placeholder="Ask Nova anything..."
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            disabled={loading}
          />

          <button
            className="send-btn"
            type="submit"
            disabled={loading || !message.trim()}
          >
            ↑
          </button>
        </form>

        <p className="footer-text">
          AskNova AI can make mistakes. Verify important information.
        </p>
      </main>
    </div>
  )
}

export default App

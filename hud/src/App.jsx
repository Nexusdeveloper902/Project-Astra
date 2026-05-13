import { useState, useEffect, useRef } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import "./App.css";

function App() {
  const [input, setInput] = useState("");
  const [status, setStatus] = useState("Ready");
  const [messages, setMessages] = useState([]);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    const unlisten = listen("astra-event", (event) => {
      const { event: eventType, data } = event.payload;

      if (eventType === "ui.output") {
        setMessages((prev) => [...prev, { role: "assistant", text: data.text }]);
        setStatus("Ready");
      } else if (eventType === "task.updated") {
        setStatus(data.status.charAt(0).toUpperCase() + data.status.slice(1) + "...");
      } else if (eventType === "task.completed") {
        setStatus("Ready");
      } else if (eventType === "task.failed") {
        setStatus("Error: " + data.error);
        setTimeout(() => setStatus("Ready"), 5000);
      }
    });

    return () => {
      unlisten.then((f) => f());
    };
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userText = input;
    setMessages((prev) => [...prev, { role: "user", text: userText }]);
    setInput("");
    setStatus("Thinking...");

    try {
      await invoke("send_input", { text: userText });
    } catch (error) {
      console.error(error);
      setStatus("Error connecting to Astra");
    }
  };

  return (
    <main className="container">
      <div className="chat-container">
        {messages.map((msg, i) => (
          <div key={i} className={`message ${msg.role}`}>
            {msg.text.startsWith("[Executing:") ? (
              <div className="action-tag">{msg.text}</div>
            ) : (
              <div className="message-text">{msg.text}</div>
            )}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <div className="bottom-bar">
        <form onSubmit={handleSubmit} className="input-form">
          <input
            id="astra-input"
            onChange={(e) => setInput(e.currentTarget.value)}
            value={input}
            placeholder="Ask Astra..."
            autoFocus
            autoComplete="off"
          />
          <div className="status-indicator">
            <span className="status-dot" data-status={status}></span>
            {status}
          </div>
        </form>
      </div>
    </main>
  );
}

export default App;

import { useState, useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";
import { listen } from "@tauri-apps/api/event";
import "./App.css";

function App() {
  const [input, setInput] = useState("");
  const [status, setStatus] = useState("Ready");
  const [response, setResponse] = useState("");

  useEffect(() => {
    const unlisten = listen("astra-message", (event) => {
      setResponse(event.payload);
      setStatus("Ready");
    });
    return () => {
      unlisten.then(f => f());
    }
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;
    
    setStatus("Sending...");
    setResponse("");
    try {
      await invoke("send_input", { text: input });
      setInput("");
      // Status will reset when astra-message is received
    } catch (error) {
      console.error(error);
      setStatus("Error");
    }
  };

  return (
    <main className="container">
      <form onSubmit={handleSubmit} className="input-form">
        <input
          id="astra-input"
          onChange={(e) => setInput(e.currentTarget.value)}
          value={input}
          placeholder="Ask Astra..."
          autoFocus
          autoComplete="off"
        />
        <div className="status">{status}</div>
      </form>
      {response && (
        <div className="response-box">
          {response.startsWith("[Executing:") ? (
            <div className="action-tag">{response}</div>
          ) : (
            <div>{response}</div>
          )}
        </div>
      )}
    </main>
  );
}

export default App;

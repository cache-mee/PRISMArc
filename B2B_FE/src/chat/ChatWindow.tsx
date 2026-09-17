import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { sendChatMessage } from "../api/chat";
import { getOrCreateSessionId } from "./session";

interface ChatMessage {
  role: "customer" | "agent";
  text: string;
}

function ChatWindow() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputText, setInputText] = useState("");

  useEffect(() => {
    const sessionId = getOrCreateSessionId();

    sendChatMessage({ session_id: sessionId, message: null })
      .then((response) => {
        setMessages((previousMessages) => [
          ...previousMessages,
          { role: "agent", text: response.reply },
        ]);
      })
      .catch((error: unknown) => {
        console.error("Failed to load opening chat message", error);
      });
  }, []);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const trimmedText = inputText.trim();
    if (!trimmedText) {
      return;
    }

    const sessionId = getOrCreateSessionId();

    setMessages((previousMessages) => [
      ...previousMessages,
      { role: "customer", text: trimmedText },
    ]);
    setInputText("");

    sendChatMessage({ session_id: sessionId, message: trimmedText })
      .then((response) => {
        setMessages((previousMessages) => [
          ...previousMessages,
          { role: "agent", text: response.reply },
        ]);
      })
      .catch((error: unknown) => {
        console.error("Failed to send chat message", error);
      });
  };

  return (
    <section>
      <ul>
        {messages.map((message, index) => (
          <li key={`${message.role}-${index.toString()}`}>
            <strong>{message.role === "customer" ? "You" : "Agent"}:</strong>{" "}
            {message.text}
          </li>
        ))}
      </ul>
      <form onSubmit={handleSubmit}>
        <input
          type="text"
          value={inputText}
          onChange={(event) => {
            setInputText(event.target.value);
          }}
          placeholder="Type a message"
        />
        <button type="submit">Send</button>
      </form>
    </section>
  );
}

export default ChatWindow;

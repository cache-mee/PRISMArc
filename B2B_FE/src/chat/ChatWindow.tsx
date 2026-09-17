import { useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { sendChatMessage } from "../api/chat";
import { getOrCreateSessionId } from "./session";
import MaterialIcon from "../shared/MaterialIcon";

interface ChatMessage {
  role: "customer" | "agent";
  text: string;
}

function ChatWindow() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputText, setInputText] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const threadRef = useRef<HTMLDivElement>(null);

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

  useEffect(() => {
    threadRef.current?.scrollTo({ top: threadRef.current.scrollHeight });
  }, [messages, isOpen]);

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
    <div className="fixed right-5 bottom-5 z-50 flex flex-col items-end">
      {isOpen ? (
        <div className="mb-3 flex h-[560px] w-[360px] max-w-[calc(100vw-2.5rem)] flex-col overflow-hidden rounded-2xl bg-surface shadow-2xl">
          <div className="flex shrink-0 items-center justify-between bg-primary px-4 py-3 text-white">
            <div className="flex items-center gap-2.5">
              <div className="relative flex h-9 w-9 items-center justify-center rounded-full bg-primary-dark">
                <MaterialIcon name="spa" className="text-[18px]" />
                <span className="absolute right-0 bottom-0 h-2.5 w-2.5 rounded-full bg-emerald-400 ring-2 ring-primary" />
              </div>
              <div>
                <p className="text-sm leading-none font-semibold">
                  Salora Salon
                </p>
                <p className="mt-1 text-[11px] text-white/80">
                  Booking Assistant • Online
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={() => {
                setIsOpen(false);
              }}
              aria-label="Close chat"
              className="rounded-full p-1 transition-colors hover:bg-primary-dark"
            >
              <MaterialIcon name="close" className="text-[20px]" />
            </button>
          </div>

          <div
            ref={threadRef}
            className="flex-1 space-y-3 overflow-y-auto bg-canvas p-4"
          >
            {messages.map((message, index) =>
              message.role === "agent" ? (
                <div
                  key={`${message.role}-${index.toString()}`}
                  className="flex items-start gap-2"
                >
                  <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary-light text-xs font-bold text-primary">
                    S
                  </div>
                  <p className="max-w-[80%] rounded-2xl rounded-tl-sm bg-agent-surface px-3.5 py-2.5 text-sm text-ink shadow-sm">
                    {message.text}
                  </p>
                </div>
              ) : (
                <div
                  key={`${message.role}-${index.toString()}`}
                  className="flex justify-end"
                >
                  <p className="max-w-[80%] rounded-2xl rounded-tr-sm bg-primary px-3.5 py-2.5 text-sm text-white shadow-sm">
                    {message.text}
                  </p>
                </div>
              ),
            )}
          </div>

          <form
            onSubmit={handleSubmit}
            className="flex shrink-0 items-center gap-2 border-t border-border bg-surface p-3"
          >
            <input
              type="text"
              value={inputText}
              onChange={(event) => {
                setInputText(event.target.value);
              }}
              placeholder="Type a message…"
              className="flex-1 rounded-full bg-agent-surface px-4 py-2 text-sm text-ink placeholder:text-ink-muted focus:outline-none"
            />
            <button
              type="submit"
              aria-label="Send message"
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary text-white transition-colors hover:bg-primary-dark"
            >
              <MaterialIcon name="send" className="text-[18px]" />
            </button>
          </form>
        </div>
      ) : null}

      <button
        id="chat-launcher"
        type="button"
        onClick={() => {
          setIsOpen((previous) => !previous);
        }}
        aria-label={isOpen ? "Close chat" : "Open booking chat"}
        className="flex h-14 w-14 items-center justify-center rounded-full bg-primary text-white shadow-xl transition-transform hover:scale-105 hover:bg-primary-dark active:scale-95"
      >
        <MaterialIcon
          name={isOpen ? "close" : "chat_bubble"}
          className="text-[24px]"
        />
      </button>
    </div>
  );
}

export default ChatWindow;

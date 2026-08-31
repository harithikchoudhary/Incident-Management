import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { Send, Trash2, Bot, User, Lightbulb } from "lucide-react";
import { api } from "../api/client.js";
import AnalysisCard from "../components/AnalysisCard.jsx";
import { Spinner } from "../components/ui.jsx";

const SUGGESTIONS = [
  "What happened when ML users could not log in to the MERC APK and Portal?",
  "How was the Kafka server low-disk-space incident resolved?",
  "Why were cases stuck at dedupe when the MAS Dedupe API failed?",
];

export default function ChatPage() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, loading]);

  const send = async (text) => {
    const message = (text ?? input).trim();
    if (!message || loading) return;

    const history = messages.map((m) => ({ role: m.role, content: m.content }));
    const userMsg = { role: "user", content: message };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const result = await api.chat(message, history);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: result.response,
          analysis: result.has_analysis ? result.analysis : null,
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `⚠️ ${err.message || "Something went wrong. Make sure the backend is running."}`,
          error: true,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const onKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return (
    <div className="flex h-full flex-col">
      <header className="flex items-center justify-between border-b border-slate-200 bg-white px-8 py-4">
        <div>
          <h2 className="text-xl font-bold text-slate-900">Incident Management Assistant</h2>
          <p className="text-sm text-slate-500">
            Ask about past incidents or get resolution recommendations — grounded only in ingested data.
          </p>
        </div>
        <button
          className="btn-secondary"
          onClick={() => setMessages([])}
          disabled={messages.length === 0}
        >
          <Trash2 className="h-4 w-4" /> Clear
        </button>
      </header>

      <div ref={scrollRef} className="flex-1 overflow-y-auto px-8 py-6">
        {messages.length === 0 && (
          <div className="mx-auto max-w-2xl">
            <div className="card p-6">
              <div className="mb-3 flex items-center gap-2 text-brand-600">
                <Lightbulb className="h-5 w-5" />
                <h3 className="font-semibold">How to use</h3>
              </div>
              <p className="mb-4 text-sm text-slate-600">
                All answers are based only on ingested historical incident data. Try one of these:
              </p>
              <div className="space-y-2">
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    onClick={() => send(s)}
                    className="flex w-full items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2.5 text-left text-sm text-slate-700 transition hover:border-brand-300 hover:bg-brand-50"
                  >
                    <Send className="h-3.5 w-3.5 flex-shrink-0 text-brand-500" />
                    {s}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        <div className="mx-auto max-w-3xl space-y-5">
          {messages.map((msg, i) => (
            <div
              key={i}
              className={`flex animate-fade-in gap-3 ${
                msg.role === "user" ? "flex-row-reverse" : ""
              }`}
            >
              <div
                className={`flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full ${
                  msg.role === "user" ? "bg-slate-700" : "bg-brand-600"
                }`}
              >
                {msg.role === "user" ? (
                  <User className="h-5 w-5 text-white" />
                ) : (
                  <Bot className="h-5 w-5 text-white" />
                )}
              </div>
              <div className={`max-w-[85%] ${msg.role === "user" ? "text-right" : ""}`}>
                <div
                  className={`inline-block rounded-2xl px-4 py-2.5 text-sm ${
                    msg.role === "user"
                      ? "bg-brand-600 text-white"
                      : msg.error
                        ? "border border-red-200 bg-red-50 text-red-700"
                        : "card text-slate-700"
                  }`}
                >
                  {msg.role === "user" ? (
                    <span className="whitespace-pre-wrap">{msg.content}</span>
                  ) : (
                    <div className="markdown text-left">
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    </div>
                  )}
                </div>
                {msg.analysis && (
                  <div className="text-left">
                    <AnalysisCard analysis={msg.analysis} />
                  </div>
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex animate-fade-in gap-3">
              <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full bg-brand-600">
                <Bot className="h-5 w-5 text-white" />
              </div>
              <div className="card flex items-center gap-2 px-4 py-3 text-sm text-slate-500">
                <Spinner className="h-4 w-4" /> Analyzing…
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="border-t border-slate-200 bg-white px-8 py-4">
        <div className="mx-auto flex max-w-3xl items-end gap-3">
          <textarea
            className="input max-h-32 min-h-[44px] resize-none py-2.5"
            rows={1}
            placeholder="Describe an incident or ask a question…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKeyDown}
          />
          <button className="btn-primary h-11 px-4" onClick={() => send()} disabled={loading || !input.trim()}>
            <Send className="h-4 w-4" /> Send
          </button>
        </div>
      </div>
    </div>
  );
}

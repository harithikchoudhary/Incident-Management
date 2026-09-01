import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";
import { Send, Trash2, Bot, User, Lightbulb, History, Plus, X, MessageSquare } from "lucide-react";
import { api } from "../api/client.js";
import AnalysisCard from "../components/AnalysisCard.jsx";
import { Spinner } from "../components/ui.jsx";

const SUGGESTIONS = [
  "What happened when ML users could not log in to the MERC APK and Portal?",
  "How was the Kafka server low-disk-space incident resolved?",
  "Why were cases stuck at dedupe when the MAS Dedupe API failed?",
];

const SESSION_STORAGE_KEY = "incident-chat-session-id";

export default function ChatPage() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [historyLoaded, setHistoryLoaded] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [sessions, setSessions] = useState([]);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const scrollRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, loading]);

  // Resume the last chat session (stored server-side in Postgres) on page load.
  useEffect(() => {
    const savedId = localStorage.getItem(SESSION_STORAGE_KEY);
    if (!savedId) {
      setHistoryLoaded(true);
      return;
    }
    api
      .getChatSessionMessages(savedId)
      .then((data) => {
        if (data.messages?.length) {
          setSessionId(savedId);
          setMessages(
            data.messages.map((m) => ({
              role: m.role,
              content: m.content,
              analysis: m.analysis || null,
            }))
          );
        } else {
          localStorage.removeItem(SESSION_STORAGE_KEY);
        }
      })
      .catch(() => localStorage.removeItem(SESSION_STORAGE_KEY))
      .finally(() => setHistoryLoaded(true));
  }, []);

  const send = async (text) => {
    const message = (text ?? input).trim();
    if (!message || loading) return;

    const history = messages.map((m) => ({ role: m.role, content: m.content }));
    const userMsg = { role: "user", content: message };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const result = await api.chat(message, history, sessionId);
      if (result.session_id && result.session_id !== sessionId) {
        setSessionId(result.session_id);
        localStorage.setItem(SESSION_STORAGE_KEY, result.session_id);
      }
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

  const clearChat = () => {
    if (sessionId) {
      api.deleteChatSession(sessionId).catch(() => {});
    }
    localStorage.removeItem(SESSION_STORAGE_KEY);
    setSessionId(null);
    setMessages([]);
  };

  // Start a fresh conversation without deleting the previous one from history.
  const startNewChat = () => {
    localStorage.removeItem(SESSION_STORAGE_KEY);
    setSessionId(null);
    setMessages([]);
    setShowHistory(false);
  };

  const loadSessions = async () => {
    setSessionsLoading(true);
    try {
      const data = await api.listChatSessions();
      const sorted = [...(data.sessions || [])].sort(
        (a, b) => new Date(b.updated_at) - new Date(a.updated_at)
      );
      setSessions(sorted);
    } catch {
      setSessions([]);
    } finally {
      setSessionsLoading(false);
    }
  };

  const openHistory = () => {
    setShowHistory(true);
    loadSessions();
  };

  const selectSession = async (id) => {
    if (id === sessionId) {
      setShowHistory(false);
      return;
    }
    try {
      const data = await api.getChatSessionMessages(id);
      setSessionId(id);
      localStorage.setItem(SESSION_STORAGE_KEY, id);
      setMessages(
        (data.messages || []).map((m) => ({
          role: m.role,
          content: m.content,
          analysis: m.analysis || null,
        }))
      );
    } finally {
      setShowHistory(false);
    }
  };

  const deleteSessionFromHistory = async (id, e) => {
    e.stopPropagation();
    try {
      await api.deleteChatSession(id);
    } catch {
      /* best-effort */
    }
    setSessions((prev) => prev.filter((s) => s.session_id !== id));
    if (id === sessionId) {
      localStorage.removeItem(SESSION_STORAGE_KEY);
      setSessionId(null);
      setMessages([]);
    }
  };

  const onKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return (
    <div className="relative flex h-full flex-col">
      <header className="flex flex-col gap-3 border-b border-slate-200 bg-white px-4 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-8">
        <div className="min-w-0">
          <h2 className="truncate text-lg font-bold text-slate-900 sm:text-xl">Incident Assistant</h2>
          <p className="text-xs text-slate-500 sm:text-sm">
            Ask about any past incident and get quick, accurate answers.
          </p>
        </div>
        <div className="flex flex-shrink-0 items-center gap-2">
          <button className="btn-secondary" onClick={openHistory}>
            <History className="h-4 w-4" /> <span className="hidden sm:inline">History</span>
          </button>
          <button className="btn-secondary" onClick={startNewChat}>
            <Plus className="h-4 w-4" /> <span className="hidden sm:inline">New Chat</span>
          </button>
          <button
            className="btn-secondary"
            onClick={clearChat}
            disabled={messages.length === 0}
            title="Delete this conversation"
          >
            <Trash2 className="h-4 w-4" /> <span className="hidden sm:inline">Clear</span>
          </button>
        </div>
      </header>

      <div ref={scrollRef} className="scroll-brand flex-1 overflow-y-auto px-4 py-6 sm:px-8">
        {historyLoaded && messages.length === 0 && (
          <div className="mx-auto max-w-3xl">
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

        <div className="mx-auto max-w-4xl space-y-5">
          {messages.map((msg, i) => (
            <div
              key={i}
              className={`flex animate-fade-in gap-3 ${
                msg.role === "user" ? "flex-row-reverse" : ""
              }`}
            >
              <div
                className={`flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full ${
                  msg.role === "user" ? "bg-ink-700" : "bg-brand-400"
                }`}
              >
                {msg.role === "user" ? (
                  <User className="h-5 w-5 text-white" />
                ) : (
                  <Bot className="h-5 w-5 text-ink-900" />
                )}
              </div>
              <div className={`max-w-[88%] sm:max-w-[85%] ${msg.role === "user" ? "text-right" : ""}`}>
                <div
                  className={`inline-block rounded-2xl px-4 py-2.5 text-sm shadow-sm ${
                    msg.role === "user"
                      ? "bg-ink-700 text-white"
                      : msg.error
                        ? "border border-red-200 bg-red-50 text-red-700"
                        : "card text-slate-700"
                  }`}
                >
                  {msg.role === "user" ? (
                    <span className="whitespace-pre-wrap">{msg.content}</span>
                  ) : (
                    <div className="markdown text-left">
                      <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]}>{msg.content}</ReactMarkdown>
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
              <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full bg-brand-400">
                <Bot className="h-5 w-5 text-ink-900" />
              </div>
              <div className="card flex items-center gap-2 px-4 py-3 text-sm text-slate-500">
                <Spinner className="h-4 w-4" /> Analyzing…
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="border-t border-slate-200 bg-white px-4 py-4 sm:px-8">
        <div className="mx-auto flex max-w-4xl items-end gap-2 sm:gap-3">
          <textarea
            className="input max-h-32 min-h-[44px] resize-none py-2.5"
            rows={1}
            placeholder="Describe an incident or ask a question…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKeyDown}
          />
          <button className="btn-primary h-11 flex-shrink-0 px-3 sm:px-4" onClick={() => send()} disabled={loading || !input.trim()}>
            <Send className="h-4 w-4" /> <span className="hidden sm:inline">Send</span>
          </button>
        </div>
      </div>

      {showHistory && (
        <div className="absolute inset-0 z-30 flex justify-end">
          <button
            aria-label="Close history"
            className="absolute inset-0 bg-ink-900/40"
            onClick={() => setShowHistory(false)}
          />
          <div className="scroll-brand relative flex h-full w-full max-w-sm flex-col overflow-y-auto border-l border-slate-200 bg-white shadow-xl animate-fade-in">
            <div className="flex items-center justify-between border-b border-slate-200 px-4 py-4">
              <h3 className="flex items-center gap-2 text-base font-bold text-slate-900">
                <History className="h-4 w-4 text-brand-600" /> Chat History
              </h3>
              <button
                className="rounded-lg p-1.5 text-slate-500 hover:bg-slate-100"
                onClick={() => setShowHistory(false)}
                aria-label="Close"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="border-b border-slate-200 p-3">
              <button className="btn-primary w-full justify-center" onClick={startNewChat}>
                <Plus className="h-4 w-4" /> New Chat
              </button>
            </div>

            <div className="flex-1 p-2">
              {sessionsLoading && (
                <div className="flex items-center justify-center gap-2 py-8 text-sm text-slate-500">
                  <Spinner className="h-4 w-4" /> Loading…
                </div>
              )}

              {!sessionsLoading && sessions.length === 0 && (
                <div className="px-3 py-8 text-center text-sm text-slate-500">
                  No previous conversations yet.
                </div>
              )}

              {!sessionsLoading &&
                sessions.map((s) => (
                  <div
                    key={s.session_id}
                    onClick={() => selectSession(s.session_id)}
                    className={`group mb-1 flex cursor-pointer items-start gap-2 rounded-lg px-3 py-2.5 transition hover:bg-brand-50 ${
                      s.session_id === sessionId ? "bg-brand-50 ring-1 ring-brand-300" : ""
                    }`}
                  >
                    <MessageSquare className="mt-0.5 h-4 w-4 flex-shrink-0 text-brand-500" />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium text-slate-800">
                        {s.title || s.preview || "Untitled conversation"}
                      </p>
                      {s.preview && s.title && (
                        <p className="truncate text-xs text-slate-500">{s.preview}</p>
                      )}
                      <p className="mt-0.5 text-[11px] text-slate-400">{formatRelativeTime(s.updated_at)}</p>
                    </div>
                    <button
                      className="flex-shrink-0 rounded p-1 text-slate-400 opacity-0 transition hover:bg-red-50 hover:text-red-600 group-hover:opacity-100"
                      onClick={(e) => deleteSessionFromHistory(s.session_id, e)}
                      aria-label="Delete conversation"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function formatRelativeTime(isoString) {
  if (!isoString) return "";
  const date = new Date(isoString.endsWith("Z") ? isoString : `${isoString}Z`);
  const diffMs = Date.now() - date.getTime();
  const diffMin = Math.round(diffMs / 60000);
  if (diffMin < 1) return "just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.round(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  const diffDay = Math.round(diffHr / 24);
  if (diffDay < 7) return `${diffDay}d ago`;
  return date.toLocaleDateString();
}

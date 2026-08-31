// Renders the raw "[timestamp] author: text" conversation string as a
// Google Chat-style threaded interface with avatars, grouping, and links.
import { useMemo } from "react";
import { MessageCircle, Users } from "lucide-react";

const AVATAR_COLORS = [
  "bg-rose-500",
  "bg-orange-500",
  "bg-amber-500",
  "bg-emerald-500",
  "bg-teal-500",
  "bg-cyan-600",
  "bg-blue-500",
  "bg-indigo-500",
  "bg-violet-500",
  "bg-fuchsia-500",
  "bg-pink-500",
  "bg-sky-500",
];

const BOT_HINTS = ["monitoring", "incident", "operations", "batch", "mod_", "l1_", "l2_"];

function hashString(str) {
  let h = 0;
  for (let i = 0; i < str.length; i += 1) {
    h = (h << 5) - h + str.charCodeAt(i);
    h |= 0;
  }
  return Math.abs(h);
}

function initials(name) {
  const parts = name.trim().split(/[\s_]+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

function isBot(name) {
  const n = name.toLowerCase();
  return BOT_HINTS.some((hint) => n.includes(hint));
}

function parseConversation(text) {
  const startRe = /^\[([^\]]+)\]\s+([^:]+):\s?(.*)$/;
  const messages = [];
  for (const line of text.split("\n")) {
    const match = line.match(startRe);
    if (match) {
      messages.push({ timestamp: match[1].trim(), author: match[2].trim(), text: match[3] });
    } else if (messages.length > 0) {
      messages[messages.length - 1].text += `\n${line}`;
    } else if (line.trim()) {
      messages.push({ timestamp: "", author: "System", text: line });
    }
  }
  return messages.map((msg) => ({ ...msg, text: msg.text.replace(/\s+$/, "") }));
}

const URL_RE = /((?:https?:\/\/|meet\.google\.com\/)[^\s]+)/g;

function renderText(text) {
  const nodes = [];
  let lastIndex = 0;
  let key = 0;
  let match;
  URL_RE.lastIndex = 0;
  while ((match = URL_RE.exec(text)) !== null) {
    if (match.index > lastIndex) nodes.push(text.slice(lastIndex, match.index));
    let url = match[0];
    let suffix = "";
    const trailing = url.match(/[.,)]+$/);
    if (trailing) {
      suffix = trailing[0];
      url = url.slice(0, -suffix.length);
    }
    const href = url.startsWith("http") ? url : `https://${url}`;
    nodes.push(
      <a
        key={`link-${key}`}
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="font-medium text-brand-600 underline decoration-brand-300 underline-offset-2 hover:text-brand-700"
      >
        {url}
      </a>
    );
    key += 1;
    if (suffix) nodes.push(suffix);
    lastIndex = match.index + match[0].length;
  }
  if (lastIndex < text.length) nodes.push(text.slice(lastIndex));
  return nodes;
}

export function ChatConversation({ text }) {
  const messages = useMemo(() => parseConversation(text || ""), [text]);

  const participants = useMemo(
    () => new Set(messages.map((m) => m.author)).size,
    [messages]
  );

  if (messages.length === 0) {
    return <p className="text-sm text-slate-500">No conversation data available.</p>;
  }

  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="flex items-center justify-between border-b border-slate-200 bg-gradient-to-r from-brand-50 to-slate-50 px-4 py-2.5">
        <div className="flex items-center gap-2">
          <MessageCircle className="h-4 w-4 text-brand-600" />
          <span className="text-sm font-semibold text-slate-700">Incident Bridge</span>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-slate-500">
          <Users className="h-3.5 w-3.5" />
          {participants} participant{participants === 1 ? "" : "s"} · {messages.length} messages
        </div>
      </div>

      <div className="max-h-[32rem] space-y-0.5 overflow-y-auto bg-slate-50 px-4 py-4">
        {messages.map((msg, i) => {
          const prev = messages[i - 1];
          const grouped = prev && prev.author === msg.author;
          const color = AVATAR_COLORS[hashString(msg.author) % AVATAR_COLORS.length];
          const bot = isBot(msg.author);
          return (
            <div key={i} className={`flex gap-3 ${grouped ? "mt-0.5" : "mt-4 first:mt-0"}`}>
              <div className="w-9 shrink-0">
                {!grouped && (
                  <div
                    className={`flex h-9 w-9 items-center justify-center rounded-full text-xs font-bold text-white shadow-sm ${color}`}
                  >
                    {initials(msg.author)}
                  </div>
                )}
              </div>

              <div className="min-w-0 flex-1">
                {!grouped && (
                  <div className="mb-1 flex items-center gap-2">
                    <span className="text-sm font-semibold text-slate-800">{msg.author}</span>
                    {bot && (
                      <span className="rounded bg-slate-200 px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-slate-500">
                        App
                      </span>
                    )}
                    {msg.timestamp && <span className="text-xs text-slate-400">{msg.timestamp}</span>}
                  </div>
                )}

                {msg.text.trim() ? (
                  <div className="inline-block max-w-full whitespace-pre-wrap break-words rounded-2xl rounded-tl-sm bg-white px-3.5 py-2 text-sm leading-relaxed text-slate-700 shadow-sm ring-1 ring-slate-200">
                    {renderText(msg.text)}
                  </div>
                ) : (
                  <div className="text-xs italic text-slate-400">
                    (no text — attachment or system message)
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default ChatConversation;

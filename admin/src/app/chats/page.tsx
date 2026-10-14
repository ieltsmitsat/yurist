"use client";

import { useEffect, useRef, useState } from "react";
import { format } from "date-fns";
import {
  getDialogs,
  getMessages,
  sendLawyerMessage,
  type Dialog,
  type ChatMessageItem as Message,
} from "@/lib/api";

export default function ChatsPage() {
  const [dialogs, setDialogs] = useState<Dialog[]>([]);
  const [selectedUserId, setSelectedUserId] = useState<number | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [replyText, setReplyText] = useState("");
  const [loadingDialogs, setLoadingDialogs] = useState(true);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [sending, setSending] = useState(false);
  const [showMessages, setShowMessages] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchDialogs();
    const timer = setInterval(() => {
      fetchDialogsSilently();
    }, 5000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (!selectedUserId) return;
    const timer = setInterval(() => {
      fetchMessagesSilently(selectedUserId);
    }, 4000);
    return () => clearInterval(timer);
  }, [selectedUserId]);

  const fetchDialogs = async () => {
    try {
      const data = await getDialogs();
      setDialogs(data || []);
    } catch (error) {
      console.error("Failed to fetch dialogs:", error);
    } finally {
      setLoadingDialogs(false);
    }
  };

  const fetchDialogsSilently = async () => {
    try {
      const data = await getDialogs();
      if (data) {
        setDialogs(data);
      }
    } catch (error) {
      console.debug("Silent dialog poll failed:", error);
    }
  };

  const fetchMessages = async (userId: number) => {
    setLoadingMessages(true);
    try {
      const data = await getMessages(userId);
      setMessages(data || []);
    } catch (error) {
      console.error("Failed to fetch messages:", error);
    } finally {
      setLoadingMessages(false);
    }
  };

  const fetchMessagesSilently = async (userId: number) => {
    try {
      const data = await getMessages(userId);
      if (data) {
        setMessages((prev) => {
          if (JSON.stringify(prev) !== JSON.stringify(data)) {
            return data;
          }
          return prev;
        });
      }
    } catch (error) {
      console.debug("Silent messages poll failed:", error);
    }
  };

  const handleSelectUser = (userId: number) => {
    setSelectedUserId(userId);
    setShowMessages(true);
    fetchMessages(userId);
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedUserId || !replyText.trim()) return;

    setSending(true);
    try {
      const newMessage = await sendLawyerMessage(selectedUserId, replyText);
      setMessages((prev) => [...prev, newMessage]);
      setReplyText("");
      setDialogs((prev) =>
        prev
          .map((d) =>
            d.user_id === selectedUserId
              ? {
                  ...d,
                  last_message: newMessage.text,
                  last_sender: "lawyer",
                  last_time: newMessage.created_at,
                  total_messages: d.total_messages + 1,
                }
              : d
          )
          .sort(
            (a, b) =>
              new Date(b.last_time || 0).getTime() - new Date(a.last_time || 0).getTime()
          )
      );
    } catch (error) {
      console.error("Error sending message:", error);
    } finally {
      setSending(false);
    }
  };

  const selectedDialog = dialogs.find((d) => d.user_id === selectedUserId);

  return (
    <div className="flex h-[calc(100vh-5rem)] bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
      {/* Left Pane: Dialogs List */}
      <div className={`border-r border-slate-200 flex-col shrink-0 ${showMessages ? "hidden md:flex md:w-80" : "flex w-full md:w-80"}`}>
        <div className="p-4 border-b border-slate-200 bg-slate-50/50">
          <h2 className="text-base font-semibold text-slate-900">✉️ Xabarlar</h2>
          <p className="text-xs text-slate-500 mt-0.5">{dialogs.length} ta suhbat</p>
        </div>
        <div className="flex-1 overflow-y-auto">
          {loadingDialogs ? (
            <div className="p-8 text-center text-slate-400">
              <div className="animate-spin h-6 w-6 border-3 border-indigo-500 border-t-transparent rounded-full mx-auto mb-2" />
              Yuklanmoqda...
            </div>
          ) : dialogs.length === 0 ? (
            <div className="p-8 text-center text-slate-400">Yozishmalar yo'q</div>
          ) : (
            dialogs.map((d) => (
              <div
                key={d.user_id}
                onClick={() => handleSelectUser(d.user_id)}
                className={`px-4 py-3.5 border-b border-slate-100 cursor-pointer transition-colors ${
                  selectedUserId === d.user_id
                    ? "bg-indigo-50 border-l-2 border-l-indigo-500"
                    : "hover:bg-slate-50"
                }`}
              >
                <div className="flex justify-between items-start mb-1">
                  <h3 className="font-medium text-slate-900 text-sm truncate">{d.full_name}</h3>
                  <span className="text-[10px] text-slate-400 whitespace-nowrap ml-2">
                    {d.last_time ? format(new Date(d.last_time), "HH:mm") : ""}
                  </span>
                </div>
                <p className="text-xs text-slate-500 truncate">
                  <span className="text-slate-400">
                    {d.last_sender === "user" ? "Mijoz" : d.last_sender === "bot" ? "Bot" : "Siz"}:
                  </span>{" "}
                  {d.last_message}
                </p>
                {d.total_messages > 0 && (
                  <span className="inline-block mt-1.5 text-[10px] bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded font-medium">
                    {d.total_messages} xabar
                  </span>
                )}
              </div>
            ))
          )}
        </div>
      </div>

      {/* Right Pane: Messages */}
      <div className={`flex-1 flex-col bg-slate-50 ${!showMessages ? "hidden md:flex" : "flex"}`}>
        {selectedUserId ? (
          <>
            {/* Header */}
            <div className="px-4 md:px-6 py-4 bg-white border-b border-slate-200 flex items-center gap-3 md:gap-4">
              <button
                onClick={() => setShowMessages(false)}
                className="md:hidden p-2 -ml-2 text-slate-500 hover:text-slate-700 rounded-full hover:bg-slate-100"
                aria-label="Back to messages"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M9.707 16.707a1 1 0 01-1.414 0l-6-6a1 1 0 010-1.414l6-6a1 1 0 011.414 1.414L5.414 9H17a1 1 0 110 2H5.414l4.293 4.293a1 1 0 010 1.414z" clipRule="evenodd" />
                </svg>
              </button>
              <div className="w-10 h-10 bg-indigo-100 rounded-full flex items-center justify-center text-indigo-600 font-semibold text-sm shrink-0">
                {selectedDialog?.full_name?.charAt(0) || "?"}
              </div>
              <div className="min-w-0">
                <h3 className="font-semibold text-slate-900 truncate">{selectedDialog?.full_name}</h3>
                <p className="text-xs text-slate-500 truncate">
                  TG: {selectedDialog?.telegram_id} • {selectedDialog?.phone_number || "Telefon yo'q"} • {selectedDialog?.lead_status}
                </p>
              </div>
            </div>

            {/* Message List */}
            <div className="flex-1 overflow-y-auto px-4 md:px-6 py-4 space-y-3">
              {loadingMessages ? (
                <div className="text-center text-slate-400 mt-10">
                  <div className="animate-spin h-6 w-6 border-3 border-indigo-500 border-t-transparent rounded-full mx-auto mb-2" />
                  Xabarlar yuklanmoqda...
                </div>
              ) : messages.length === 0 ? (
                <div className="text-center text-slate-400 mt-10">Xabar yo'q</div>
              ) : (
                messages.map((m) => {
                  const isLawyer = m.sender_type === "lawyer";
                  const isBot = m.sender_type === "bot";
                  return (
                    <div key={m.id} className={`flex ${isLawyer ? "justify-end" : "justify-start"}`}>
                      <div
                        className={`max-w-[85%] md:max-w-[65%] rounded-2xl px-4 py-2.5 shadow-sm ${
                          isLawyer
                            ? "bg-indigo-600 text-white rounded-br-md"
                            : isBot
                            ? "bg-blue-50 text-slate-800 border border-blue-100 rounded-bl-md"
                            : "bg-white text-slate-800 border border-slate-200 rounded-bl-md"
                        }`}
                      >
                        <div className={`text-[10px] font-semibold mb-1 ${isLawyer ? "text-indigo-200" : "text-slate-400"}`}>
                          {isLawyer ? "Advokat (Siz)" : isBot ? "Bot / AI" : "Mijoz"}
                        </div>
                        <div className="whitespace-pre-wrap text-sm leading-relaxed">{m.text}</div>
                        <div className={`text-[10px] text-right mt-1 ${isLawyer ? "text-indigo-200" : "text-slate-400"}`}>
                          {m.created_at ? format(new Date(m.created_at), "HH:mm") : ""}
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <div className="px-4 md:px-6 py-3 md:py-4 bg-white border-t border-slate-200">
              <form onSubmit={handleSendMessage} className="flex gap-2 md:gap-3">
                <input
                  type="text"
                  value={replyText}
                  onChange={(e) => setReplyText(e.target.value)}
                  placeholder="Mijozga xabar yozing..."
                  className="flex-1 rounded-xl border border-slate-300 px-3 md:px-4 py-2 md:py-2.5 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 placeholder:text-slate-400"
                  disabled={sending}
                />
                <button
                  type="submit"
                  disabled={sending || !replyText.trim()}
                  className="px-4 md:px-5 py-2 md:py-2.5 bg-indigo-600 text-white rounded-xl text-sm font-semibold hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors whitespace-nowrap"
                >
                  {sending ? "..." : "Yuborish →"}
                </button>
              </form>
            </div>
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-slate-400 p-6 text-center">
            <div className="text-5xl mb-4">💬</div>
            <p className="text-sm">Yozishmani ko'rish uchun chap tomondan mijozni tanlang</p>
          </div>
        )}
      </div>
    </div>
  );
}

import { useState, useRef, useEffect } from "react";
import { useParams } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Send } from "lucide-react";
import client from "../api/client";
import { ChatMessage } from "../types";

export default function ChatPage() {
  const { sessionId } = useParams();
  const [message, setMessage] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const queryClient = useQueryClient();

  const { data: messages = [] } = useQuery({
    queryKey: ["messages", sessionId],
    queryFn: async () => {
      const { data } = await client.get(`/api/chat/sessions/${sessionId}/messages`);
      return data as ChatMessage[];
    },
  });

  const sendMessage = useMutation({
    mutationFn: async () => {
      await client.post("/api/chat/ai", { session_id: Number(sessionId), message });
    },
    onSuccess: () => {
      setMessage("");
      queryClient.invalidateQueries({ queryKey: ["messages", sessionId] });
    },
  });

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold mb-4">Chat</h1>
      <div className="bg-white rounded shadow h-[500px] flex flex-col">
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {messages.map((m) => (
            <div key={m.id} className={`flex ${m.is_ai_generated ? "justify-start" : "justify-end"}`}>
              <div className={`max-w-[70%] px-4 py-2 rounded-lg ${m.is_ai_generated ? "bg-gray-100" : "bg-indigo-600 text-white"}`}>
                <p className="text-sm">{m.content}</p>
                {m.is_ai_generated && <span className="text-xs text-gray-400">AI Assistant</span>}
              </div>
            </div>
          ))}
          <div ref={bottomRef} />
        </div>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (message.trim()) sendMessage.mutate();
          }}
          className="flex gap-2 p-4 border-t"
        >
          <input
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Type a message..."
            className="flex-1 px-3 py-2 border rounded"
          />
          <button type="submit" disabled={sendMessage.isPending} className="bg-indigo-600 text-white px-4 py-2 rounded hover:bg-indigo-700">
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  );
}

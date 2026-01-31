import { useMemo, useState } from "react";
import { Loader2, Sparkles } from "lucide-react";

import { sendAiChat, getAiConfig, type AiMessage } from "@/api/ai";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";

interface AIAssistantDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function AIAssistantDialog({ open, onOpenChange }: AIAssistantDialogProps) {
  const config = useMemo(() => getAiConfig(), []);
  const [messages, setMessages] = useState<AiMessage[]>([
    {
      role: "assistant",
      content:
        "Ask for a report like: “orders for trousers last month” or “total revenue by customer last week”.",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSend = async () => {
    const trimmed = input.trim();
    if (!trimmed || loading) return;

    setError(null);
    setInput("");

    const nextMessages = [...messages, { role: "user", content: trimmed }];
    setMessages(nextMessages);
    setLoading(true);

    try {
      const response = await sendAiChat(nextMessages);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: response || "No response returned." },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to reach AI provider.");
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    setMessages([
      {
        role: "assistant",
        content:
          "Ask for a report like: “orders for trousers last month” or “total revenue by customer last week”.",
      },
    ]);
    setError(null);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="bottom-6 top-auto left-auto right-6 translate-x-0 translate-y-0 sm:max-w-[420px] w-[calc(100%-3rem)]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-blue-600" />
            AI Reports
          </DialogTitle>
        </DialogHeader>

        <div className="text-xs text-gray-500">
          Provider: {config.provider === "ollama" ? "Ollama (local)" : "Backend"}
        </div>

        <div className="mt-3 max-h-[50vh] overflow-y-auto rounded-lg border border-gray-200 bg-gray-50 p-3 space-y-3">
          {messages.map((message, index) => (
            <div
              key={`${message.role}-${index}`}
              className={`rounded-lg px-3 py-2 text-sm ${
                message.role === "user"
                  ? "ml-auto bg-blue-600 text-white"
                  : "bg-white text-gray-800 border border-gray-200"
              }`}
            >
              {message.content}
            </div>
          ))}
          {loading && (
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <Loader2 className="h-4 w-4 animate-spin" />
              Thinking...
            </div>
          )}
        </div>

        {error && (
          <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
            {error}
          </div>
        )}

        <div className="space-y-2">
          <Textarea
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Ask for a report..."
            className="min-h-[80px]"
            onKeyDown={(event) => {
              if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) {
                event.preventDefault();
                void handleSend();
              }
            }}
          />
          <div className="flex items-center justify-between">
            <Button type="button" variant="outline" onClick={handleClear}>
              Clear
            </Button>
            <Button type="button" onClick={handleSend} disabled={loading || !input.trim()}>
              {loading ? "Sending..." : "Send"}
            </Button>
          </div>
          <p className="text-xs text-gray-500">
            Tip: Press Cmd/Ctrl + Enter to send.
          </p>
        </div>
      </DialogContent>
    </Dialog>
  );
}

import { cn } from "@/lib/utils";

interface ChatMessageProps {
  role: "user" | "ai";
  content: string;
}

const ChatMessage = ({ role, content }: ChatMessageProps) => {
  return (
    <div className={cn("px-4 py-3", role === "ai" ? "border-l-2 border-l-primary bg-primary/5" : "bg-secondary/20")}>
      <span className="mb-1 block font-mono text-xs uppercase tracking-widest text-muted-foreground">
        {role === "ai" ? "VOICEOPS" : "YOU"}
      </span>
      <div className={cn("whitespace-pre-line text-sm leading-relaxed", role === "ai" ? "text-primary" : "text-foreground")}>
        {content}
      </div>
    </div>
  );
};

export default ChatMessage;

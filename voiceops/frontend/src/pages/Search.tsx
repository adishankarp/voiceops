import { useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import Layout from "@/components/Layout";
import ChatMessage from "@/components/ChatMessage";
import { Input } from "@/components/ui/input";
import { EmptyState, PageHeader, SectionHeading, SurfaceCard } from "@/components/ui/page-section";
import { ScrollArea } from "@/components/ui/scroll-area";
import { searchConversations, chat, type SearchResult } from "@/lib/api";

interface ChatMessageType {
  id: string;
  role: "user" | "ai";
  content: string;
}

const Search = () => {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [chatMessages, setChatMessages] = useState<ChatMessageType[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [hasSearched, setHasSearched] = useState(false);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [chatting, setChatting] = useState(false);

  const runSearch = useCallback(async (query: string) => {
    const trimmed = query.trim();
    setHasSearched(true);
    setSearchError(null);
    if (!trimmed) {
      setResults([]);
      return;
    }
    try {
      setSearching(true);
      const res = await searchConversations(trimmed);
      setResults(res || []);
    } catch (err) {
      console.error(err);
      setResults([]);
      setSearchError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setSearching(false);
    }
  }, []);

  const handleSearch = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      void runSearch(searchQuery);
    },
    [runSearch, searchQuery],
  );

  const handleChat = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!chatInput.trim()) return;
      const userMsg: ChatMessageType = { id: `u-${Date.now()}`, role: "user", content: chatInput };
      setChatMessages((prev) => [...prev, userMsg]);
      try {
        setChatting(true);
        const res = await chat(chatInput);
        const aiMsg: ChatMessageType = { id: `a-${Date.now()}`, role: "ai", content: res.answer };
        setChatMessages((prev) => [...prev, aiMsg]);
      } catch (err) {
        console.error(err);
        const aiMsg: ChatMessageType = {
          id: `a-${Date.now()}`,
          role: "ai",
          content: "Sorry, I couldn't process that question right now.",
        };
        setChatMessages((prev) => [...prev, aiMsg]);
      } finally {
        setChatting(false);
        setChatInput("");
      }
    },
    [chatInput],
  );

  return (
    <Layout>
      <PageHeader title="SEARCH + AI CHAT" description="Query conversations and ask questions" />

      <div className="space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-mono text-xs uppercase tracking-widest text-muted-foreground/70">TRY</span>
          {["price", "installation timeline", "warranty", "financing"].map((q) => (
            <button
              key={q}
              onClick={() => {
                setSearchQuery(q);
                void runSearch(q);
              }}
              className="border border-border bg-card px-3 py-1.5 font-mono text-xs text-muted-foreground transition-colors hover:border-primary/40 hover:text-primary"
            >
              {q}
            </button>
          ))}
        </div>

        <form onSubmit={handleSearch}>
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="search conversations... (try: price, objection, insurance)"
            className="bg-card border-border font-mono text-sm"
          />
        </form>
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(280px,360px)_minmax(0,1fr)]">
        <div className="space-y-3">
          <SectionHeading
            title="SEARCH RESULTS"
            description={searching ? "Searching conversations..." : hasSearched ? `${results.length} matches` : "Run a query to inspect transcripts."}
          />
          {searchError ? (
            <div className="rounded-md border border-destructive/50 bg-destructive/10 px-4 py-3 text-sm text-destructive">
              {searchError}
            </div>
          ) : null}
          {searching ? (
            <SurfaceCard contentClassName="space-y-2">
              {Array.from({ length: 4 }).map((_, index) => (
                <div key={index} className="space-y-2 border-b border-border/60 pb-3 last:border-b-0 last:pb-0">
                  <div className="h-3 w-24 animate-pulse bg-muted" />
                  <div className="h-8 w-full animate-pulse bg-muted" />
                </div>
              ))}
            </SurfaceCard>
          ) : !hasSearched ? (
            <EmptyState
              title="AWAITING QUERY"
              description="Search by objection, keyword, timeline, or customer concern."
            />
          ) : results.length === 0 && !searchError ? (
            <EmptyState
              title="NO RESULTS"
              description="Try broader keywords or search for a specific topic mentioned in the call."
            />
          ) : (
            <div className="space-y-2">
              {results.map((result) => (
                <button
                  key={result.conversation_id}
                  onClick={() => navigate(`/conversation/${result.conversation_id}`)}
                  className="block w-full border border-border bg-card px-4 py-3 text-left transition-colors hover:bg-secondary"
                >
                  <p className="truncate text-sm font-semibold text-foreground">{result.filename}</p>
                  <p className="mt-2 line-clamp-3 text-sm leading-relaxed text-muted-foreground">
                    "{result.snippet}"
                  </p>
                  <p className="mt-2 font-mono text-xs text-primary">score: {result.score}</p>
                </button>
              ))}
            </div>
          )}
        </div>

        <SurfaceCard title="AI CONVERSATION" contentClassName="flex min-h-[420px] flex-col p-0">
          <ScrollArea className="min-h-[320px] flex-1">
            <div className="space-y-3 p-4 sm:p-5">
              {chatMessages.length === 0 ? (
                <EmptyState
                  title="ASK A QUESTION"
                  description="Use the chat to summarize patterns, objections, and sentiment across your conversations."
                  className="min-h-[280px] border-0 bg-transparent px-0 py-0"
                />
              ) : (
                chatMessages.map((msg) => (
                  <ChatMessage key={msg.id} role={msg.role} content={msg.content} />
                ))
              )}
              {chatting ? (
                <div className="border-l-2 border-l-primary pl-4">
                  <span className="mb-1 block font-mono text-xs uppercase tracking-widest text-muted-foreground">
                    VOICEOPS
                  </span>
                  <div className="h-4 w-32 animate-pulse bg-muted" />
                </div>
              ) : null}
            </div>
          </ScrollArea>
          <form onSubmit={handleChat} className="border-t border-border p-4">
            <Input
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              placeholder="ask about objections, pain points, sentiment..."
              className="bg-background border-border font-mono text-sm"
            />
          </form>
        </SurfaceCard>
      </div>
    </Layout>
  );
};

export default Search;

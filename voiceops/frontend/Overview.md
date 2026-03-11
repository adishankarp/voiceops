

==================================================
1. PROJECT OVERVIEW
==================================================

**What VoiceOps is**  
VoiceOps is a single-tenant web app that ingests sales call audio (.wav/.mp3), transcribes it, extracts structured insights and a summary, embeds the transcript for search, and optionally detects cross-conversation patterns. Users browse conversations, inspect transcripts with a timeline, run semantic (and keyword) search, and ask natural-language questions over conversation context (RAG-style chat).

**What problem it solves**  
It turns raw call recordings into searchable, summarized, and queryable assets: find calls by topic, see pain points/objections/buying signals per call, and ask “what did we hear about X?” across the corpus without reading every transcript.

**Product category**  
Conversation intelligence / sales call analysis: post-call transcription, insight extraction, semantic search, and an AI assistant over your own calls. Closer to Gong/Chorus/Revenue.io (analysis + search + AI) than to generic meeting tools.

**One sentence**  
VoiceOps is a conversation-intelligence prototype that transcribes sales calls, extracts structured insights and summaries, embeds them for semantic search, and lets you query the corpus via an AI chat.

**One paragraph**  
VoiceOps accepts uploaded sales-call audio, runs a backend pipeline (Whisper transcription → OpenAI insights + summary → OpenAI embeddings), and stores each conversation as a JSON record with transcript, segments, insights, summary, and embedding. The frontend offers a dashboard of conversations with aggregate insight counts and LLM-derived cross-call patterns, a per-call detail view with timeline-to-transcript sync and sentiment, semantic (and keyword-fallback) search, and an AI chat that answers from either a single conversation or the top search results. It is built as a full-stack MVP with FastAPI, React, and file-based storage, aimed at demonstrating an end-to-end AI product rather than multi-tenant scale.

**What it resembles**  
A lightweight, single-tenant conversation-intelligence or sales-call analysis tool: Gong/Chorus-style analysis plus semantic search and a RAG copilot, implemented as an early-stage AI SaaS prototype.

---

==================================================
2. END-TO-END PRODUCT FLOW
==================================================

**A. User-facing flow**

1. **Entry** – User opens the app; Layout shows nav (Dashboard, Upload, Search, System). Default route is Dashboard.
2. **Dashboard** – PageHeader “DASHBOARD” and meta like “N CONVERSATIONS ANALYZED”. Left: “RECENT CONVERSATIONS” list (filename/date/status, objection/pain/signal counts, delete); right: “PATTERNS” (top 5 from GET /patterns or empty state), then “AGGREGATE INSIGHTS” (InsightCards + avg sentiment). Clicking a row goes to `/conversation/:id`.
3. **Upload** – “UPLOAD” page: drag-and-drop or file picker for .wav/.mp3. On drop: POST /conversations/upload → conversation_id + “uploaded”. UI shows FILE card (name, size, type), PROCESSING PIPELINE (PipelineSteps: Uploaded → Transcribing → Extracting → Complete with ✓/⚡/•), and polling GET /conversations/:id every 2s until status is “complete” or “failed”. On complete: “ANALYSIS COMPLETE. VIEW IT FROM THE DASHBOARD” and “Upload another file”.
4. **Conversation detail** – Back link, PageHeader with conversation title and date. Left column: AI SUMMARY (or “No summary”), CONVERSATION DETAILS (file, status, date, participants), PROCESSING STATUS (PipelineSteps, optional failedStage), SENTIMENT (0–100 + bar), INSIGHTS (grouped by type; each item clickable). Right: TIMELINE (events sorted by time; click → jump to transcript), TRANSCRIPT (segments in ScrollArea; highlighted segment scrolls into view and is styled). Timeline and insight clicks call `highlightSegmentAtTimestamp` → `findSegmentIdForTimestamp` (containment or fallback) → `setHighlightedSegment` → TranscriptViewer scroll + highlight.
5. **Search** – “SEARCH + AI CHAT”: suggested chips (e.g. price, installation timeline), text input, GET /search?query=… → list of results (filename, snippet, score); click result → conversation detail. No explicit “search” button; form submit runs search.
6. **AI chat** – Same page: chat input; submit POST /chat with question (and optional conversation_id). Backend uses search (or single conv) to build context, then OpenAI chat. Messages shown in ScrollArea; “VoiceOps” typing indicator while chatting.
7. **System** – “SYSTEM”: backend status (GET /), conversation list, pipeline health (healthy/degraded/offline from in-progress count), configured models (hardcoded labels), conversation status mix (complete vs in_progress counts).
8. **Delete** – Dashboard and detail: trash icon opens modal “DELETE CONVERSATION?”; confirm → DELETE /conversations/:id, modal closes, optional onDeleted callback (e.g. remove from dashboard list).

**B. Backend processing flow**

1. **POST /conversations/upload** – Validate .wav/.mp3, save file under UPLOAD_DIR as `{conversation_id}_{filename}`, create conversation record (id, filename, status=uploaded, transcript=[], segments=[], insights={}, summary=None, created_at=None, error=None), persist via storage.save_conversation, enqueue background task `process_conversation(conversation_id, path)`, return 202 + conversation_id.
2. **process_conversation** (background) – Load conversation, clear error. (1) status=transcribing, save; transcribe_audio (ffmpeg normalize → Whisper); store transcript + segments; log_decision; on failure set status=failed, error stage=transcription, save, return. (2) status=extracting, save; extract_insights(transcript) (OpenAI, structured JSON); store insights; log_decision; on failure set failed + stage=insights, return. (3) generate_summary(transcript) (OpenAI); store summary; log_decision; on failure set failed + stage=summary, return. (4) embed transcript[:4000] (OpenAI embeddings); store embedding; log_decision (embedding failure does not fail pipeline). (5) status=complete, save.
3. **GET /conversations** – list_conversations() (JSON file, sort by created_at desc), normalize status, return list[ConversationResponse].
4. **GET /conversations/:id** – get_conversation; 404 if missing; build_timeline(insights) → conv["timeline"]; return ConversationResponse.
5. **GET /search?query=** – search_conversations(query): optional query embedding; for each conversation compute keyword score and, if embedding exists, cosine similarity; combine; sort by score; return list of {conversation_id, filename, snippet, score}.
6. **POST /chat** – Validate question; if conversation_id then load that conversation as sole context and source; else search_conversations(question)[:3], load full convs, build context from transcript + insights (and excerpts for search hits); truncate context to 12k chars; OpenAI chat completion; log_decision; return answer + sources.
7. **GET /patterns** – list_conversations(); detect_patterns(conversations) (OpenAI over summaries + insight snippets, JSON patterns); return list[PatternResponse].
8. **DELETE /conversations/:id** – delete_conversation_by_id (rewrite JSON without that id).

---

==================================================
3. FEATURE INVENTORY
==================================================

**Dashboard**  
- Conversation list with title, date, duration, status badge, objection/pain/signal counts; click → detail. **Location:** `Dashboard.tsx`. **State:** Complete.  
- Aggregate insight counts (pain points, objections, buying signals, closing attempts, key moments). **Location:** `getAggregateInsightCounts` + InsightCard grid. **State:** Complete.  
- Average sentiment (0–100) with bar. **Location:** `computeAverageSentiment` + SurfaceCard. **State:** Complete.  
- Cross-call patterns (top 5) or empty state. **Location:** GET /patterns, PATTERNS section + SurfaceCard “TOP PATTERNS”. **State:** Complete.  
- Delete per conversation (trash → modal → DELETE). **Location:** DeleteConversationButton. **State:** Complete.  
- Loading skeletons and empty state when no conversations. **State:** Complete.

**Upload and processing**  
- Drag-and-drop and file picker for .wav/.mp3. **Location:** `Upload.tsx`. **State:** Complete.  
- Upload API call and display of file name/size/type. **State:** Complete.  
- Processing pipeline UI (Uploaded → Transcribing → Extracting → Complete) with icons (✓/⚡/•/✕) and pulse. **Location:** PipelineSteps. **State:** Complete.  
- Polling until complete/failed and “Analysis complete” CTA. **State:** Complete.  
- “Upload another file” reset. **State:** Complete.

**Conversation intelligence**  
- Per-call AI summary card. **Location:** ConversationDetail, “AI SUMMARY” SurfaceCard. **State:** Complete.  
- Structured insights (pain points, objections, buying signals, closing attempts, key moments) with timestamps. **Location:** ConversationDetail + getDisplayInsights + insightTypeLabels/Colors. **State:** Complete.  
- Timeline built from insights (pain_point, objection, buying_signal, closing_attempt, key_moment) with type, timestamp, label. **Location:** build_timeline in insights.py, Timeline component. **State:** Complete.  
- Timeline click → scroll transcript and highlight segment (containment or fallback). **Location:** findSegmentIdForTimestamp (endSeconds), TranscriptViewer scrollIntoView + refs, highlightSegmentAtTimestamp. **State:** Complete.  
- Insight item click → jump to timestamp in transcript. **State:** Complete.  
- Sentiment score (0–100) and bar with success/warning/destructive. **State:** Complete.  
- Processing status (PipelineSteps) with optional failed stage from conversation.error.stage. **State:** Complete.  
- Transcript viewer with segments (timestamp, speaker, text), ScrollArea, empty state. **State:** Complete.

**Search and retrieval**  
- Semantic search: query embedding + cosine similarity to conversation embeddings. **Location:** search.py (embed_text + _cosine_similarity). **State:** Complete.  
- Keyword fallback when embedding fails or no embeddings. **Location:** _score_occurrences over transcript + insight texts. **State:** Complete.  
- Snippet extraction around query match. **Location:** _best_snippet. **State:** Complete.  
- Search results list (filename, snippet, score) and click → conversation. **Location:** Search.tsx. **State:** Complete.  
- Suggested query chips. **State:** Complete.  
- Search loading state (skeletons). **State:** Complete.

**AI chat / copilot**  
- POST /chat with question and optional conversation_id. **Location:** chat route, Search page chat form. **State:** Complete.  
- Single-conversation mode: one conv as context. **State:** Complete.  
- Global mode: search(question)[:3], load convs, build context with excerpts for snippets. **State:** Complete.  
- System prompt constraining answers to context. **Location:** _SYSTEM_PROMPT. **State:** Complete.  
- Response with answer + sources (conversation_id, filename). **State:** Complete.  
- Chat UI (messages, input, typing indicator). **Location:** Search.tsx, ChatMessage. **State:** Complete.  
- No conversation_id passed from Search UI (always global RAG). **State:** Partial (API supports scoped chat; UI does not expose it).

**System / health**  
- Backend health GET /. **Location:** main.py. **State:** Complete.  
- System page: backend status, conversation count, avg sentiment, pipeline health (healthy/degraded/offline), configured models (hardcoded), status mix. **Location:** System.tsx. **State:** Complete.  
- Debug route GET /debug with route list. **Location:** main.py. **State:** Present (debug-only).

**UX / polish**  
- Shared Layout with nav and active state. **Location:** Layout, NavLink. **State:** Complete.  
- PageHeader (title, description, meta) with font-display. **State:** Complete.  
- SectionHeading, SurfaceCard, EmptyState, LoadingState (skeletons). **Location:** page-section.tsx. **State:** Complete.  
- Dashboard row hover (framer-motion whileHover). **State:** Complete.  
- Delete confirmation modal (backdrop, card, Cancel/Delete). **State:** Complete.  
- 404 route. **Location:** NotFound. **State:** Minimal.

**Admin / utility**  
- None beyond System and /debug; no auth, no user management, no orgs.

---

==================================================
4. AI / ML CAPABILITIES
==================================================

**Transcription**  
- **What:** Audio file → normalized 16 kHz mono WAV (ffmpeg) → Whisper → full text + segments (start, end, text).  
- **Where:** `transcription.py` (normalize_audio, WhisperProvider, transcribe_audio), `conversations.py` pipeline.  
- **Model/service:** Whisper (local, MODEL_NAMES["transcription"] default "base").  
- **Patterns:** Provider protocol, run_with_timeout (default 300s), TranscriptionError, log_decision.  
- **Strength:** Clear separation, timeout for long files. **Weakness:** Single process; no streaming; speaker labels not in segment output (speaker comes from backend segment shape if present).

**Insight extraction**  
- **What:** Transcript → structured JSON: pain_points, objections, buying_signals, closing_attempts, key_moments (with timestamps), sentiment_score 0–1.  
- **Where:** `insights.py` (EXTRACTION_SYSTEM, OpenAIInsightsProvider.extract, _parse_insights).  
- **Model:** OpenAI chat (default gpt-4o-mini).  
- **Patterns:** Pydantic Insights schema, retry_call (3 attempts, exponential backoff), markdown strip, backward compatibility for string-only lists, parse retry on ValidationError, ExternalServiceError.  
- **Strength:** Schema-driven output, retries, parse robustness. **Weakness:** Single provider in process (no swap at runtime beyond set_insights_provider).

**Summary generation**  
- **What:** Transcript → one short paragraph (2–4 sentences).  
- **Where:** `insights.py` (SUMMARY_SYSTEM, generate_summary).  
- **Model:** Same as insights (gpt-4o-mini) via get_insights_provider().  
- **Patterns:** Reuses provider client and retry; empty transcript returns ""; non-OpenAI provider returns "" with warning.  
- **Strength:** Consistent with insights stack. **Weakness:** Tied to OpenAI provider type check.

**Semantic embeddings**  
- **What:** Text (transcript truncated to 4000 chars) → vector (OpenAI embedding).  
- **Where:** `embeddings.py` (embed_text), `conversations.py` pipeline.  
- **Model:** text-embedding-3-small.  
- **Patterns:** retry_call + run_with_timeout composition, ExternalServiceError on failure; pipeline does not mark failed on embedding error (embedding optional).  
- **Strength:** Timeout + retries. **Weakness:** Module-level OpenAI() (no api_key at import can fail); no batching.

**Semantic search**  
- **What:** Query → optional query embedding; for each conversation, keyword score + cosine(query_embedding, conv.embedding); combined score; sort; return conversation_id, filename, snippet, score.  
- **Where:** `search.py` (KeywordSearchProvider).  
- **Patterns:** SearchProvider protocol; graceful fallback to keyword-only if embed_text fails; _best_snippet for display.  
- **Strength:** Hybrid semantic + keyword, no hard failure on embedding. **Weakness:** O(n) over all conversations; no vector index (faiss-cpu in requirements but unused).

**RAG / AI chat**  
- **What:** Question + optional conversation_id → context from one or multiple conversations (transcript + insights JSON, excerpts for search hits) → OpenAI chat → answer + sources.  
- **Where:** `chat.py` (_build_context, _render_conversation_context, POST "").  
- **Patterns:** Pydantic ChatRequest (question 1–4000 chars), retry_call, log_decision, empty-match and no-conv responses.  
- **Strength:** Clear RAG flow, context truncation (12k), source attribution. **Weakness:** No chunking or embedding-based retrieval; context is full transcript + insights; conversation_id not used from Search UI.

**Pattern detection**  
- **What:** All conversations’ summaries + insight snippets → one LLM call → top 5 patterns (label + description).  
- **Where:** `patterns.py` (_build_conversation_context, _build_user_message, detect_patterns), GET /patterns.  
- **Model:** gpt-4o-mini.  
- **Patterns:** Returns [] on no data or LLM/parse error; retry_call; markdown strip; 18k char cap.  
- **Strength:** Non-blocking for dashboard; graceful degradation. **Weakness:** No caching; runs on every GET /patterns.

**Timeline generation**  
- **What:** insights dict → sorted list of {type, timestamp, label} from pain_points, objections, buying_signals, closing_attempts, key_moments.  
- **Where:** `insights.build_timeline`, used in get_conversation_detail.  
- **Patterns:** Pure function; normalizes text/summary and timestamp; skips invalid entries.  
- **Strength:** Simple, deterministic. **Weakness:** Not an LLM step; derived from existing insights.

**Decision logging / observability**  
- **What:** Each pipeline stage (and chat) logs stage, model, input_preview, output_preview, conversation_id to conversation’s decision_log and persists.  
- **Where:** `decision_log.log_decision`, called from conversations pipeline and chat.  
- **Patterns:** 200-char previews, append to conv["decision_log"], save_conversation.  
- **Strength:** Audit trail and debugging. **Weakness:** Stored in same JSON as conversation; no separate log aggregation or sampling.

**Model/provider abstraction**  
- **What:** InsightsProvider protocol, set_insights_provider / get_insights_provider; TranscriptionProvider, set_transcription_provider; SearchProvider, set_search_provider.  
- **Where:** insights.py, transcription.py, search.py.  
- **Strength:** Testability and future provider swap. **Weakness:** Only insights has an alternate path (generate_summary with non-OpenAI); config is MODEL_NAMES + env (no per-tenant models).

---

==================================================
5. BACKEND ARCHITECTURE
==================================================

**Framework**  
FastAPI; CORS for localhost/8080/5173; exception handlers installed via `core.http.install_exception_handlers`.

**Route structure**  
- `main.py`: GET /, GET /debug; includes routers with prefix/tags: conversations (/conversations), search (/search), chat (/chat), patterns (/patterns).  
- `conversations.py`: POST /upload, GET "", GET /{id}, DELETE /{id}.  
- `search.py`: GET "" (query param).  
- `chat.py`: POST "" (body).  
- `patterns.py`: GET "".

**Services**  
- `conversations.py`: save_audio_upload (validation, UPLOAD_DIR).  
- `storage.py`: JSON file (DATA_DIR/conversations.json), fcntl lock, _load_all, save_conversation, get_conversation, list_conversations, delete_conversation_by_id.  
- `transcription.py`, `insights.py`, `embeddings.py`, `search.py`, `patterns.py`, `decision_log.py` as above.

**Storage**  
Single JSON file; read full list for list/get; write via tmp + replace; fcntl for cross-process safety. No DB, no migrations.

**Background processing**  
BackgroundTasks (FastAPI) + run_guarded_background_task (try/except, log). No Celery/Redis; process runs in-app. Survives restarts only if upload is re-sent.

**Resilience**  
- `retry_call`: attempts, retry_exceptions, operation_name, exponential backoff.  
- `run_with_timeout`: ThreadPoolExecutor, future.result(timeout).  
- Used in transcription (timeout), embeddings (timeout + retry), insights/summary/patterns/chat (retry).

**Error handling**  
AppError (code, message, status_code, details); ExternalServiceError(502); PipelineStageError; install_exception_handlers for RequestValidationError, AppError, HTTPException, Exception; request_id middleware; JSON error body with request_id.

**Logging**  
Standard logging; configure_logging in main; per-route and per-service logger.info/exception/warning.

**Response models**  
Pydantic in `schemas.py`: UploadConversationResponse, ConversationResponse (with nested segment/insights/timeline/error), DeleteConversationResponse, SearchResultResponse, PatternResponse, ChatRequest/ChatResponse (in chat.py). ConfigDict(extra="ignore") on response models.

**Deletion**  
DELETE /conversations/:id removes record from JSON; no removal of uploaded audio file or embeddings elsewhere.

**Configuration**  
dotenv; OPENAI_API_KEY, MODEL_NAMES (JSON env), UPLOAD_DIR, DATA_DIR; VOICEOPS_OPENAI_RETRY_ATTEMPTS, VOICEOPS_TRANSCRIPTION_TIMEOUT_SECONDS, VOICEOPS_EMBEDDING_TIMEOUT_SECONDS.

**Middleware**  
Single HTTP middleware: add request_id (header or uuid), set on response.

**Observability**  
decision_log per conversation; no metrics, tracing, or APM.

**Strengths**  
Structured errors and request_id; retries and timeouts; provider protocols; Pydantic schemas; pipeline stages and failure stages recorded.

**MVP-level**  
File storage; in-process background tasks; no queue; no auth; single JSON file for all data.

**For production scale**  
Replace file storage with a DB; use a queue (e.g. Celery/Redis) for pipeline jobs; add auth and tenant isolation; consider vector index (e.g. FAISS) for search; separate decision_log or sampling; add metrics and tracing.

---

==================================================
6. FRONTEND ARCHITECTURE
==================================================

**Framework / build**  
Vite 5, React 18, TypeScript; @vitejs/plugin-react-swc; path alias `@` → `src`.

**Routing**  
react-router-dom: / (Dashboard), /upload, /conversation/:id, /search, /system, * (NotFound).

**Component organization**  
- `pages/`: Dashboard, Upload, ConversationDetail, Search, System, NotFound.  
- `components/`: Layout, PipelineSteps, Timeline, TranscriptViewer, InsightCard, DeleteConversationButton, ChatMessage, NavLink; `components/ui/`: card, button, input, scroll-area, page-section (PageHeader, SectionHeading, SurfaceCard, EmptyState, LoadingState), sonner, toaster, tooltip, etc. (shadcn-style).

**Shared UI**  
page-section.tsx (SurfaceCard, PageHeader, SectionHeading, EmptyState, LoadingState); Radix-based primitives (ScrollArea, etc.); Tailwind + cn().

**API layer**  
`lib/api.ts`: BASE_URL from env; request<T>; getConversations, getPatterns, getBackendStatus, getConversation, uploadConversation (FormData), searchConversations, chat, deleteConversation (fetch). No React Query for these (QueryClient present but not used for these calls).

**Type system**  
`lib/api-types.ts`: Conversation, ConversationSegment, ConversationInsights, TimelineEvent, Pattern, SearchResult, ChatResponse, etc. `lib/conversation-utils.ts`: TranscriptSegmentView, InsightDisplayItem, getTranscriptSegments, findSegmentIdForTimestamp, getDisplayInsights, getAggregateInsightCounts, etc.

**State**  
useState/useEffect per page; no global store; cancellation via cancelled flag in useEffect.

**Loading**  
LoadingState (skeletons) on Dashboard and ConversationDetail; Search uses inline skeletons; Upload shows PipelineSteps and polling.

**Empty states**  
EmptyState component used for no conversations, no patterns, no insights, no results, no transcript, no timeline, no chat messages.

**Visual hierarchy**  
PageHeader (title + description + meta); SectionHeading (uppercase mono); SurfaceCard with optional title; consistent spacing and grids.

**Delete**  
DeleteConversationButton with modal (backdrop, card, Cancel/Delete, busy state).

**Timeline–transcript**  
Timeline and insight buttons call onJump(timestamp) → findSegmentIdForTimestamp (containment with endSeconds or fallback) → setHighlightedSegment; TranscriptViewer receives highlightedId, refs per segment, requestAnimationFrame + scrollIntoView({ behavior: "smooth", block: "center" }), highlight styles.

**Motion**  
framer-motion: Dashboard row whileHover; PipelineSteps animate-pulse for current step. No page transitions.

**Responsiveness**  
Tailwind breakpoints (sm, lg, xl); grid cols for dashboard and detail; Layout flex-wrap nav.

**Polish**  
Consistent cards and typography; clear empty/loading states; timeline–transcript sync and scroll; pipeline UI with icons. **MVP-like:** Search does not submit on Enter explicitly (form submit); conversation_id for chat not exposed in UI; some TypeScript strictness gaps (e.g. groupedInsights); React Query not used for server state.

---

==================================================
7. DESIGN SYSTEM / UI LANGUAGE
==================================================

**Color**  
CSS variables (HSL): --background (dark), --foreground, --card, --primary (yellow 50 100% 55%), --secondary, --muted, --destructive, --success, --warning, --border, etc. Tailwind theme extends these. Dark theme duplicates same palette.

**Typography**  
- Body: font-sans (Inter, system-ui).  
- Headings: Satoshi, Inter, system-ui (index.css + .font-display).  
- Mono/labels: Roboto Mono (label-mono, font-mono).  
- Tailwind: fontFamily sans (Inter), display (Satoshi), mono (Roboto Mono).

**Fonts**  
Satoshi (400, 500, 700) from /fonts/*.woff2; font-display: swap; PageHeader h1 uses font-display.

**Cards**  
SurfaceCard: Card + CardHeader (optional title/description) + CardContent; border-border, bg-card, shadow-none; contentClassName for inner padding.

**Buttons**  
Tailwind + border/background variants; no single Button usage in main flows (custom classNames). Delete modal: Cancel (border), Delete (destructive).

**Section headings**  
SectionHeading: uppercase mono label; optional description. SurfaceCard titles: font-mono uppercase tracking-widest text-muted-foreground.

**Loading**  
LoadingState: SurfaceCard with Skeleton rows (h-3 w-28, h-10 w-full). Search: custom skeleton list.

**Empty states**  
EmptyState: dashed border, card/40 background, centered text, title + description (mono + muted).

**Dashboard**  
Two-column grid (conversations | patterns + aggregate insights); cards and metrics in right column.

**Modals**  
Delete: fixed inset-0, backdrop, centered card, no Radix Dialog (custom div).

**Overall**  
Dark, high-contrast, yellow accent, mono labels; resembles a dev/dashboard or internal tool (e.g. Linear/Vercel dashboard style) more than a consumer product.

---

==================================================
8. TECHNOLOGY STACK
==================================================

**Frontend**  
React 18, TypeScript, Vite 5, react-router-dom 6, @vitejs/plugin-react-swc. Used for SPA and routing.

**Backend**  
FastAPI, uvicorn, pydantic, python-multipart. Used for API, validation, uploads.

**Styling**  
Tailwind 3, tailwindcss-animate, class-variance-authority, clsx, tailwind-merge (cn). Used for utility-first UI and theming.

**AI/ML**  
OpenAI (openai package): chat (insights, summary, patterns, chat), embeddings. Whisper (local): transcription. Used for all LLM and embedding features.

**Search**  
In-memory cosine similarity and keyword scoring in search.py. faiss-cpu in requirements but not used in code.

**Audio**  
ffmpeg (subprocess) for 16 kHz mono WAV; Whisper for speech-to-text.

**Data/storage**  
JSON file (conversations.json), python-dotenv. No DB.

**Utilities/DX**  
path (Node), @ alias, react-query (present but not used for main API calls), zod (in deps, minimal use in app).

**Animation**  
framer-motion (hover, pulse). tailwindcss-animate (accordion, pulse).

**Fonts/assets**  
Satoshi (woff2), Inter (system), Roboto Mono (mono). Served from public/fonts.

---

==================================================
9. ENGINEERING SIGNALS DEMONSTRATED
==================================================

- **Full-stack ownership:** One codebase from upload → pipeline → storage → API → dashboard, detail, search, chat, system, and delete; coherent data shapes and error handling.  
- **AI systems design:** Multi-stage pipeline with clear stages, failure stages, and optional embedding; RAG with context selection (single vs search); pattern detection as a separate, non-blocking endpoint.  
- **LLM reliability:** Retries, timeouts, structured outputs (Pydantic), parse retries and markdown stripping, ExternalServiceError, and graceful degradation (patterns [], search keyword fallback).  
- **Schema-driven outputs:** Insights, PatternResponse, ChatResponse, ConversationResponse defined and used end-to-end.  
- **Async processing:** BackgroundTasks + guarded task; frontend polling; no deadlocks.  
- **Search/retrieval:** Hybrid semantic + keyword, snippet extraction, and fallback when embeddings fail.  
- **Observability:** decision_log per conversation and per stage; request_id; structured logging.  
- **Product judgment:** Features aligned to conversation intelligence (insights, timeline, search, chat, patterns); no overbuild (e.g. no auth or multi-tenant).  
- **UX polish:** Loading/empty states, timeline–transcript sync, pipeline visualization, delete confirmation.  
- **Deployment readiness:** Env-based config, CORS, health/debug routes; file storage and in-process background jobs limit scalability.  
- **Modular services:** Provider protocols and set_*_provider for tests; services take minimal dependencies.  
- **Debugging maturity:** request_id, error codes, and decision_log support tracing; no distributed tracing or metrics.

---

==================================================
10. IMPLEMENTED DATA SHAPES / DOMAIN MODELS
==================================================

- **Conversation (backend storage / ConversationResponse):** id, filename, status, transcript, segments[], insights{}, summary, timeline[] (computed), created_at, error{stage, message}, embedding[], decision_log[] (not in response schema).  
- **Segment:** id?, start, end, speaker?, timestamp?, text.  
- **Insights:** pain_points, objections, buying_signals, closing_attempts, key_moments (items: text, timestamp?; key_moments: timestamp, summary), sentiment_score.  
- **Timeline event:** type, timestamp, label (from build_timeline).  
- **Pattern:** label, description (from detect_patterns).  
- **Search result:** conversation_id, filename, snippet, score.  
- **Chat response:** answer, sources[{conversation_id, filename}].  
- **Upload response:** conversation_id, status.  
- **Delete response:** status: "deleted".  
- **Status/Debug:** status string; routes list.

Flow: Upload creates minimal record; pipeline fills transcript, segments, insights, summary, embedding, decision_log; GET /conversations/:id adds timeline; list returns same shape without timeline; search returns search result shape; chat returns answer + sources; patterns returns list of pattern shape.

---

==================================================
11. API SURFACE
==================================================

- **GET /** – Health. Response: { status }. Frontend: getBackendStatus (System). Production-ready.  
- **GET /debug** – Debug. Response: { status, routes[] }. Frontend: none. Debug.  
- **POST /conversations/upload** – Upload audio. Body: multipart file. Response: conversation_id, status (202). Frontend: Upload. MVP (no auth, size limits only by server).  
- **GET /conversations** – List conversations. Response: list[ConversationResponse]. Frontend: Dashboard, System. MVP.  
- **GET /conversations/:id** – Get one conversation (with timeline). Response: ConversationResponse. Frontend: ConversationDetail, Upload polling. MVP.  
- **DELETE /conversations/:id** – Delete conversation. Response: { status: "deleted" }. Frontend: DeleteConversationButton. MVP.  
- **GET /search?query=** – Search. Query: query. Response: list[SearchResultResponse]. Frontend: Search. MVP.  
- **POST /chat** – RAG chat. Body: { question, conversation_id? }. Response: ChatResponse. Frontend: Search. MVP.  
- **GET /patterns** – Cross-call patterns. Response: list[PatternResponse]. Frontend: Dashboard. MVP.

---

==================================================
12. FILE / MODULE MAP
==================================================

**Backend**  
- `main.py` – App, CORS, exception handlers, router includes.  
- `config.py` – OPENAI_API_KEY, MODEL_NAMES, UPLOAD_DIR, DATA_DIR.  
- `schemas.py` – Pydantic request/response models.  
- `routes/conversations.py` – Upload, list, get, delete, process_conversation.  
- `routes/search.py` – GET search.  
- `routes/chat.py` – POST chat.  
- `routes/patterns.py` – GET patterns.  
- `services/storage.py` – JSON read/write, list/get/save/delete.  
- `services/conversations.py` – save_audio_upload.  
- `services/transcription.py` – Whisper + ffmpeg, transcribe_audio.  
- `services/insights.py` – extract_insights, generate_summary, build_timeline, provider.  
- `services/embeddings.py` – embed_text.  
- `services/search.py` – search_conversations, KeywordSearchProvider.  
- `services/patterns.py` – detect_patterns.  
- `services/decision_log.py` – log_decision.  
- `core/errors.py` – AppError, ExternalServiceError, PipelineStageError.  
- `core/resilience.py` – retry_call, run_with_timeout.  
- `core/background.py` – run_guarded_background_task.  
- `core/http.py` – install_exception_handlers, request_id middleware.

**Frontend**  
- `App.tsx` – Router, QueryClientProvider, TooltipProvider, Toaster, routes.  
- `index.html` / `main.tsx` – Entry.  
- `pages/Dashboard.tsx` – List, patterns, aggregate, delete.  
- `pages/Upload.tsx` – Drop zone, pipeline UI, polling.  
- `pages/ConversationDetail.tsx` – Summary, details, status, sentiment, insights, timeline, transcript.  
- `pages/Search.tsx` – Search + chat.  
- `pages/System.tsx` – Health, pipeline health, models, status mix.  
- `pages/NotFound.tsx` – 404.  
- `components/Layout.tsx` – Nav, main.  
- `components/PipelineSteps.tsx` – Pipeline UI.  
- `components/Timeline.tsx` – Timeline list, onJump.  
- `components/TranscriptViewer.tsx` – Segments, scroll, highlight.  
- `components/InsightCard.tsx` – Label + count.  
- `components/DeleteConversationButton.tsx` – Trash + modal.  
- `components/ChatMessage.tsx` – Chat bubble.  
- `components/ui/page-section.tsx` – PageHeader, SectionHeading, SurfaceCard, EmptyState, LoadingState.  
- `lib/api.ts` – Fetch wrappers.  
- `lib/api-types.ts` – TS interfaces.  
- `lib/conversation-utils.ts` – Segment/insight/timeline helpers, findSegmentIdForTimestamp.  
- `lib/utils.ts` – cn (tailwind-merge + clsx).  
- `index.css` – Fonts, Tailwind layers, base styles.  
- `tailwind.config.ts` – Theme, fontFamily, content.  
- `vite.config.ts` – Port 8080, alias, react plugin.

---

==================================================
13. WHAT MAKES VOICEOPS IMPRESSIVE
==================================================

- **End-to-end AI pipeline:** Single codebase from upload → Whisper → OpenAI insights/summary → embeddings → storage and search/chat, with clear stages and failure handling.  
- **Structured LLM outputs:** Pydantic-backed insights and patterns with retries and parse recovery; demonstrates production-minded LLM integration.  
- **Timeline–transcript sync:** Clicking timeline or insight scrolls and highlights the correct segment (with containment and fallback), showing attention to UX detail.  
- **Hybrid search:** Semantic + keyword with graceful fallback and snippet extraction, without requiring a vector DB.  
- **RAG chat with attribution:** Context from search or single conversation, source list, and context truncation.  
- **Cross-call patterns:** GET /patterns as a separate, non-blocking feature that degrades to [] on failure.  
- **Observability:** decision_log and request_id give a clear audit trail and debugging path.  
- **Consistent UI:** Shared cards, headings, empty/loading states, and pipeline visualization across pages.

---

==================================================
14. WHAT IS STILL MVP / NOT YET ENTERPRISE
==================================================

- **Storage:** Single JSON file; no DB, no migrations, no backups.  
- **Users:** No auth, no tenants, no permissions.  
- **Background jobs:** In-process; no queue; jobs lost on restart.  
- **Search scale:** O(n) in-memory; faiss-cpu present but unused.  
- **Cost control:** No rate limits, quotas, or model cost tracking.  
- **Analytics:** No usage or quality metrics.  
- **Deployment:** No Docker/CI described; CORS hardcoded to localhost.  
- **Tests:** No backend or frontend tests observed in the paths reviewed.  
- **Data lifecycle:** Uploaded audio files not deleted on conversation delete; decision_log grows unbounded.  
- **Chat scope:** conversation_id not exposed in Search UI; optional scoped chat underused.

---

==================================================
15. RESUME / PORTFOLIO POSITIONING
==================================================

**A. Three strong resume bullets**  
- Shipped an end-to-end conversation-intelligence pipeline (Whisper transcription, OpenAI insights/summary/embeddings, semantic + keyword search, RAG chat) with staged processing, retries, timeouts, and per-stage failure handling.  
- Implemented timeline-to-transcript playhead sync and segment highlighting using timestamp containment and scroll-into-view inside a custom ScrollArea, plus cross-call pattern detection via a dedicated LLM endpoint.  
- Built a FastAPI backend with Pydantic schemas, provider abstractions for transcription/insights/search, file-based storage with locking, request_id middleware, and structured error responses, and a React dashboard with shared design primitives and loading/empty states.

**B. Portfolio paragraph**  
VoiceOps is a full-stack conversation-intelligence prototype that ingests sales-call audio, transcribes it with Whisper, and runs an OpenAI-powered pipeline to extract structured insights (pain points, objections, buying signals, etc.), generate summaries, and embed transcripts for search. The app provides a dashboard with conversation list, aggregate metrics, and LLM-derived cross-call patterns; per-call detail views with a timeline and transcript that stay in sync on click; semantic search with keyword fallback; and an AI chat that answers from search results or a single conversation. The backend uses FastAPI, retries, timeouts, and decision logging; the frontend uses React, TypeScript, and a consistent card/empty-state system. It demonstrates end-to-end AI product execution from upload to search and chat.

**C. “What I built” (interviews)**  
“I built VoiceOps, a conversation-intelligence tool: you upload sales calls, it transcribes them with Whisper and runs an OpenAI pipeline to get structured insights, a summary, and embeddings. You can search across calls by meaning, open a call and jump from a timeline or insight into the right spot in the transcript, and ask questions in natural language; the backend does RAG over the top search hits or one conversation and returns answers with sources. I focused on a clear pipeline with retries and failure stages, timeline–transcript sync, and hybrid semantic plus keyword search.”

**D. “Why it’s technically interesting”**  
“It’s a single codebase that ties together local Whisper, multiple OpenAI APIs (chat for insights/summary/patterns, embeddings), and file-based storage into a pipeline with timeouts and retries, then exposes that via semantic search and RAG chat. The interesting parts are the structured LLM outputs with parse recovery, the hybrid search that degrades to keyword if embeddings fail, the timeline–transcript sync using segment containment and scroll-into-view, and the decision log for every AI step so you can debug and audit.”

---

==================================================
16. FINAL SUMMARY
==================================================

- **Technical verdict:** VoiceOps is a coherent, end-to-end MVP: clear pipeline, provider-style abstractions, retries and timeouts, Pydantic schemas, request_id and decision logging, and a React frontend with consistent layout and timeline–transcript sync. Storage, background execution, and scale are intentionally minimal; the codebase shows strong LLM-integration and product-stack judgment for a portfolio or early-stage build.  
- **Product verdict:** It delivers a complete loop (upload → analyze → browse → search → ask) with a defined conversation-intelligence feature set (insights, summary, timeline, patterns, semantic search, RAG chat). Scope is single-tenant and demo-ready, not yet enterprise.  
- **Strongest one-sentence product description:** VoiceOps is a conversation-intelligence prototype that turns sales-call audio into searchable, summarized conversations and lets you query them via semantic search and an AI chat.  
- **Strongest one-sentence engineer signal:** The project shows an engineer who can own a full-stack AI product—from pipeline design and LLM reliability (retries, schemas, fallbacks) to observable backend behavior and a consistent, detail-oriented frontend (timeline–transcript sync, pipeline UI, empty states)—with clear boundaries between what’s implemented and what’s left at MVP level.
import { useState, useCallback, useEffect } from "react";
import Layout from "@/components/Layout";
import PipelineSteps from "@/components/PipelineSteps";
import { PageHeader, SurfaceCard } from "@/components/ui/page-section";
import { cn } from "@/lib/utils";
import { uploadConversation, getConversation } from "@/lib/api";
import type { ProcessingStatus as ProcessingStatusType } from "@/lib/api-types";

const Upload = () => {
  const [isDragging, setIsDragging] = useState(false);
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [status, setStatus] = useState<ProcessingStatusType | null>(null);
  const [conversationId, setConversationId] = useState<string | null>(null);

  const startUpload = useCallback(async (file: File) => {
    setUploadedFile(file);
    setStatus("uploaded");
    try {
      const res = await uploadConversation(file);
      setConversationId(res.conversation_id);
    } catch (err) {
      console.error("Upload failed", err);
      setStatus(null);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file && (file.name.endsWith(".wav") || file.name.endsWith(".mp3"))) {
      void startUpload(file);
    }
  }, [startUpload]);

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) void startUpload(file);
  }, [startUpload]);

  useEffect(() => {
    if (!conversationId) return;
    let cancelled = false;

    const poll = async () => {
      try {
        const conv = await getConversation(conversationId);
        const newStatus = conv.status;
        if (newStatus) {
          setStatus(newStatus);
        }
        if (!cancelled && newStatus !== "complete") {
          setTimeout(poll, 2000);
        }
      } catch (err) {
        console.error(err);
        if (!cancelled) {
          setTimeout(poll, 2000);
        }
      }
    };

    void poll();

    return () => {
      cancelled = true;
    };
  }, [conversationId]);

  const formatSize = (bytes: number) => {
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <Layout>
      <div className="mx-auto flex w-full max-w-3xl flex-col gap-6">
        <PageHeader title="UPLOAD" description="Drag and drop an audio file to begin analysis" />

        {!uploadedFile ? (
          <label
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragging(true);
            }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
            className={cn(
              "flex min-h-[320px] cursor-pointer flex-col items-center justify-center border-2 border-dashed px-8 py-16 text-center transition-colors",
              isDragging
                ? "border-primary bg-primary/5"
                : "border-muted-foreground/40 hover:border-primary/60 hover:bg-primary/5",
            )}
          >
            <p className="font-mono text-base font-medium text-muted-foreground sm:text-lg">DROP .WAV OR .MP3 FILE HERE</p>
            <p className="mt-3 font-mono text-xs uppercase tracking-widest text-muted-foreground/60">OR CLICK TO BROWSE</p>
            <input
              type="file"
              accept=".wav,.mp3"
              onChange={handleFileSelect}
              className="hidden"
            />
          </label>
        ) : (
          <div className="grid gap-4">
            <SurfaceCard title="FILE">
              <div className="space-y-1 font-mono text-sm">
                <p><span className="text-muted-foreground">NAME: </span><span className="text-foreground">{uploadedFile.name}</span></p>
                <p><span className="text-muted-foreground">SIZE: </span><span className="text-foreground">{formatSize(uploadedFile.size)}</span></p>
                <p><span className="text-muted-foreground">TYPE: </span><span className="text-foreground">{uploadedFile.type || uploadedFile.name.split(".").pop()?.toUpperCase()}</span></p>
              </div>
            </SurfaceCard>

            <SurfaceCard title="PROCESSING PIPELINE">
              {status && <PipelineSteps status={status} variant="vertical" />}
            </SurfaceCard>

            {status === "complete" && (
              <SurfaceCard className="border-primary/30 bg-primary/5">
                <p className="font-mono text-sm text-primary">ANALYSIS COMPLETE. VIEW IT FROM THE DASHBOARD.</p>
              </SurfaceCard>
            )}

            <button
              onClick={() => {
                setUploadedFile(null);
                setStatus(null);
                setConversationId(null);
              }}
              className="w-fit font-mono text-xs text-muted-foreground transition-colors hover:text-foreground"
            >
              ← UPLOAD ANOTHER FILE
            </button>
          </div>
        )}
      </div>
    </Layout>
  );
};

export default Upload;

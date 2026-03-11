import { useState } from "react";
import { Trash2 } from "lucide-react";

import { deleteConversation } from "@/lib/api";
import { cn } from "@/lib/utils";

interface DeleteConversationButtonProps {
  id: string;
  onDeleted?: () => void;
}

const DeleteConversationButton = ({ id, onDeleted }: DeleteConversationButtonProps) => {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);

  const handleDelete = async () => {
    try {
      setBusy(true);
      await deleteConversation(id);
      setOpen(false);
      onDeleted?.();
    } catch (err) {
      console.error("Failed to delete conversation", err);
      setBusy(false);
    }
  };

  return (
    <>
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          setOpen(true);
        }}
        className="text-destructive hover:text-destructive/80"
        aria-label="Delete conversation"
      >
        <Trash2 size={16} />
      </button>

      {open && (
        <div
          className="fixed inset-0 z-40 flex items-center justify-center bg-background/80 backdrop-blur-sm"
          onClick={() => !busy && setOpen(false)}
        >
          <div
            className="w-full max-w-sm border border-border bg-card p-6 shadow-lg"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="mb-3 font-mono text-sm font-semibold tracking-widest text-foreground">
              DELETE CONVERSATION?
            </h3>
            <p className="mb-6 text-sm text-muted-foreground">
              This will permanently delete the conversation and all associated data.
            </p>
            <div className="flex justify-end gap-3">
              <button
                type="button"
                onClick={() => !busy && setOpen(false)}
                className={cn(
                  "px-3 py-1 text-xs font-mono",
                  "border border-border bg-card text-muted-foreground hover:text-foreground",
                )}
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleDelete}
                disabled={busy}
                className={cn(
                  "px-3 py-1 text-xs font-mono",
                  "bg-destructive text-destructive-foreground hover:bg-destructive/90 disabled:opacity-70",
                )}
              >
                {busy ? "Deleting..." : "Delete"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default DeleteConversationButton;


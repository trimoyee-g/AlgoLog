import { useMutation, useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { Mail } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { getDigestPreview, sendDigestNow } from "@/lib/api";

interface DigestDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function DigestDialog({ open, onOpenChange }: DigestDialogProps) {
  const { data, isLoading } = useQuery({
    queryKey: ["digest-preview"],
    queryFn: getDigestPreview,
    enabled: open,
  });

  const sendMutation = useMutation({
    mutationFn: sendDigestNow,
    onSuccess: () => toast.success("Digest sent — check your inbox."),
    onError: (err: Error) => toast.error(`Digest failed: ${err.message}`),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Your digest</DialogTitle>
          <DialogDescription>
            Exactly what the Sunday email would say.
          </DialogDescription>
        </DialogHeader>

        {isLoading ? (
          <div className="py-6 text-center text-sm text-muted-foreground">
            Building your digest…
          </div>
        ) : (
          <pre className="max-h-[50vh] overflow-auto whitespace-pre-wrap rounded-lg border border-border px-3 py-2.5 text-sm">
            {data?.body}
          </pre>
        )}

        <Button
          variant="outline"
          size="sm"
          className="self-start"
          onClick={() => sendMutation.mutate()}
          disabled={isLoading || sendMutation.isPending}
        >
          <Mail className="h-3.5 w-3.5" />
          {sendMutation.isPending ? "Sending…" : "Send over email"}
        </Button>
      </DialogContent>
    </Dialog>
  );
}

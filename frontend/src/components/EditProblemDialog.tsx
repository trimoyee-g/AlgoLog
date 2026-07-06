import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Trash2 } from "lucide-react";
import { toast } from "sonner";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { deleteProblem, updateProblem } from "@/lib/api";
import {
  latestAttempt,
  PLATFORMS,
  PLATFORM_LABELS,
  type Platform,
  type Problem,
} from "@/lib/types";

interface EditProblemDialogProps {
  problem: Problem | null;
  onOpenChange: (open: boolean) => void;
}

function EditForm({ problem, onOpenChange }: { problem: Problem; onOpenChange: (o: boolean) => void }) {
  const latest = latestAttempt(problem);
  const [title, setTitle] = useState(problem.title);
  const [url, setUrl] = useState(problem.url);
  const [platform, setPlatform] = useState<Platform>(problem.platform);
  const [tags, setTags] = useState(problem.tags ?? "");
  const [rating, setRating] = useState(String(latest?.rating ?? 3));
  const [solvedSelf, setSolvedSelf] = useState(latest ? String(latest.solved_self) : "true");
  const queryClient = useQueryClient();

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["overview"] });
    queryClient.invalidateQueries({ queryKey: ["problems"] });
  };

  const saveMutation = useMutation({
    mutationFn: () =>
      updateProblem(problem.id, {
        title: title.trim(),
        url: url.trim(),
        platform,
        tags: tags.trim() || null,
        rating: parseInt(rating, 10),
        solved_self: solvedSelf === "true",
      }),
    onSuccess: () => {
      toast.success("Saved");
      invalidate();
      onOpenChange(false);
    },
    onError: (err: Error) => toast.error(`Couldn't save: ${err.message}`),
  });

  const deleteMutation = useMutation({
    mutationFn: () => deleteProblem(problem.id),
    onSuccess: () => {
      toast.success("Deleted");
      invalidate();
      onOpenChange(false);
    },
    onError: (err: Error) => toast.error(`Couldn't delete: ${err.message}`),
  });

  return (
    <>
      <DialogHeader>
        <DialogTitle>Edit problem</DialogTitle>
      </DialogHeader>

      <div className="grid grid-cols-2 gap-3">
        <div className="col-span-2 space-y-1.5">
          <Label>Title</Label>
          <Input value={title} onChange={(e) => setTitle(e.target.value)} />
        </div>
        <div className="col-span-2 space-y-1.5">
          <Label>URL</Label>
          <Input value={url} onChange={(e) => setUrl(e.target.value)} />
        </div>
        <div className="space-y-1.5">
          <Label>Platform</Label>
          <Select value={platform} onValueChange={(v) => setPlatform(v as Platform)}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {PLATFORMS.map((p) => (
                <SelectItem key={p} value={p}>
                  {PLATFORM_LABELS[p]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1.5">
          <Label>Tags</Label>
          <Input value={tags} onChange={(e) => setTags(e.target.value)} />
        </div>
        <div className="space-y-1.5">
          <Label>Rating</Label>
          <Select value={rating} onValueChange={setRating}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {[1, 2, 3, 4, 5].map((n) => (
                <SelectItem key={n} value={String(n)}>
                  {n}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1.5">
          <Label>Solved myself</Label>
          <Select value={solvedSelf} onValueChange={setSolvedSelf}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="true">Yes</SelectItem>
              <SelectItem value="false">No</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <DialogFooter className="mt-2 justify-between sm:justify-between">
        <Button
          variant="destructive"
          size="sm"
          onClick={() => {
            if (confirm(`Delete "${problem.title}" and all its attempts?`)) {
              deleteMutation.mutate();
            }
          }}
          disabled={deleteMutation.isPending}
        >
          <Trash2 className="h-3.5 w-3.5" />
          Delete
        </Button>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            size="sm"
            onClick={() => saveMutation.mutate()}
            disabled={saveMutation.isPending}
          >
            {saveMutation.isPending ? "Saving…" : "Save"}
          </Button>
        </div>
      </DialogFooter>
    </>
  );
}

export function EditProblemDialog({ problem, onOpenChange }: EditProblemDialogProps) {
  return (
    <Dialog open={!!problem} onOpenChange={onOpenChange}>
      <DialogContent>
        {problem && (
          <EditForm key={problem.id} problem={problem} onOpenChange={onOpenChange} />
        )}
      </DialogContent>
    </Dialog>
  );
}

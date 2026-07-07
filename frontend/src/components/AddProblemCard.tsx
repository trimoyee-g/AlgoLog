import { useState, type FormEvent } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Star } from "lucide-react";
import { toast } from "sonner";
import { Card } from "@/components/ui/card";
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
import { cn } from "@/lib/utils";
import { addAttempt } from "@/lib/api";
import { PLATFORMS, PLATFORM_LABELS, type Platform } from "@/lib/types";

const emptyForm = {
  url: "",
  title: "",
  platform: "leetcode" as Platform,
  tags: "",
  rating: 3,
  solvedSelf: true,
  notes: "",
};

export function AddProblemCard({ bare, onSuccess }: { bare?: boolean; onSuccess?: () => void } = {}) {
  const [form, setForm] = useState(emptyForm);
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: addAttempt,
    onSuccess: () => {
      toast.success("Problem added");
      setForm(emptyForm);
      queryClient.invalidateQueries({ queryKey: ["overview"] });
      queryClient.invalidateQueries({ queryKey: ["problems"] });
      onSuccess?.();
    },
    onError: (err: Error) => {
      toast.error(`Failed to add problem: ${err.message}`);
    },
  });

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!form.url.trim() || !form.title.trim()) {
      toast.error("URL and title are required.");
      return;
    }
    mutation.mutate({
      url: form.url.trim(),
      title: form.title.trim(),
      platform: form.platform,
      tags: form.tags.trim() || null,
      rating: form.rating,
      solved_self: form.solvedSelf,
      notes: form.notes.trim() || null,
    });
  };

  const form_ = (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <Label htmlFor="url">Problem URL</Label>
          <Input
            id="url"
            placeholder="leetcode.com/problems/two-sum"
            value={form.url}
            onChange={(e) => setForm({ ...form, url: e.target.value })}
          />
        </div>
        <div className="space-y-1.5">
          <Label>Platform</Label>
          <Select
            value={form.platform}
            onValueChange={(v) => setForm({ ...form, platform: v as Platform })}
          >
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
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="title">Title</Label>
        <Input
          id="title"
          placeholder="Two sum"
          value={form.title}
          onChange={(e) => setForm({ ...form, title: e.target.value })}
        />
      </div>
      <div className="space-y-1.5">
        <Label>Difficulty (your own rating)</Label>
        <div className="flex items-center gap-1">
          {[1, 2, 3, 4, 5].map((n) => (
            <button
              key={n}
              type="button"
              onClick={() => setForm({ ...form, rating: n })}
              className="p-0.5"
              aria-label={`Rate ${n}`}
            >
              <Star
                className={cn(
                  "h-6 w-6",
                  n <= form.rating
                    ? "fill-amber-400 text-amber-400"
                    : "text-muted-foreground/40"
                )}
              />
            </button>
          ))}
        </div>
      </div>
      <div className="space-y-1.5">
        <Label>Did you solve it yourself?</Label>
        <div className="flex gap-2">
          {[
            { label: "Yes", value: true },
            { label: "No", value: false },
          ].map((opt) => (
            <Button
              key={opt.label}
              type="button"
              variant={form.solvedSelf === opt.value ? "default" : "outline"}
              className="flex-1"
              onClick={() => setForm({ ...form, solvedSelf: opt.value })}
            >
              {opt.label}
            </Button>
          ))}
        </div>
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="tags">Tags (comma-separated — used to find similar problems)</Label>
        <Input
          id="tags"
          placeholder="dp, binary-search, graph..."
          value={form.tags}
          onChange={(e) => setForm({ ...form, tags: e.target.value })}
        />
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="notes">Notes (optional)</Label>
        <textarea
          id="notes"
          rows={3}
          placeholder="What tripped you up / key insight..."
          value={form.notes}
          onChange={(e) => setForm({ ...form, notes: e.target.value })}
          className="flex w-full rounded-md border border-input bg-background/40 px-3 py-2 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
        />
      </div>
      <Button type="submit" disabled={mutation.isPending} className="w-full">
        <Plus className="h-4 w-4" />
        {mutation.isPending ? "Adding…" : "Add problem"}
      </Button>
    </form>
  );

  if (bare) return form_;

  return (
    <Card className="p-4">
      <div className="mb-3 text-sm font-medium text-muted-foreground">
        Log a new attempt
      </div>
      {form_}
    </Card>
  );
}

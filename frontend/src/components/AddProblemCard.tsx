import { useState, type FormEvent } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
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
import { addAttempt } from "@/lib/api";
import { PLATFORMS, PLATFORM_LABELS, type Platform } from "@/lib/types";

const emptyForm = {
  url: "",
  title: "",
  platform: "leetcode" as Platform,
  tags: "",
  rating: "3",
  solvedSelf: "true",
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
      rating: parseInt(form.rating, 10),
      solved_self: form.solvedSelf === "true",
    });
  };

  const form_ = (
    <form
      onSubmit={handleSubmit}
      className="grid grid-cols-2 gap-3 md:grid-cols-6 md:items-end"
    >
        <div className="col-span-2 space-y-1.5 md:col-span-2">
          <Label htmlFor="url">Problem URL</Label>
          <Input
            id="url"
            placeholder="leetcode.com/problems/two-sum"
            value={form.url}
            onChange={(e) => setForm({ ...form, url: e.target.value })}
          />
        </div>
        <div className="space-y-1.5 md:col-span-1">
          <Label htmlFor="title">Title</Label>
          <Input
            id="title"
            placeholder="Two sum"
            value={form.title}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
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
        <div className="space-y-1.5">
          <Label htmlFor="tags">Tags</Label>
          <Input
            id="tags"
            placeholder="dp, graph"
            value={form.tags}
            onChange={(e) => setForm({ ...form, tags: e.target.value })}
          />
        </div>
        <div className="space-y-1.5">
          <Label>Rating</Label>
          <Select
            value={form.rating}
            onValueChange={(v) => setForm({ ...form, rating: v })}
          >
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
        <div className="col-span-2 flex items-end gap-3 md:col-span-6">
          <div className="flex-1 space-y-1.5">
            <Label>Solved myself</Label>
            <Select
              value={form.solvedSelf}
              onValueChange={(v) => setForm({ ...form, solvedSelf: v })}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="true">Yes</SelectItem>
                <SelectItem value="false">No</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <Button type="submit" disabled={mutation.isPending} className="shrink-0">
            <Plus className="h-4 w-4" />
            {mutation.isPending ? "Adding…" : "Add problem"}
          </Button>
        </div>
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

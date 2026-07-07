import { Filter, Mail } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { PLATFORMS, PLATFORM_LABELS, type Platform } from "@/lib/types";

export interface FilterDraft {
  minRating: string;
  solvedSelf: string;
  platform: string;
  tag: string;
}

interface FiltersBarProps {
  draft: FilterDraft;
  onChange: (draft: FilterDraft) => void;
  onApply: () => void;
  onDigest: () => void;
  digestPending: boolean;
}

export function FiltersBar({
  draft,
  onChange,
  onApply,
  onDigest,
  digestPending,
}: FiltersBarProps) {
  return (
    <div className="flex flex-wrap items-center gap-2">
      <Select
        value={draft.minRating}
        onValueChange={(v) => onChange({ ...draft, minRating: v })}
      >
        <SelectTrigger className="w-[130px]">
          <SelectValue placeholder="Min. difficulty" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="any">Any difficulty</SelectItem>
          {[1, 2, 3, 4, 5].map((n) => (
            <SelectItem key={n} value={String(n)}>
              {n}+
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select
        value={draft.solvedSelf}
        onValueChange={(v) => onChange({ ...draft, solvedSelf: v })}
      >
        <SelectTrigger className="w-[130px]">
          <SelectValue placeholder="Solved myself" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="any">Any status</SelectItem>
          <SelectItem value="true">Solved myself</SelectItem>
          <SelectItem value="false">Needed help</SelectItem>
        </SelectContent>
      </Select>

      <Select
        value={draft.platform}
        onValueChange={(v) => onChange({ ...draft, platform: v })}
      >
        <SelectTrigger className="w-[140px]">
          <SelectValue placeholder="Platform" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="any">Any platform</SelectItem>
          {PLATFORMS.map((p) => (
            <SelectItem key={p} value={p}>
              {PLATFORM_LABELS[p as Platform]}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Input
        placeholder="Filter by tag"
        value={draft.tag}
        onChange={(e) => onChange({ ...draft, tag: e.target.value })}
        className="w-[160px]"
      />

      <Button variant="secondary" size="sm" onClick={onApply}>
        <Filter className="h-3.5 w-3.5" />
        Apply
      </Button>

      <div className="flex-1" />

      <Button variant="outline" size="sm" onClick={onDigest} disabled={digestPending}>
        <Mail className="h-3.5 w-3.5" />
        {digestPending ? "Sending…" : "Send weekly digest"}
      </Button>
    </div>
  );
}

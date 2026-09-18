"use client";

import { useState, type KeyboardEvent } from "react";
import { useTranslations } from "next-intl";
import { X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

// Usage scopes suggested to the admin; any other free-form value is accepted.
export const KNOWN_SERVICE_SCOPES = ["linto", "meet", "twake"];

interface ServiceScopesEditorProps {
  value: string[];
  onChange: (value: string[]) => void;
  disabled?: boolean;
}

// Editor for the client products a service is listed for. At least one scope
// stays selected: the last one cannot be removed.
export function ServiceScopesEditor({
  value,
  onChange,
  disabled = false,
}: ServiceScopesEditorProps) {
  const t = useTranslations("services");
  const [draft, setDraft] = useState("");

  const add = (raw: string) => {
    const scope = raw.trim().toLowerCase();
    if (!scope || value.includes(scope)) return;
    onChange([...value, scope]);
  };
  const remove = (scope: string) => {
    if (value.length <= 1) return;
    onChange(value.filter((s) => s !== scope));
  };
  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      add(draft);
      setDraft("");
    }
  };
  const suggestions = KNOWN_SERVICE_SCOPES.filter((s) => !value.includes(s));

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-2">
        {value.map((scope) => (
          <Badge
            key={scope}
            variant="default"
            className="gap-1 font-mono text-xs"
          >
            {scope}
            {!disabled && value.length > 1 && (
              <button
                type="button"
                className="ml-1 rounded-sm hover:text-destructive"
                onClick={() => remove(scope)}
                aria-label={`${t("scopes.remove")} ${scope}`}
              >
                <X className="h-3 w-3" />
              </button>
            )}
          </Badge>
        ))}
      </div>
      {!disabled && (
        <div className="flex flex-wrap items-center gap-2">
          {suggestions.map((scope) => (
            <Button
              key={scope}
              type="button"
              variant="outline"
              size="sm"
              onClick={() => add(scope)}
            >
              + {scope}
            </Button>
          ))}
          <Input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={t("placeholders.addScope")}
            className="h-8 w-48"
          />
        </div>
      )}
      <p className="text-xs text-muted-foreground">{t("scopes.hint")}</p>
    </div>
  );
}

"use client";

import { useTranslations } from "next-intl";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { TEMPLATE_ICONS } from "@/lib/template-icons";

interface TemplateIconSelectProps {
  value: string;
  onChange: (value: string) => void;
}

// Icon picker for a document template, previewed with the matching lucide icon.
export function TemplateIconSelect({
  value,
  onChange,
}: TemplateIconSelectProps) {
  const t = useTranslations("templates");

  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger>
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {TEMPLATE_ICONS.map(({ value: icon, preview: Preview }) => (
          <SelectItem key={icon} value={icon}>
            <span className="flex items-center gap-2">
              <Preview className="h-4 w-4" />
              {t(`icons.${icon}`)}
            </span>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

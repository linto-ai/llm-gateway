// Icons an admin can pick for a document template. The value is the Phosphor
// icon name rendered by LinTO Studio on the template card; the lucide
// component is only the admin-side preview of the same pictogram.
import {
  Briefcase,
  ClipboardList,
  FileText,
  GraduationCap,
  Handshake,
  Lightbulb,
  ListChecks,
  Megaphone,
  MessageSquareText,
  Newspaper,
  NotebookPen,
  Presentation,
  Scale,
  Users,
  type LucideIcon,
} from "lucide-react";

export const DEFAULT_TEMPLATE_ICON = "file-text";

export const TEMPLATE_ICONS: { value: string; preview: LucideIcon }[] = [
  { value: "file-text", preview: FileText },
  { value: "note-pencil", preview: NotebookPen },
  { value: "list-checks", preview: ListChecks },
  { value: "users-three", preview: Users },
  { value: "chat-circle-text", preview: MessageSquareText },
  { value: "presentation-chart", preview: Presentation },
  { value: "newspaper", preview: Newspaper },
  { value: "clipboard-text", preview: ClipboardList },
  { value: "briefcase", preview: Briefcase },
  { value: "scales", preview: Scale },
  { value: "handshake", preview: Handshake },
  { value: "graduation-cap", preview: GraduationCap },
  { value: "lightbulb", preview: Lightbulb },
  { value: "megaphone", preview: Megaphone },
];

export function getTemplateIconPreview(
  icon: string | null | undefined,
): LucideIcon {
  const entry = TEMPLATE_ICONS.find((item) => item.value === icon);
  return entry ? entry.preview : FileText;
}

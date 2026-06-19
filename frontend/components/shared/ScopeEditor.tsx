'use client';

import { useState, KeyboardEvent } from 'react';
import { Plus, X, Globe } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';

export interface ScopeValue {
  organizationIds: string[];
  userIds: string[];
}

interface ScopeEditorProps {
  value: ScopeValue;
  onChange: (value: ScopeValue) => void;
  disabled?: boolean;
  /** Labels / hints (pass translated strings). */
  orgLabel?: string;
  userLabel?: string;
  orgPlaceholder?: string;
  userPlaceholder?: string;
  /** Shown when both lists are empty (resource is global / system-wide). */
  globalHint?: string;
  className?: string;
}

/**
 * Free-text chip editor for the multi-scope access lists (organizations + users).
 *
 * Org/user IDs are external free-form identifiers (e.g. Studio Mongo ObjectIds),
 * so there is no dropdown of known values - the admin types/pastes an ID and
 * presses Enter (or the + button) to add it. When both lists are empty the
 * resource is global (visible to everyone).
 */
export function ScopeEditor({
  value,
  onChange,
  disabled = false,
  orgLabel = 'Organizations',
  userLabel = 'Users',
  orgPlaceholder = 'Add an organization ID…',
  userPlaceholder = 'Add a user ID…',
  globalHint = 'No restrictions — visible to everyone (global).',
  className,
}: ScopeEditorProps) {
  const isGlobal = value.organizationIds.length === 0 && value.userIds.length === 0;

  return (
    <div className={className}>
      <ChipList
        label={orgLabel}
        placeholder={orgPlaceholder}
        items={value.organizationIds}
        disabled={disabled}
        onAdd={(id) =>
          onChange({ ...value, organizationIds: addUnique(value.organizationIds, id) })
        }
        onRemove={(id) =>
          onChange({ ...value, organizationIds: value.organizationIds.filter((x) => x !== id) })
        }
      />
      <div className="mt-4">
        <ChipList
          label={userLabel}
          placeholder={userPlaceholder}
          items={value.userIds}
          disabled={disabled}
          onAdd={(id) => onChange({ ...value, userIds: addUnique(value.userIds, id) })}
          onRemove={(id) =>
            onChange({ ...value, userIds: value.userIds.filter((x) => x !== id) })
          }
        />
      </div>
      {isGlobal && (
        <p className="mt-3 flex items-center gap-2 text-sm text-muted-foreground">
          <Globe className="h-4 w-4" />
          {globalHint}
        </p>
      )}
    </div>
  );
}

function addUnique(list: string[], raw: string): string[] {
  const value = raw.trim();
  if (!value || list.includes(value)) return list;
  return [...list, value];
}

interface ChipListProps {
  label: string;
  placeholder: string;
  items: string[];
  disabled: boolean;
  onAdd: (id: string) => void;
  onRemove: (id: string) => void;
}

function ChipList({ label, placeholder, items, disabled, onAdd, onRemove }: ChipListProps) {
  const [draft, setDraft] = useState('');

  const commit = () => {
    if (draft.trim()) {
      onAdd(draft);
      setDraft('');
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      commit();
    }
  };

  return (
    <div>
      <Label className="text-sm">{label}</Label>
      {items.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-2">
          {items.map((id) => (
            <Badge key={id} variant="secondary" className="gap-1 font-mono text-xs">
              {id}
              {!disabled && (
                <button
                  type="button"
                  className="ml-1 rounded-sm hover:text-destructive"
                  onClick={() => onRemove(id)}
                  aria-label={`Remove ${id}`}
                >
                  <X className="h-3 w-3" />
                </button>
              )}
            </Badge>
          ))}
        </div>
      )}
      <div className="mt-2 flex gap-2">
        <Input
          value={draft}
          placeholder={placeholder}
          disabled={disabled}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <Button type="button" variant="outline" size="icon" disabled={disabled || !draft.trim()} onClick={commit}>
          <Plus className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}

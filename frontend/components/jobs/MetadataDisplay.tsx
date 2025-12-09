'use client';

import { useTranslations } from 'next-intl';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import {
  User,
  Tag,
  CheckSquare,
  Key,
  ThumbsUp,
  ThumbsDown,
  Minus,
  FileText,
  Calendar,
  Globe,
  Hash,
} from 'lucide-react';
import { parsePlaceholder } from '@/types/document-template';

interface MetadataDisplayProps {
  metadata: Record<string, any>;
}

/**
 * Display extracted metadata from a job result.
 * Renders different field types appropriately (strings, arrays, sentiment badges).
 * Skips internal fields (those starting with _).
 */
// Standard placeholders provided by the system - not extracted metadata
const STANDARD_PLACEHOLDERS = [
  'output',
  'job_id',
  'job_date',
  'service_name',
  'flavor_name',
  'organization_name',
  'generated_at',
];

export function MetadataDisplay({ metadata }: MetadataDisplayProps) {
  const t = useTranslations('metadata');

  if (!metadata || Object.keys(metadata).length === 0) {
    return null;
  }

  // Filter out internal fields (starting with _) and standard placeholders
  const displayFields = Object.entries(metadata).filter(
    ([key]) => !key.startsWith('_') && !STANDARD_PLACEHOLDERS.includes(key)
  );

  if (displayFields.length === 0) {
    return null;
  }

  // Get sentiment variant for badge styling
  const getSentimentVariant = (sentiment: string): 'default' | 'destructive' | 'secondary' | 'outline' => {
    switch (sentiment?.toLowerCase()) {
      case 'positive':
        return 'default';
      case 'negative':
        return 'destructive';
      case 'neutral':
        return 'secondary';
      case 'mixed':
        return 'outline';
      default:
        return 'secondary';
    }
  };

  // Get sentiment icon
  const getSentimentIcon = (sentiment: string) => {
    switch (sentiment?.toLowerCase()) {
      case 'positive':
        return <ThumbsUp className="h-3 w-3" />;
      case 'negative':
        return <ThumbsDown className="h-3 w-3" />;
      default:
        return <Minus className="h-3 w-3" />;
    }
  };

  // Format an array item - handles objects like {task: "...", assignee: "..."}
  const formatArrayItem = (item: any): string => {
    if (item === null || item === undefined) {
      return '-';
    }
    if (typeof item === 'object') {
      // Format object as "value1 - value2 - value3"
      const values = Object.values(item).filter(v => v !== null && v !== undefined);
      if (values.length === 0) return '-';
      return values.map(v => String(v)).join(' - ');
    }
    return String(item);
  };

  // Render field value based on its type and key
  const renderFieldValue = (key: string, value: any) => {
    // Parse key to get the field name (without description)
    const { name: fieldName } = parsePlaceholder(key);

    // Handle null/undefined
    if (value === null || value === undefined) {
      return <span className="text-muted-foreground italic">-</span>;
    }

    // Handle sentiment specially
    if (fieldName === 'sentiment' && typeof value === 'string') {
      return (
        <Badge variant={getSentimentVariant(value)} className="gap-1">
          {getSentimentIcon(value)}
          {t(`sentimentValues.${value.toLowerCase()}`, { defaultValue: value })}
        </Badge>
      );
    }

    // Handle arrays (participants, topics, action_items, key_points)
    if (Array.isArray(value)) {
      if (value.length === 0) {
        return <span className="text-muted-foreground italic">-</span>;
      }

      // Use badges for short items like participants and topics
      if (fieldName === 'participants' || fieldName === 'topics') {
        return (
          <div className="flex flex-wrap gap-1">
            {value.map((item, index) => (
              <Badge key={index} variant={fieldName === 'participants' ? 'secondary' : 'outline'}>
                {fieldName === 'participants' && <User className="h-3 w-3 mr-1" />}
                {fieldName === 'topics' && <Tag className="h-3 w-3 mr-1" />}
                {String(item)}
              </Badge>
            ))}
          </div>
        );
      }

      // Use list for longer items like action_items, key_points, decisions
      return (
        <ul className="list-disc list-inside space-y-1">
          {value.map((item, index) => (
            <li key={index} className="text-sm">
              {formatArrayItem(item)}
            </li>
          ))}
        </ul>
      );
    }

    // Handle numbers
    if (typeof value === 'number') {
      return <span className="font-mono">{value.toLocaleString()}</span>;
    }

    // Handle strings
    return <span>{String(value)}</span>;
  };

  // Get icon for field (uses parsed name without description)
  const getFieldIcon = (key: string) => {
    const { name } = parsePlaceholder(key);
    switch (name) {
      case 'title':
        return <FileText className="h-4 w-4" />;
      case 'participants':
        return <User className="h-4 w-4" />;
      case 'topics':
        return <Tag className="h-4 w-4" />;
      case 'action_items':
      case 'actionItems':
        return <CheckSquare className="h-4 w-4" />;
      case 'key_points':
      case 'keyPoints':
        return <Key className="h-4 w-4" />;
      case 'date':
        return <Calendar className="h-4 w-4" />;
      case 'language':
        return <Globe className="h-4 w-4" />;
      case 'word_count':
      case 'wordCount':
        return <Hash className="h-4 w-4" />;
      default:
        return null;
    }
  };

  // Get translated label for field (uses parsed name without description)
  const getFieldLabel = (key: string) => {
    const { name } = parsePlaceholder(key);
    // Convert snake_case to camelCase for i18n lookup
    const camelKey = name.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase());
    return t(camelKey, { defaultValue: name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()) });
  };

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-lg">{t('title')}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Title - prominent display */}
        {metadata.title && (
          <div>
            <Label className="text-sm text-muted-foreground flex items-center gap-1">
              {getFieldIcon('title')}
              {getFieldLabel('title')}
            </Label>
            <p className="font-semibold text-lg mt-1">{metadata.title}</p>
          </div>
        )}

        {/* Summary */}
        {metadata.summary && (
          <div>
            <Label className="text-sm text-muted-foreground">{getFieldLabel('summary')}</Label>
            <p className="mt-1">{metadata.summary}</p>
          </div>
        )}

        {/* Other fields in grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {displayFields
            .filter(([key]) => key !== 'title' && key !== 'summary')
            .map(([key, value]) => (
              <div key={key}>
                <Label className="text-sm text-muted-foreground flex items-center gap-1">
                  {getFieldIcon(key)}
                  {getFieldLabel(key)}
                </Label>
                <div className="mt-1">{renderFieldValue(key, value)}</div>
              </div>
            ))}
        </div>
      </CardContent>
    </Card>
  );
}

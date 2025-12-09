'use client';

import { useTranslations } from 'next-intl';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { AlertCircle, Tag, Lightbulb } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import type { JobCategorization } from '@/types/job';

interface CategorizationDisplayProps {
  categorization: JobCategorization;
}

/**
 * Display categorization results from a job.
 * Shows matched tags with confidence scores, suggested tags, and handles error states.
 */
export function CategorizationDisplay({ categorization }: CategorizationDisplayProps) {
  const t = useTranslations('jobs.categorization');

  // Handle error state
  if (categorization._categorization_error) {
    return (
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-lg">{t('title')}</CardTitle>
        </CardHeader>
        <CardContent>
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              {t('error')}: {categorization._categorization_error}
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    );
  }

  const hasMatchedTags = categorization.matched_tags && categorization.matched_tags.length > 0;
  const hasSuggestedTags = categorization.suggested_tags && categorization.suggested_tags.length > 0;

  // Don't render if no tags at all
  if (!hasMatchedTags && !hasSuggestedTags) {
    return (
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-lg">{t('title')}</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground text-sm">{t('noTags')}</p>
        </CardContent>
      </Card>
    );
  }

  // Get badge variant based on confidence level
  const getConfidenceVariant = (confidence: number): 'default' | 'secondary' | 'outline' => {
    if (confidence >= 0.8) return 'default';
    if (confidence >= 0.5) return 'secondary';
    return 'outline';
  };

  // Format confidence as percentage
  const formatConfidence = (confidence: number): string => {
    return `${Math.round(confidence * 100)}%`;
  };

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-lg">{t('title')}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Matched Tags */}
        {hasMatchedTags && (
          <div>
            <div className="flex items-center gap-1 text-sm text-muted-foreground mb-2">
              <Tag className="h-4 w-4" />
              <span>{t('matchedTags')}</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {categorization.matched_tags!.map((tag, index) => (
                <Badge
                  key={index}
                  variant={getConfidenceVariant(tag.confidence)}
                  className="gap-1"
                >
                  {tag.name}
                  <span className="text-xs opacity-75">
                    ({formatConfidence(tag.confidence)})
                  </span>
                </Badge>
              ))}
            </div>
          </div>
        )}

        {/* Suggested Tags */}
        {hasSuggestedTags && (
          <div>
            <div className="flex items-center gap-1 text-sm text-muted-foreground mb-2">
              <Lightbulb className="h-4 w-4" />
              <span>{t('suggestedTags')}</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {categorization.suggested_tags!.map((tag, index) => (
                <Badge
                  key={index}
                  variant="outline"
                  className="gap-1 border-dashed"
                >
                  {tag.name}
                  <span className="text-xs opacity-75">
                    ({formatConfidence(tag.confidence)})
                  </span>
                </Badge>
              ))}
            </div>
          </div>
        )}

        {/* Warning if present */}
        {categorization._categorization_warning && (
          <Alert>
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              {categorization._categorization_warning}
            </AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
}

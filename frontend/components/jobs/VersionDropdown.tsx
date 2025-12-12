'use client';

import { useTranslations } from 'next-intl';
import { formatDistanceToNow } from 'date-fns';
import { History } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

import { useJobVersions } from '@/hooks/use-job-versions';

interface VersionDropdownProps {
  jobId: string;
  /** The version currently being viewed */
  viewingVersion: number;
  /** The actual current/latest version saved in DB */
  currentVersion: number;
  /** Called when user selects a different version to view */
  onVersionChange: (version: number) => void;
  /** Whether version content is loading */
  isLoading?: boolean;
}

export function VersionDropdown({
  jobId,
  viewingVersion,
  currentVersion,
  onVersionChange,
  isLoading = false,
}: VersionDropdownProps) {
  const t = useTranslations('jobs');

  // Fetch version list
  const { data: versions, isLoading: isLoadingVersions } = useJobVersions(jobId);

  // Handle version selection - directly switch view, no confirmation needed
  const handleVersionSelect = (value: string) => {
    const versionNumber = parseInt(value, 10);
    if (versionNumber === viewingVersion) return;
    onVersionChange(versionNumber);
  };

  // If only 1 version (or loading), just show the version number
  if (isLoadingVersions || !versions || versions.length <= 1) {
    return (
      <div className="flex items-center gap-1 text-sm text-muted-foreground">
        <History className="h-4 w-4" />
        <span>{t('versions.version', { number: currentVersion })}</span>
      </div>
    );
  }

  return (
    <Select
      value={viewingVersion.toString()}
      onValueChange={handleVersionSelect}
      disabled={isLoading}
    >
      <SelectTrigger className="w-auto h-8 text-sm gap-1">
        <History className="h-4 w-4 shrink-0" />
        <span className="truncate">
          v{viewingVersion}
          {viewingVersion === currentVersion && ` (${t('versions.current')})`}
        </span>
      </SelectTrigger>
      <SelectContent className="min-w-[280px]">
        {versions.map((version) => {
          const isCurrent = version.version_number === currentVersion;
          const isOriginal = version.version_number === 1;
          const timeAgo = formatDistanceToNow(new Date(version.created_at), { addSuffix: true });

          return (
            <SelectItem
              key={version.version_number}
              value={version.version_number.toString()}
              className="flex items-center"
            >
              <div className="flex items-center gap-2 w-full">
                <span className="font-medium">v{version.version_number}</span>
                {isCurrent && (
                  <Badge variant="default" className="text-[10px] px-1 py-0">
                    {t('versions.current')}
                  </Badge>
                )}
                {isOriginal && !isCurrent && (
                  <Badge variant="secondary" className="text-[10px] px-1 py-0">
                    {t('versions.original')}
                  </Badge>
                )}
                <span className="text-xs text-muted-foreground ml-auto">
                  {timeAgo}
                </span>
              </div>
            </SelectItem>
          );
        })}
      </SelectContent>
    </Select>
  );
}

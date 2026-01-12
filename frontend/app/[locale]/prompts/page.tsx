'use client';

import { use, useState } from 'react';
import { useTranslations, useLocale } from 'next-intl';
import { useRouter, Link } from '@/lib/navigation';
import { Plus, Zap, RefreshCw, HelpCircle, Eye, Trash2 } from 'lucide-react';
import { toast } from 'sonner';

import { usePrompts, useDeletePrompt } from '@/hooks/use-prompts';
import { useServiceTypes } from '@/hooks/use-service-types';
import { usePromptTypes } from '@/hooks/use-prompt-types';
import { Button } from '@/components/ui/button';
import { DataTable } from '@/components/shared/DataTable';
import { Pagination } from '@/components/shared/Pagination';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { ConfirmDialog } from '@/components/shared/ConfirmDialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import type { PromptResponse, PromptCategory } from "@/types/prompt";

// Helper to count placeholders in prompt content
const countPlaceholders = (content: string): number => {
  const matches = content.match(/\{\}/g);
  return matches ? matches.length : 0;
};

// Get processing mode compatibility based on placeholder count
const getProcessingModeInfo = (content: string): { mode: 'single_pass' | 'iterative' | 'both'; count: number } => {
  const count = countPlaceholders(content);
  if (count === 1) {
    return { mode: 'single_pass', count };
  } else if (count === 2) {
    return { mode: 'iterative', count };
  }
  return { mode: 'both', count };
};

interface PageProps {
  params: Promise<{ locale: string }>;
}

export default function PromptsPage({ params }: PageProps) {
  const resolvedParams = use(params);
  const { locale } = resolvedParams;
  const t = useTranslations();
  const tCommon = useTranslations('common');
  const router = useRouter();
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);

  // Filter state - with page reset handlers
  const [serviceTypeFilter, setServiceTypeFilter] = useState<string>('all');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [promptTypeFilter, setPromptTypeFilter] = useState<string>('all');

  // Delete state
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [selectedPrompt, setSelectedPrompt] = useState<PromptResponse | null>(null);

  // Handler that resets page when filter changes
  const handleServiceTypeChange = (value: string) => {
    setServiceTypeFilter(value);
    setPage(1); // Reset to first page when filter changes
    // Reset prompt type filter when service type changes to non-summary
    if (value !== 'summary') {
      setPromptTypeFilter('all');
    }
  };

  const handleCategoryChange = (value: string) => {
    setCategoryFilter(value);
    setPage(1); // Reset to first page when filter changes
  };

  const handlePromptTypeChange = (value: string) => {
    setPromptTypeFilter(value);
    setPage(1); // Reset to first page when filter changes
  };

  // Fetch service types for filter dropdown
  const { data: serviceTypes } = useServiceTypes();

  // Fetch prompt types for summary service (for filter dropdown)
  const { data: summaryPromptTypes } = usePromptTypes({
    service_type: 'summary',
    active_only: true
  });

  // Apply filters to usePrompts
  const { data: promptsResponse, isLoading } = usePrompts({
    page,
    page_size: pageSize,
    service_type: serviceTypeFilter === 'all' ? undefined : serviceTypeFilter,
    prompt_category: categoryFilter === 'all' ? undefined : categoryFilter as PromptCategory,
    prompt_type: promptTypeFilter === 'all' ? undefined : promptTypeFilter,
  });

  // Delete mutation
  const deleteMutation = useDeletePrompt();

  // Handlers
  const handleDelete = async () => {
    if (!selectedPrompt) return;

    try {
      await deleteMutation.mutateAsync(selectedPrompt.id);
      toast.success(t('prompts.deleteSuccess'));
      setDeleteDialogOpen(false);
      setSelectedPrompt(null);
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : t('prompts.deleteError');
      toast.error(message);
    }
  };

  const handleViewPrompt = (prompt: PromptResponse) => {
    router.push(`/prompts/${prompt.id}`);
  };

  // Helper to get service type display name
  const getServiceTypeName = (type: string | null) => {
    if (!type) return '-';
    const config = serviceTypes?.find(st => st.code === type);
    return config ? (locale === 'fr' ? (config.name.fr || config.name.en) : config.name.en) : type;
  };

  const columns = [
    {
      header: t('prompts.fields.name'),
      accessorKey: 'name' as keyof PromptResponse,
      cell: (row: PromptResponse) => (
        <Link href={`/prompts/${row.id}`} className="text-primary hover:underline">
          {row.name}
        </Link>
      ),
    },
    // Service Type column
    {
      header: t('prompts.serviceType'),
      accessorKey: 'service_type' as keyof PromptResponse,
      cell: (row: PromptResponse) => (
        <Badge variant={row.service_type ? 'default' : 'secondary'}>
          {getServiceTypeName(row.service_type)}
        </Badge>
      ),
    },
    // Category column (System / User)
    {
      header: t('prompts.fields.category'),
      accessorKey: 'prompt_category' as keyof PromptResponse,
      cell: (row: PromptResponse) => row.prompt_category ? (
        <Badge variant={row.prompt_category === 'system' ? 'secondary' : 'outline'}>
          {t(`prompts.category.${row.prompt_category}`)}
        </Badge>
      ) : (
        <span className="text-muted-foreground">-</span>
      ),
    },
    // Processing mode compatibility based on placeholder count
    {
      header: t('prompts.processingMode'),
      accessorKey: 'content' as keyof PromptResponse,
      cell: (row: PromptResponse) => {
        const { mode, count } = getProcessingModeInfo(row.content);
        if (mode === 'single_pass') {
          return (
            <Badge variant="outline" className="gap-1">
              <Zap className="h-3 w-3" />
              {t('prompts.modes.singlePass')}
            </Badge>
          );
        } else if (mode === 'iterative') {
          return (
            <Badge variant="outline" className="gap-1">
              <RefreshCw className="h-3 w-3" />
              {t('prompts.modes.iterative')}
            </Badge>
          );
        }
        return (
          <Badge variant="outline" className="gap-1 text-muted-foreground">
            <HelpCircle className="h-3 w-3" />
            {count} {'{}'}
          </Badge>
        );
      },
    },
    {
      header: t('common.createdAt'),
      accessorKey: 'created_at' as keyof PromptResponse,
      cell: (row: PromptResponse) => new Date(row.created_at).toLocaleDateString(),
    },
    {
      header: tCommon('actions'),
      cell: (row: PromptResponse) => (
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              handleViewPrompt(row);
            }}
          >
            <Eye className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={(e) => {
              e.stopPropagation();
              setSelectedPrompt(row);
              setDeleteDialogOpen(true);
            }}
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">{t('prompts.title')}</h1>
          <p className="text-muted-foreground mt-1">{t('prompts.subtitle')}</p>
        </div>
        <Button onClick={() => router.push('/prompts/new')} data-testid="btn-create">
          <Plus className="mr-2 h-4 w-4" />
          {t('prompts.createNew')}
        </Button>
      </div>

      {/* Filters */}
      <div className="flex gap-4 flex-wrap">
        <div className="flex items-center gap-2">
          <Label>{t('prompts.filters.serviceType')}</Label>
          <Select value={serviceTypeFilter} onValueChange={handleServiceTypeChange}>
            <SelectTrigger className="w-[200px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">{t('prompts.filters.allServiceTypes')}</SelectItem>
              {serviceTypes?.map((st) => (
                <SelectItem key={st.code} value={st.code}>
                  {locale === 'fr' ? (st.name.fr || st.name.en) : st.name.en}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-center gap-2">
          <Label>{t('prompts.fields.category')}</Label>
          <Select value={categoryFilter} onValueChange={handleCategoryChange}>
            <SelectTrigger className="w-[160px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">{t('prompts.filters.allCategories')}</SelectItem>
              <SelectItem value="system">{t('prompts.category.system')}</SelectItem>
              <SelectItem value="user">{t('prompts.category.user')}</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Prompt Type filter - only visible when Summary is selected */}
        {serviceTypeFilter === 'summary' && (
          <div className="flex items-center gap-2">
            <Label>{t('prompts.fields.promptType')}</Label>
            <Select value={promptTypeFilter} onValueChange={handlePromptTypeChange}>
              <SelectTrigger className="w-[180px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">{t('prompts.filters.allPromptTypes')}</SelectItem>
                {summaryPromptTypes?.map((pt) => (
                  <SelectItem key={pt.code} value={pt.code}>
                    {locale === 'fr' ? (pt.name.fr || pt.name.en) : pt.name.en}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}
      </div>

      <DataTable
        columns={columns}
        data={promptsResponse?.items || []}
        isLoading={isLoading}
        onRowClick={(row) => router.push(`/prompts/${row.id}`)}
        getRowId={(row) => row.id}
        emptyState={{ title: t('prompts.emptyStateDescription'), description: t('prompts.emptyStateDescription') }}
      />

      {promptsResponse && promptsResponse.total > 0 && (
        <Pagination
          page={page}
          totalPages={promptsResponse.total_pages}
          pageSize={pageSize}
          total={promptsResponse.total}
          onPageChange={setPage}
          onPageSizeChange={setPageSize}
        />
      )}

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        open={deleteDialogOpen}
        onOpenChange={setDeleteDialogOpen}
        title={t('prompts.deletePrompt')}
        description={t('prompts.deleteConfirm')}
        confirmText={tCommon('delete')}
        cancelText={tCommon('cancel')}
        onConfirm={handleDelete}
        variant="destructive"
      />
    </div>
  );
}

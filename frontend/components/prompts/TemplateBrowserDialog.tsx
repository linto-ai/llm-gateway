'use client';

import { useState, useMemo } from 'react';
import { useTranslations } from 'next-intl';
import { format } from 'date-fns';
import { enUS, fr } from 'date-fns/locale';
import { Search } from 'lucide-react';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { usePromptTemplates } from '@/hooks/use-prompts';
import type { PromptResponse, PromptCategory } from '@/types/prompt';

interface TemplateBrowserDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  category: PromptCategory;
  onSelect: (template: PromptResponse) => void;
  locale?: string;
}

export function TemplateBrowserDialog({
  open,
  onOpenChange,
  category,
  onSelect,
  locale = 'en',
}: TemplateBrowserDialogProps) {
  const t = useTranslations('sprint007.prompts.templates');
  const [searchQuery, setSearchQuery] = useState('');
  const [page, setPage] = useState(1);

  const { data: templatesResponse, isLoading } = usePromptTemplates({
    category,
    page,
    page_size: 10,
  });

  const dateLocale = locale === 'fr' ? fr : enUS;

  // Client-side search filtering
  const filteredTemplates = useMemo(() => {
    if (!templatesResponse?.items) return [];

    if (!searchQuery) return templatesResponse.items;

    const query = searchQuery.toLowerCase();
    return templatesResponse.items.filter(
      (t) =>
        t.name.toLowerCase().includes(query) ||
        t.content.toLowerCase().includes(query) ||
        Object.values(t.description).some((desc) => desc.toLowerCase().includes(query))
    );
  }, [templatesResponse, searchQuery]);

  const handleSelect = (template: PromptResponse) => {
    onSelect(template);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {t('browse')}: {t(`category.${category}`)}
          </DialogTitle>
          <DialogDescription>
            {t('../saveAsTemplate.descriptionEn')}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder={t('search')}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-8"
            />
          </div>

          {/* Template list */}
          {isLoading && (
            <div className="text-center py-8 text-muted-foreground">
              {t('../../common.loading')}
            </div>
          )}

          {!isLoading && filteredTemplates.length === 0 && (
            <div className="text-center py-8 text-muted-foreground">
              {t('noTemplates')}
            </div>
          )}

          {!isLoading && filteredTemplates.length > 0 && (
            <div className="space-y-4">
              {filteredTemplates.map((template) => (
                <Card key={template.id}>
                  <CardHeader>
                    <CardTitle className="text-base">{template.name}</CardTitle>
                    <CardDescription>
                      {template.description[locale] || template.description['en'] || ''}
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="bg-muted p-3 rounded-md">
                      <p className="text-sm font-mono text-muted-foreground line-clamp-3">
                        {template.content}
                      </p>
                    </div>
                  </CardContent>
                  <CardFooter className="flex justify-between">
                    <span className="text-sm text-muted-foreground">
                      {t('created')}: {format(new Date(template.created_at), 'PP', { locale: dateLocale })}
                    </span>
                    <Button onClick={() => handleSelect(template)}>
                      {t('select')}
                    </Button>
                  </CardFooter>
                </Card>
              ))}
            </div>
          )}

          {/* Pagination */}
          {templatesResponse && templatesResponse.total_pages > 1 && (
            <div className="flex justify-center gap-2">
              <Button
                variant="outline"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
              >
                {t('../../common.previous')}
              </Button>
              <span className="flex items-center px-4">
                {page} {t('../../common.of')} {templatesResponse.total_pages}
              </span>
              <Button
                variant="outline"
                onClick={() => setPage((p) => Math.min(templatesResponse.total_pages, p + 1))}
                disabled={page === templatesResponse.total_pages}
              >
                {t('../../common.next')}
              </Button>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

'use client';

import { useState, useCallback } from 'react';
import { useTranslations } from 'next-intl';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Upload, X, FileText, Loader2 } from 'lucide-react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Checkbox } from '@/components/ui/checkbox';
import { Textarea } from '@/components/ui/textarea';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
  FormDescription,
} from '@/components/ui/form';
import { Card, CardContent } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

import { useUploadDocumentTemplate } from '@/hooks/use-document-templates';
import { formatFileSize } from '@/lib/template-utils';
import type { DocumentTemplate } from '@/types/document-template';

// Max file size: 10MB
const MAX_FILE_SIZE = 10 * 1024 * 1024;

// Allowed MIME types for DOCX
const ALLOWED_MIME_TYPES = [
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
];

interface TemplateUploadProps {
  organizationId?: string;
  userId?: string;
  /** @deprecated Use organizationId instead - kept for backward compatibility */
  serviceId?: string;
  /** Whether to show the "set as default" checkbox. Only relevant in service context. */
  showDefaultOption?: boolean;
  onSuccess: (template: DocumentTemplate) => void;
  onCancel?: () => void;
}

/**
 * Template upload form with i18n fields and drag-and-drop support.
 */
export function TemplateUpload({
  organizationId,
  userId,
  serviceId: _serviceId,
  showDefaultOption = true,
  onSuccess,
  onCancel,
}: TemplateUploadProps) {
  const t = useTranslations('templates');
  const tCommon = useTranslations('common');

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [fileError, setFileError] = useState<string | null>(null);

  const uploadMutation = useUploadDocumentTemplate();

  // Form schema with i18n fields
  const formSchema = z.object({
    name_fr: z.string().min(1, t('fileValidation.required')),
    name_en: z.string().optional(),
    description_fr: z.string().optional(),
    description_en: z.string().optional(),
    is_default: z.boolean().default(false),
  });

  type FormData = z.infer<typeof formSchema>;

  const form = useForm<FormData>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      name_fr: '',
      name_en: '',
      description_fr: '',
      description_en: '',
      is_default: false,
    },
  });

  // Validate file
  const validateFile = (file: File): string | null => {
    if (!ALLOWED_MIME_TYPES.includes(file.type)) {
      return t('fileValidation.invalidType');
    }
    if (file.size > MAX_FILE_SIZE) {
      return t('fileValidation.tooLarge');
    }
    return null;
  };

  // Handle file selection
  const handleFileSelect = (file: File | null) => {
    if (!file) {
      setSelectedFile(null);
      setFileError(null);
      return;
    }

    const error = validateFile(file);
    if (error) {
      setFileError(error);
      setSelectedFile(null);
      return;
    }

    setFileError(null);
    setSelectedFile(file);

    // Auto-fill name from filename if empty
    if (!form.getValues('name_fr')) {
      const nameWithoutExtension = file.name.replace(/\.docx$/i, '');
      form.setValue('name_fr', nameWithoutExtension);
    }
  };

  // Handle drag events
  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      handleFileSelect(files[0]);
    }
  }, []);

  // Handle form submission
  const onSubmit = async (data: FormData) => {
    if (!selectedFile) {
      setFileError(t('fileValidation.required'));
      return;
    }

    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('name_fr', data.name_fr);
    formData.append('is_default', String(data.is_default));

    if (data.name_en) {
      formData.append('name_en', data.name_en);
    }
    if (data.description_fr) {
      formData.append('description_fr', data.description_fr);
    }
    if (data.description_en) {
      formData.append('description_en', data.description_en);
    }
    if (organizationId) {
      formData.append('organization_id', organizationId);
    }
    if (userId) {
      formData.append('user_id', userId);
    }

    try {
      const template = await uploadMutation.mutateAsync(formData);
      toast.success(t('uploadSuccess'));
      onSuccess(template);
    } catch (error: any) {
      toast.error(error.message || t('uploadError'));
    }
  };

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
        {/* Drop zone */}
        <div
          className={`
            relative border-2 border-dashed rounded-lg p-8 text-center transition-colors cursor-pointer
            ${isDragging ? 'border-primary bg-primary/5' : 'border-muted-foreground/25 hover:border-primary/50'}
            ${fileError ? 'border-destructive' : ''}
          `}
          onDragEnter={handleDragEnter}
          onDragLeave={handleDragLeave}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
          onClick={() => document.getElementById('file-input')?.click()}
        >
          <input
            id="file-input"
            type="file"
            accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            className="hidden"
            onChange={(e) => handleFileSelect(e.target.files?.[0] || null)}
          />

          {selectedFile ? (
            <Card className="inline-block">
              <CardContent className="p-4 flex items-center gap-3">
                <FileText className="h-8 w-8 text-blue-500" />
                <div className="text-left">
                  <p className="font-medium">{selectedFile.name}</p>
                  <p className="text-sm text-muted-foreground">
                    {formatFileSize(selectedFile.size)}
                  </p>
                </div>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={(e) => {
                    e.stopPropagation();
                    setSelectedFile(null);
                  }}
                >
                  <X className="h-4 w-4" />
                </Button>
              </CardContent>
            </Card>
          ) : (
            <>
              <Upload className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <p className="text-lg font-medium">{t('dropzone.title')}</p>
              <p className="text-sm text-muted-foreground">{t('dropzone.subtitle')}</p>
            </>
          )}
        </div>

        {fileError && (
          <p className="text-sm text-destructive">{fileError}</p>
        )}

        {/* i18n fields in tabs */}
        <Tabs defaultValue="fr" className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="fr">{t('fields.french')}</TabsTrigger>
            <TabsTrigger value="en">{t('fields.english')}</TabsTrigger>
          </TabsList>

          <TabsContent value="fr" className="space-y-4 mt-4">
            {/* French Name */}
            <FormField
              control={form.control}
              name="name_fr"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('fields.nameFr')} *</FormLabel>
                  <FormControl>
                    <Input {...field} placeholder={t('namePlaceholder')} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* French Description */}
            <FormField
              control={form.control}
              name="description_fr"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('fields.descriptionFr')}</FormLabel>
                  <FormControl>
                    <Textarea
                      {...field}
                      placeholder={t('descriptionPlaceholder')}
                      rows={3}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </TabsContent>

          <TabsContent value="en" className="space-y-4 mt-4">
            {/* English Name */}
            <FormField
              control={form.control}
              name="name_en"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('fields.nameEn')}</FormLabel>
                  <FormControl>
                    <Input {...field} placeholder={t('namePlaceholder')} />
                  </FormControl>
                  <FormDescription>
                    {t('fields.optionalEnglish')}
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* English Description */}
            <FormField
              control={form.control}
              name="description_en"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('fields.descriptionEn')}</FormLabel>
                  <FormControl>
                    <Textarea
                      {...field}
                      placeholder={t('descriptionPlaceholder')}
                      rows={3}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </TabsContent>
        </Tabs>

        {/* Set as Default - only shown in service context */}
        {showDefaultOption && (
          <FormField
            control={form.control}
            name="is_default"
            render={({ field }) => (
              <FormItem className="flex flex-row items-start space-x-3 space-y-0 rounded-md border p-4">
                <FormControl>
                  <Checkbox checked={field.value} onCheckedChange={field.onChange} />
                </FormControl>
                <div className="space-y-1 leading-none">
                  <FormLabel>{t('setDefault')}</FormLabel>
                  <FormDescription>
                    {t('setDefaultDescription')}
                  </FormDescription>
                </div>
              </FormItem>
            )}
          />
        )}

        {/* Actions */}
        <div className="flex justify-end gap-3">
          {onCancel && (
            <Button type="button" variant="outline" onClick={onCancel}>
              {tCommon('cancel')}
            </Button>
          )}
          <Button type="submit" disabled={uploadMutation.isPending || !selectedFile}>
            {uploadMutation.isPending ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                {tCommon('uploading')}
              </>
            ) : (
              <>
                <Upload className="h-4 w-4 mr-2" />
                {t('upload')}
              </>
            )}
          </Button>
        </div>
      </form>
    </Form>
  );
}

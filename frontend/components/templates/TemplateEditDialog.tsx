'use client';

import { useState, useCallback, useEffect } from 'react';
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
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
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
import { Badge } from '@/components/ui/badge';

import { useUpdateDocumentTemplate } from '@/hooks/use-document-templates';
import { formatFileSize } from '@/lib/template-utils';
import { getPlaceholderName } from '@/types/document-template';
import type { DocumentTemplate } from '@/types/document-template';

// Max file size: 10MB
const MAX_FILE_SIZE = 10 * 1024 * 1024;

// Allowed MIME types for DOCX
const ALLOWED_MIME_TYPES = [
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
];

interface TemplateEditDialogProps {
  template: DocumentTemplate | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
  /** Whether to show the "Set as Default" option. Only relevant in service context. */
  showDefaultOption?: boolean;
}

/**
 * Dialog for editing template metadata and optionally replacing the file.
 */
export function TemplateEditDialog({
  template,
  open,
  onOpenChange,
  onSuccess,
  showDefaultOption = false,
}: TemplateEditDialogProps) {
  const t = useTranslations('templates');
  const tCommon = useTranslations('common');

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [fileError, setFileError] = useState<string | null>(null);

  const updateMutation = useUpdateDocumentTemplate();

  // Form schema
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

  // Reset form when template changes
  useEffect(() => {
    if (template) {
      form.reset({
        name_fr: template.name_fr,
        name_en: template.name_en || '',
        description_fr: template.description_fr || '',
        description_en: template.description_en || '',
        is_default: template.is_default,
      });
    }
    setSelectedFile(null);
    setFileError(null);
  }, [template, form]);

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
    if (!template) return;

    const formData = new FormData();

    // Only append changed fields
    if (data.name_fr !== template.name_fr) {
      formData.append('name_fr', data.name_fr);
    }
    if (data.name_en !== (template.name_en || '')) {
      formData.append('name_en', data.name_en || '');
    }
    if (data.description_fr !== (template.description_fr || '')) {
      formData.append('description_fr', data.description_fr || '');
    }
    if (data.description_en !== (template.description_en || '')) {
      formData.append('description_en', data.description_en || '');
    }
    if (data.is_default !== template.is_default) {
      formData.append('is_default', String(data.is_default));
    }

    // Append file if selected
    if (selectedFile) {
      formData.append('file', selectedFile);
    }

    try {
      await updateMutation.mutateAsync({ id: template.id, formData });
      toast.success(t('updateSuccess'));
      onOpenChange(false);
      onSuccess?.();
    } catch (error: any) {
      toast.error(error.message || t('updateError'));
    }
  };

  if (!template) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{t('edit')}</DialogTitle>
          <DialogDescription>
            {t('editDescription')}
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
            {/* Current file info */}
            <div className="rounded-lg border p-4 bg-muted/50">
              <div className="flex items-center gap-3">
                <FileText className="h-8 w-8 text-blue-500" />
                <div>
                  <p className="font-medium">{template.file_name}</p>
                  <p className="text-sm text-muted-foreground">
                    {formatFileSize(template.file_size)}
                  </p>
                </div>
              </div>
              {/* Show placeholders */}
              {template.placeholders && template.placeholders.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-1">
                  {template.placeholders.map((placeholder) => (
                    <Badge key={placeholder} variant="outline" className="text-xs font-mono">
                      {`{{${getPlaceholderName(placeholder)}}}`}
                    </Badge>
                  ))}
                </div>
              )}
            </div>

            {/* Optional file replacement */}
            <div className="space-y-2">
              <label className="text-sm font-medium">{t('replaceFile')}</label>
              <div
                className={`
                  relative border-2 border-dashed rounded-lg p-4 text-center transition-colors cursor-pointer
                  ${isDragging ? 'border-primary bg-primary/5' : 'border-muted-foreground/25 hover:border-primary/50'}
                  ${fileError ? 'border-destructive' : ''}
                `}
                onDragEnter={handleDragEnter}
                onDragLeave={handleDragLeave}
                onDragOver={handleDragOver}
                onDrop={handleDrop}
                onClick={() => document.getElementById('edit-file-input')?.click()}
              >
                <input
                  id="edit-file-input"
                  type="file"
                  accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                  className="hidden"
                  onChange={(e) => handleFileSelect(e.target.files?.[0] || null)}
                />

                {selectedFile ? (
                  <Card className="inline-block">
                    <CardContent className="p-3 flex items-center gap-3">
                      <FileText className="h-6 w-6 text-blue-500" />
                      <div className="text-left">
                        <p className="font-medium text-sm">{selectedFile.name}</p>
                        <p className="text-xs text-muted-foreground">
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
                    <Upload className="h-8 w-8 mx-auto text-muted-foreground mb-2" />
                    <p className="text-sm">{t('dropzone.replaceTitle')}</p>
                    <p className="text-xs text-muted-foreground">{t('dropzone.optional')}</p>
                  </>
                )}
              </div>
              {fileError && (
                <p className="text-sm text-destructive">{fileError}</p>
              )}
            </div>

            {/* i18n fields in tabs */}
            <Tabs defaultValue="fr" className="w-full">
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="fr">{t('fields.french')}</TabsTrigger>
                <TabsTrigger value="en">{t('fields.english')}</TabsTrigger>
              </TabsList>

              <TabsContent value="fr" className="space-y-4 mt-4">
                <FormField
                  control={form.control}
                  name="name_fr"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>{t('fields.nameFr')} *</FormLabel>
                      <FormControl>
                        <Input {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="description_fr"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>{t('fields.descriptionFr')}</FormLabel>
                      <FormControl>
                        <Textarea {...field} rows={3} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </TabsContent>

              <TabsContent value="en" className="space-y-4 mt-4">
                <FormField
                  control={form.control}
                  name="name_en"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>{t('fields.nameEn')}</FormLabel>
                      <FormControl>
                        <Input {...field} />
                      </FormControl>
                      <FormDescription>
                        {t('fields.optionalEnglish')}
                      </FormDescription>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="description_en"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>{t('fields.descriptionEn')}</FormLabel>
                      <FormControl>
                        <Textarea {...field} rows={3} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </TabsContent>
            </Tabs>

            {/* Set as Default - only show in service context */}
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
                      <FormLabel>{t('fields.isDefault')}</FormLabel>
                    </div>
                  </FormItem>
                )}
              />
            )}

            {/* Actions */}
            <div className="flex justify-end gap-3">
              <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                {tCommon('cancel')}
              </Button>
              <Button type="submit" disabled={updateMutation.isPending}>
                {updateMutation.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    {tCommon('saving')}
                  </>
                ) : (
                  tCommon('save')
                )}
              </Button>
            </div>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}

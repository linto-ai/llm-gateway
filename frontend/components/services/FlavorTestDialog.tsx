'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Loader2 } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { useTestFlavor } from '@/hooks/use-services';
import { testFlavorSchema, type TestFlavorFormData } from '@/schemas/service.schema';
import { toast } from 'sonner';
import type { FlavorTestResponse } from '@/types/service';

interface FlavorTestDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  flavorId: string;
  flavorName: string;
}

export function FlavorTestDialog({
  open,
  onOpenChange,
  flavorId,
  flavorName,
}: FlavorTestDialogProps) {
  const t = useTranslations('flavors.test');
  const tCommon = useTranslations('common');
  const [testResult, setTestResult] = useState<FlavorTestResponse | null>(null);
  const testFlavorMutation = useTestFlavor();

  const form = useForm<TestFlavorFormData>({
    resolver: zodResolver(testFlavorSchema),
    defaultValues: {
      prompt: '',
    },
  });

  const onSubmit = async (data: TestFlavorFormData) => {
    try {
      const result = await testFlavorMutation.mutateAsync({
        flavorId,
        data,
      });
      setTestResult(result);
      toast.success(t('success'));
    } catch (error: any) {
      toast.error(error.response?.data?.detail || t('error'));
    }
  };

  const handleClose = () => {
    onOpenChange(false);
    form.reset();
    setTestResult(null);
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto overflow-x-hidden">
        <DialogHeader>
          <DialogTitle>{t('title')}: {flavorName}</DialogTitle>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            {/* Prompt Input */}
            <FormField
              control={form.control}
              name="prompt"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t('prompt')}</FormLabel>
                  <FormControl>
                    <Textarea
                      {...field}
                      placeholder={t('promptPlaceholder')}
                      rows={6}
                      disabled={testFlavorMutation.isPending}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Submit Button */}
            <Button
              type="submit"
              disabled={testFlavorMutation.isPending || !form.watch('prompt')}
              className="w-full"
            >
              {testFlavorMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  {t('running')}
                </>
              ) : (
                t('run')
              )}
            </Button>
          </form>
        </Form>

        {/* Results Section */}
        {testResult && (
          <div className="border rounded-lg p-4 space-y-4 mt-4">
            <div>
              <h4 className="font-semibold text-sm mb-2">{t('model')}</h4>
              <p className="text-sm text-muted-foreground">
                {testResult.model.model_name} ({testResult.model.provider_name})
              </p>
            </div>

            <div className="min-w-0">
              <h4 className="font-semibold text-sm mb-2">{t('request')}</h4>
              <pre className="text-xs bg-muted p-3 rounded overflow-x-auto max-w-full whitespace-pre-wrap break-all">
                {JSON.stringify(testResult.request, null, 2)}
              </pre>
            </div>

            <div className="min-w-0">
              <h4 className="font-semibold text-sm mb-2">{t('response')}</h4>
              <div className="bg-muted p-4 rounded whitespace-pre-wrap text-sm break-words">
                {testResult.response.content}
              </div>
              <p className="text-xs text-muted-foreground mt-2">
                {t('finishReason')}: {testResult.response.finish_reason}
              </p>
            </div>

            <div>
              <h4 className="font-semibold text-sm mb-2">{t('metadata')}</h4>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <span className="text-muted-foreground">{t('inputTokens')}:</span>{' '}
                  {testResult.metadata.input_tokens}
                </div>
                <div>
                  <span className="text-muted-foreground">{t('outputTokens')}:</span>{' '}
                  {testResult.metadata.output_tokens}
                </div>
                <div>
                  <span className="text-muted-foreground">{t('totalTokens')}:</span>{' '}
                  {testResult.metadata.total_tokens}
                </div>
                <div>
                  <span className="text-muted-foreground">{t('latency')}:</span>{' '}
                  {testResult.metadata.latency_ms}ms
                </div>
                {testResult.metadata.estimated_cost != null && (
                  <div className="col-span-2">
                    <span className="text-muted-foreground">{t('cost')}:</span> $
                    {testResult.metadata.estimated_cost.toFixed(4)}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

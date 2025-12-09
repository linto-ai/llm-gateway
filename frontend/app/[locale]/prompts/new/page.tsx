'use client';

import { use } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { toast } from 'sonner';
import { ArrowLeft } from 'lucide-react';
import Link from 'next/link';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { PromptForm } from '@/components/prompts/PromptForm';

interface PageProps {
  params: Promise<{ locale: string }>;
}

export default function NewPromptPage({ params }: PageProps) {
  const { locale } = use(params);
  const t = useTranslations();
  const router = useRouter();

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="sm" asChild>
          <Link href={`/${locale}/prompts`}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            {t('common.back')}
          </Link>
        </Button>
        <h1 className="text-3xl font-bold">{t('prompts.createNew')}</h1>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{t('prompts.newPromptTitle')}</CardTitle>
        </CardHeader>
        <CardContent>
          <PromptForm
            onSuccess={() => {
              toast.success(t('prompts.createSuccess'));
              router.push(`/${locale}/prompts`);
            }}
            onCancel={() => router.push(`/${locale}/prompts`)}
          />
        </CardContent>
      </Card>
    </div>
  );
}

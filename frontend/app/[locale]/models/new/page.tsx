'use client';

import { use } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { toast } from 'sonner';
import { ArrowLeft } from 'lucide-react';
import Link from 'next/link';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ModelForm } from '@/components/models/ModelForm';

interface PageProps {
  params: Promise<{ locale: string }>;
}

export default function NewModelPage({ params }: PageProps) {
  const { locale } = use(params);
  const t = useTranslations();
  const router = useRouter();

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="sm" asChild>
          <Link href={`/${locale}/models`}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            {t('common.back')}
          </Link>
        </Button>
        <h1 className="text-3xl font-bold">{t('models.createNew')}</h1>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{t('models.newModelTitle')}</CardTitle>
        </CardHeader>
        <CardContent>
          <ModelForm
            locale={locale}
            onSuccess={() => {
              toast.success(t('models.createSuccess'));
              router.push(`/${locale}/models`);
            }}
            onCancel={() => router.push(`/${locale}/models`)}
          />
        </CardContent>
      </Card>
    </div>
  );
}

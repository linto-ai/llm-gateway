'use client';

import { use } from 'react';
import { useRouter, Link } from '@/lib/navigation';
import { useTranslations } from 'next-intl';
import { toast } from 'sonner';
import { ArrowLeft } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { ServiceForm } from '@/components/services/ServiceForm';

interface PageProps {
  params: Promise<{ locale: string }>;
}

export default function NewServicePage({ params }: PageProps) {
  const { locale } = use(params);
  const t = useTranslations();
  const router = useRouter();

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="sm" asChild>
          <Link href="/services">
            <ArrowLeft className="h-4 w-4 mr-2" />
            {t('common.back')}
          </Link>
        </Button>
        <h1 className="text-3xl font-bold">{t('services.createNew')}</h1>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{t('services.newServiceTitle')}</CardTitle>
        </CardHeader>
        <CardContent>
          <ServiceForm
            onSuccess={() => {
              toast.success(t('services.createSuccess'));
              router.push('/services');
            }}
            onCancel={() => router.push('/services')}
          />
        </CardContent>
      </Card>
    </div>
  );
}

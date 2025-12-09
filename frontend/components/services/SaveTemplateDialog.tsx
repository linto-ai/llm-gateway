'use client';

import { useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { useTranslations } from 'next-intl';

interface SaveTemplateDialogProps {
  open: boolean;
  onClose: () => void;
  onSave: (name: string, description: { en: string; fr: string }) => Promise<void>;
}

export function SaveTemplateDialog({ open, onClose, onSave }: SaveTemplateDialogProps) {
  const t = useTranslations('services.flavors');
  const [name, setName] = useState('');
  const [descriptionEn, setDescriptionEn] = useState('');
  const [descriptionFr, setDescriptionFr] = useState('');
  const [saving, setSaving] = useState(false);

  const handleSave = async () => {
    setSaving(true);
    try {
      await onSave(name, { en: descriptionEn, fr: descriptionFr });
      setName('');
      setDescriptionEn('');
      setDescriptionFr('');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t('saveAsTemplate')}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div>
            <Label htmlFor="name">{t('templateName')}</Label>
            <Input
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder={t('templateNamePlaceholder')}
            />
          </div>
          <div>
            <Label htmlFor="desc-en">{t('descriptionEn')}</Label>
            <Input
              id="desc-en"
              value={descriptionEn}
              onChange={(e) => setDescriptionEn(e.target.value)}
            />
          </div>
          <div>
            <Label htmlFor="desc-fr">{t('descriptionFr')}</Label>
            <Input
              id="desc-fr"
              value={descriptionFr}
              onChange={(e) => setDescriptionFr(e.target.value)}
            />
          </div>
        </div>
        <DialogFooter>
          <Button type="button" variant="outline" onClick={onClose}>
            {t('cancel')}
          </Button>
          <Button type="button" onClick={handleSave} disabled={saving || !name}>
            {t('save')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

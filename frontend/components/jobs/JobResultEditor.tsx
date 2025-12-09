'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import { useTranslations } from 'next-intl';
import dynamic from 'next/dynamic';
import remarkGfm from 'remark-gfm';
import { Undo2, Redo2, Save, X, Eye, Edit3, AlertCircle } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';

// Lazy load ReactMarkdown for performance
const ReactMarkdown = dynamic(() => import('react-markdown'), {
  loading: () => <div className="animate-pulse text-muted-foreground">Loading...</div>,
});

interface JobResultEditorProps {
  jobId: string;
  initialContent: string;
  outputType: 'text' | 'markdown' | 'json';
  onSave: (content: string) => Promise<void>;
  onCancel: () => void;
}

// Local storage key for drafts
const getDraftKey = (jobId: string) => `job-draft-${jobId}`;

// Simple undo/redo history management
interface HistoryState {
  past: string[];
  present: string;
  future: string[];
}

export function JobResultEditor({
  jobId,
  initialContent,
  outputType,
  onSave,
  onCancel,
}: JobResultEditorProps) {
  const t = useTranslations('jobs');

  // History state for undo/redo
  const [history, setHistory] = useState<HistoryState>(() => {
    // Check for draft in localStorage
    if (typeof window !== 'undefined') {
      const draft = localStorage.getItem(getDraftKey(jobId));
      if (draft) {
        return { past: [initialContent], present: draft, future: [] };
      }
    }
    return { past: [], present: initialContent, future: [] };
  });

  const [isSaving, setIsSaving] = useState(false);
  const [showDiscardDialog, setShowDiscardDialog] = useState(false);

  const content = history.present;
  const hasChanges = content !== initialContent;
  const canUndo = history.past.length > 0;
  const canRedo = history.future.length > 0;

  // Determine if we should show markdown preview
  const showMarkdownPreview = outputType === 'markdown';

  // Auto-save draft to localStorage on content changes
  useEffect(() => {
    if (hasChanges) {
      localStorage.setItem(getDraftKey(jobId), content);
    } else {
      localStorage.removeItem(getDraftKey(jobId));
    }
  }, [content, hasChanges, jobId]);

  // Clear draft on unmount if saved
  useEffect(() => {
    return () => {
      // Draft will be cleared when component unmounts after save
    };
  }, []);

  // Handle content change with history tracking
  const handleChange = useCallback((newContent: string) => {
    setHistory((prev) => ({
      past: [...prev.past, prev.present],
      present: newContent,
      future: [],
    }));
  }, []);

  // Undo action
  const handleUndo = useCallback(() => {
    setHistory((prev) => {
      if (prev.past.length === 0) return prev;
      const newPast = [...prev.past];
      const previous = newPast.pop()!;
      return {
        past: newPast,
        present: previous,
        future: [prev.present, ...prev.future],
      };
    });
  }, []);

  // Redo action
  const handleRedo = useCallback(() => {
    setHistory((prev) => {
      if (prev.future.length === 0) return prev;
      const newFuture = [...prev.future];
      const next = newFuture.shift()!;
      return {
        past: [...prev.past, prev.present],
        present: next,
        future: newFuture,
      };
    });
  }, []);

  // Handle save
  const handleSave = async () => {
    if (!hasChanges) return;

    setIsSaving(true);
    try {
      await onSave(content);
      // Clear draft after successful save
      localStorage.removeItem(getDraftKey(jobId));
    } finally {
      setIsSaving(false);
    }
  };

  // Handle cancel with unsaved changes check
  const handleCancel = () => {
    if (hasChanges) {
      setShowDiscardDialog(true);
    } else {
      onCancel();
    }
  };

  // Confirm discard and cancel
  const confirmDiscard = () => {
    localStorage.removeItem(getDraftKey(jobId));
    setShowDiscardDialog(false);
    onCancel();
  };

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'z') {
        e.preventDefault();
        if (e.shiftKey) {
          handleRedo();
        } else {
          handleUndo();
        }
      }
      if ((e.metaKey || e.ctrlKey) && e.key === 's') {
        e.preventDefault();
        handleSave();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleUndo, handleRedo, handleSave]);

  // Character count
  const charCount = useMemo(() => content.length, [content]);

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <Edit3 className="h-5 w-5" />
            {t('editor.title')}
          </CardTitle>
          <div className="flex items-center gap-2">
            {/* Undo/Redo buttons */}
            <div className="flex items-center gap-1 mr-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={handleUndo}
                disabled={!canUndo}
                title="Undo (Ctrl+Z)"
                className="h-8 w-8 p-0"
              >
                <Undo2 className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleRedo}
                disabled={!canRedo}
                title="Redo (Ctrl+Shift+Z)"
                className="h-8 w-8 p-0"
              >
                <Redo2 className="h-4 w-4" />
              </Button>
            </div>

            {/* Save/Cancel buttons */}
            <Button
              variant="outline"
              size="sm"
              onClick={handleCancel}
              disabled={isSaving}
            >
              <X className="h-4 w-4 mr-1" />
              {t('editor.cancel')}
            </Button>
            <Button
              size="sm"
              onClick={handleSave}
              disabled={!hasChanges || isSaving}
            >
              <Save className="h-4 w-4 mr-1" />
              {isSaving ? t('editor.saving') : t('editor.save')}
            </Button>
          </div>
        </div>
        {/* Unsaved changes indicator */}
        {hasChanges && (
          <div className="flex items-center gap-1 text-sm text-amber-600 mt-1">
            <AlertCircle className="h-3 w-3" />
            {t('editor.unsavedChanges')}
          </div>
        )}
      </CardHeader>
      <CardContent>
        {showMarkdownPreview ? (
          // Markdown editor with preview tabs
          <Tabs defaultValue="edit" className="w-full">
            <TabsList className="mb-4">
              <TabsTrigger value="edit" className="gap-2">
                <Edit3 className="h-4 w-4" />
                {t('editor.edit')}
              </TabsTrigger>
              <TabsTrigger value="preview" className="gap-2">
                <Eye className="h-4 w-4" />
                {t('editor.preview')}
              </TabsTrigger>
            </TabsList>
            <TabsContent value="edit">
              <Textarea
                value={content}
                onChange={(e) => handleChange(e.target.value)}
                className="min-h-[400px] font-mono text-sm resize-y"
                placeholder={t('editor.placeholder')}
              />
              <div className="text-xs text-muted-foreground mt-2 text-right">
                {charCount.toLocaleString()} {t('editor.characters')}
              </div>
            </TabsContent>
            <TabsContent value="preview">
              <div className="prose prose-sm dark:prose-invert max-w-none bg-muted/50 p-4 rounded-md overflow-auto min-h-[400px] max-h-[600px]">
                {content ? (
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {content}
                  </ReactMarkdown>
                ) : (
                  <p className="text-muted-foreground italic">{t('editor.emptyPreview')}</p>
                )}
              </div>
            </TabsContent>
          </Tabs>
        ) : (
          // Plain textarea for text output
          <>
            <Textarea
              value={content}
              onChange={(e) => handleChange(e.target.value)}
              className="min-h-[400px] font-mono text-sm resize-y"
              placeholder={t('editor.placeholder')}
            />
            <div className="text-xs text-muted-foreground mt-2 text-right">
              {charCount.toLocaleString()} {t('editor.characters')}
            </div>
          </>
        )}
      </CardContent>

      {/* Discard changes confirmation dialog */}
      <AlertDialog open={showDiscardDialog} onOpenChange={setShowDiscardDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('editor.discardTitle')}</AlertDialogTitle>
            <AlertDialogDescription>
              {t('editor.discardConfirm')}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t('editor.cancel')}</AlertDialogCancel>
            <AlertDialogAction onClick={confirmDiscard}>
              {t('editor.discard')}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Card>
  );
}

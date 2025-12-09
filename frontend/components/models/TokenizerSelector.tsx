'use client';

import { useState, useEffect } from 'react';
import { useTranslations } from 'next-intl';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { HelpCircle, Download, Check, Loader2, X } from 'lucide-react';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { useTokenizers, usePreloadTokenizerByRepo } from '@/hooks/use-tokenizers';
import { toast } from 'sonner';

// Known tokenizer options
const TIKTOKEN_ENCODINGS = [
  { value: 'cl100k_base', label: 'cl100k_base', description: 'GPT-4, GPT-3.5-turbo, text-embedding-ada-002' },
  { value: 'o200k_base', label: 'o200k_base', description: 'GPT-4o, GPT-4o-mini, o1, o3' },
  { value: 'p50k_base', label: 'p50k_base', description: 'Codex models, text-davinci-002/003' },
  { value: 'r50k_base', label: 'r50k_base', description: 'GPT-3 models (davinci, curie, babbage, ada)' },
];

// Common HuggingFace tokenizers for known model families
const COMMON_HF_TOKENIZERS = [
  { value: 'meta-llama/Llama-3.3-70B-Instruct', label: 'Llama 3.3' },
  { value: 'meta-llama/Llama-3.1-8B-Instruct', label: 'Llama 3.1' },
  { value: 'meta-llama/Llama-2-7b-hf', label: 'Llama 2' },
  { value: 'mistralai/Mistral-7B-Instruct-v0.3', label: 'Mistral 7B' },
  { value: 'mistralai/Mixtral-8x7B-Instruct-v0.1', label: 'Mixtral 8x7B' },
  { value: 'Qwen/Qwen2.5-72B-Instruct', label: 'Qwen 2.5' },
  { value: 'deepseek-ai/DeepSeek-V3', label: 'DeepSeek V3' },
  { value: 'google/gemma-2-27b-it', label: 'Gemma 2' },
  { value: 'microsoft/phi-4', label: 'Phi 4' },
];

type TokenizerType = 'auto' | 'tiktoken' | 'huggingface';

interface TokenizerSelectorProps {
  tokenizerClass: string | null;
  tokenizerName: string | null;
  onChange: (tokenizerClass: string | null, tokenizerName: string | null) => void;
}

export function TokenizerSelector({
  tokenizerClass,
  tokenizerName,
  onChange,
}: TokenizerSelectorProps) {
  const t = useTranslations('models');
  const { data: tokenizersResponse } = useTokenizers();
  const preloadTokenizer = usePreloadTokenizerByRepo();
  const [tokenizerStatus, setTokenizerStatus] = useState<boolean | null>(null);
  const [customRepoInput, setCustomRepoInput] = useState('');

  // Determine current type from values
  const getTypeFromValues = (): TokenizerType => {
    if (!tokenizerClass && !tokenizerName) return 'auto';
    if (tokenizerClass === 'tiktoken') return 'tiktoken';
    // Any other case (including huggingface or unknown) maps to huggingface
    return 'huggingface';
  };

  const [type, setType] = useState<TokenizerType>(getTypeFromValues);

  // Check if current tokenizer is available locally
  const isTokenizerLocal = (repo: string) => {
    return tokenizersResponse?.tokenizers.some(t => t.source_repo === repo) ?? false;
  };

  // Update local state when props change
  useEffect(() => {
    setType(getTypeFromValues());
    // Update status based on local availability
    if (tokenizerClass === 'huggingface' && tokenizerName) {
      setTokenizerStatus(isTokenizerLocal(tokenizerName));
    }
  }, [tokenizerClass, tokenizerName, tokenizersResponse]);

  const handleDownloadTokenizer = async (repo: string) => {
    if (!repo) return;

    setTokenizerStatus(null);
    try {
      const result = await preloadTokenizer.mutateAsync(repo);
      if (result.success) {
        setTokenizerStatus(true);
        toast.success(result.cached ? t('tokenizer.alreadyCached') : t('tokenizer.downloaded'));
      } else {
        setTokenizerStatus(false);
        toast.error(result.message);
      }
    } catch (error: any) {
      setTokenizerStatus(false);
      const errorMsg = error.message || '';
      // Check if it's a gated repo error
      if (errorMsg.includes('gated') || errorMsg.includes('restricted')) {
        const needsAccess = errorMsg.includes('403') || errorMsg.includes('not in the authorized list');
        const needsToken = errorMsg.includes('401') || errorMsg.includes('be authenticated');

        if (needsAccess) {
          // User needs to accept license on HuggingFace
          toast.error(t('tokenizer.gatedRepoNeedsAccess'), {
            description: (
              <div className="space-y-2">
                <p>{t('tokenizer.gatedRepoAccessHint')}</p>
                <a
                  href={`https://huggingface.co/${repo}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary underline"
                >
                  {`huggingface.co/${repo}`}
                </a>
              </div>
            ),
            duration: 15000,
          });
        } else if (needsToken) {
          toast.error(t('tokenizer.gatedRepoError'), {
            description: t('tokenizer.gatedRepoHint'),
            duration: 10000,
          });
        } else {
          toast.error(t('tokenizer.gatedRepoError'), {
            description: errorMsg,
            duration: 10000,
          });
        }
      } else {
        toast.error(errorMsg || t('tokenizer.downloadFailed'));
      }
    }
  };

  const handleTypeChange = (newType: TokenizerType) => {
    setType(newType);
    setCustomRepoInput('');

    if (newType === 'auto') {
      onChange(null, null);
    } else if (newType === 'tiktoken') {
      // Default to cl100k_base for tiktoken
      onChange('tiktoken', 'cl100k_base');
    } else if (newType === 'huggingface') {
      // Clear values, user will select from dropdown or enter custom
      onChange('huggingface', '');
    }
  };

  const handleTiktokenEncodingChange = (encoding: string) => {
    onChange('tiktoken', encoding);
  };

  const handleHuggingFaceRepoChange = async (repo: string) => {
    if (repo === 'custom') {
      // User wants to enter a custom repo - show input field
      setCustomRepoInput('');
      return;
    }
    setCustomRepoInput('');
    onChange('huggingface', repo);
    // Auto-download if not already local
    if (!isTokenizerLocal(repo)) {
      await handleDownloadTokenizer(repo);
    } else {
      setTokenizerStatus(true);
    }
  };

  const handleCustomRepoSubmit = async () => {
    const repo = customRepoInput.trim();
    if (!repo) return;

    onChange('huggingface', repo);
    // Auto-download
    if (!isTokenizerLocal(repo)) {
      await handleDownloadTokenizer(repo);
    } else {
      setTokenizerStatus(true);
    }
  };

  // Display value for current tokenizer
  const getDisplayValue = () => {
    if (!tokenizerClass && !tokenizerName) {
      return t('tokenizer.autoDetect');
    }
    if (tokenizerClass === 'tiktoken' && tokenizerName) {
      return `tiktoken: ${tokenizerName}`;
    }
    if (tokenizerName) {
      return tokenizerName;
    }
    return t('tokenizer.autoDetect');
  };

  // Check if current repo is in common list
  const isCommonRepo = (repo: string) => {
    return COMMON_HF_TOKENIZERS.some(tok => tok.value === repo);
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <CardTitle className="text-lg">{t('tokenizer.title')}</CardTitle>
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <HelpCircle className="h-4 w-4 text-muted-foreground cursor-help" />
              </TooltipTrigger>
              <TooltipContent side="right" className="max-w-xs">
                <p>{t('tokenizer.help')}</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </div>
        <CardDescription>{t('tokenizer.description')}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Current value display */}
        <div className="flex items-center gap-2">
          <Label className="text-muted-foreground">{t('tokenizer.current')}:</Label>
          <Badge variant="secondary">{getDisplayValue()}</Badge>
        </div>

        {/* Type selector */}
        <div className="space-y-2">
          <Label>{t('tokenizer.type')}</Label>
          <Select value={type} onValueChange={(v) => handleTypeChange(v as TokenizerType)}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="auto">{t('tokenizer.types.auto')}</SelectItem>
              <SelectItem value="tiktoken">{t('tokenizer.types.tiktoken')}</SelectItem>
              <SelectItem value="huggingface">{t('tokenizer.types.huggingface')}</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Type-specific options */}
        {type === 'tiktoken' && (
          <div className="space-y-2">
            <Label>{t('tokenizer.encoding')}</Label>
            <Select
              value={tokenizerName || 'cl100k_base'}
              onValueChange={handleTiktokenEncodingChange}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {TIKTOKEN_ENCODINGS.map((enc) => (
                  <SelectItem key={enc.value} value={enc.value}>
                    <div className="flex flex-col">
                      <span>{enc.label}</span>
                      <span className="text-xs text-muted-foreground">{enc.description}</span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}

        {type === 'huggingface' && (
          <div className="space-y-4">
            {/* Common tokenizers dropdown */}
            <div className="space-y-2">
              <Label>{t('tokenizer.repository')}</Label>
              <Select
                value={tokenizerName && isCommonRepo(tokenizerName) ? tokenizerName : 'custom'}
                onValueChange={handleHuggingFaceRepoChange}
                disabled={preloadTokenizer.isPending}
              >
                <SelectTrigger>
                  <SelectValue placeholder={t('tokenizer.selectRepo')} />
                </SelectTrigger>
                <SelectContent>
                  {COMMON_HF_TOKENIZERS.map((tok) => (
                    <SelectItem key={tok.value} value={tok.value}>
                      <div className="flex items-center gap-2">
                        {isTokenizerLocal(tok.value) && (
                          <Check className="h-3 w-3 text-green-500" />
                        )}
                        <span>{tok.label}</span>
                        <span className="text-xs text-muted-foreground">({tok.value})</span>
                      </div>
                    </SelectItem>
                  ))}
                  <SelectItem value="custom">
                    <span className="italic">{t('tokenizer.customRepo')}</span>
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Custom repo input */}
            {(!tokenizerName || !isCommonRepo(tokenizerName)) && (
              <div className="space-y-2">
                <Label>{t('tokenizer.customRepo')}</Label>
                <div className="flex gap-2">
                  <Input
                    value={customRepoInput || (tokenizerName && !isCommonRepo(tokenizerName) ? tokenizerName : '')}
                    onChange={(e) => setCustomRepoInput(e.target.value)}
                    placeholder={t('placeholders.huggingfaceRepo')}
                    disabled={preloadTokenizer.isPending}
                  />
                  <Button
                    type="button"
                    onClick={handleCustomRepoSubmit}
                    disabled={preloadTokenizer.isPending || !customRepoInput.trim()}
                  >
                    <Download className="h-4 w-4 mr-1" />
                    {t('tokenizer.download')}
                  </Button>
                </div>
              </div>
            )}

            {/* Loading indicator */}
            {preloadTokenizer.isPending && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>{t('tokenizer.downloading')}</span>
              </div>
            )}

            {/* Current selection status */}
            {tokenizerName && !preloadTokenizer.isPending && (
              <div className="flex items-center gap-2 text-sm">
                <span className="text-muted-foreground">{t('tokenizer.current')}:</span>
                <span className="font-mono">{tokenizerName}</span>
                {tokenizerStatus === true && <Check className="h-4 w-4 text-green-500" />}
                {tokenizerStatus === false && (
                  <>
                    <X className="h-4 w-4 text-red-500" />
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => handleDownloadTokenizer(tokenizerName)}
                    >
                      <Download className="h-3 w-3 mr-1" />
                      {t('tokenizer.retry')}
                    </Button>
                  </>
                )}
              </div>
            )}
          </div>
        )}

        {type === 'auto' && (
          <p className="text-sm text-muted-foreground">
            {t('tokenizer.autoDescription')}
          </p>
        )}
      </CardContent>
    </Card>
  );
}

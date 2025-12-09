/**
 * Prompt placeholder validation utilities.
 *
 * Validates that prompt placeholder count matches processing mode requirements.
 */

export type ProcessingMode = 'single_pass' | 'iterative';

export interface PromptValidationResult {
  valid: boolean;
  placeholderCount: number;
  requiredCount: number;
  processingMode: ProcessingMode;
}

/**
 * Count {} placeholders in prompt content.
 * Only counts empty braces {}, not named placeholders like {name}.
 */
export function countPlaceholders(content: string): number {
  if (!content) return 0;

  let count = 0;
  let i = 0;
  while (i < content.length - 1) {
    if (content[i] === '{' && content[i + 1] === '}') {
      count++;
      i += 2;
    } else {
      i++;
    }
  }
  return count;
}

/**
 * Get required placeholder count for a processing mode.
 *
 * - single_pass: 1 placeholder for content
 * - iterative: 2 placeholders (previous summary + new content)
 */
export function getRequiredPlaceholders(processingMode: ProcessingMode): number {
  return processingMode === 'iterative' ? 2 : 1;
}

/**
 * Validate prompt placeholder count against processing mode.
 *
 * Returns validation result with details about mismatch.
 */
export function validatePromptForMode(
  promptContent: string | undefined,
  processingMode: ProcessingMode
): PromptValidationResult {
  const placeholderCount = countPlaceholders(promptContent || '');
  const requiredCount = getRequiredPlaceholders(processingMode);

  return {
    valid: !promptContent || placeholderCount === requiredCount,
    placeholderCount,
    requiredCount,
    processingMode,
  };
}

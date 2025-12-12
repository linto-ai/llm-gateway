import type { DocumentTemplate, TemplateScope } from '@/types/document-template';

/**
 * Get localized template name based on current locale
 */
export function getLocalizedName(
  template: DocumentTemplate,
  locale: string = 'fr'
): string {
  if (locale === 'en' && template.name_en) {
    return template.name_en;
  }
  return template.name_fr;
}

/**
 * Get localized template description
 */
export function getLocalizedDescription(
  template: DocumentTemplate,
  locale: string = 'fr'
): string | null {
  if (locale === 'en' && template.description_en) {
    return template.description_en;
  }
  return template.description_fr;
}

/**
 * Get badge variant for scope display
 */
export function getScopeBadgeVariant(
  scope: TemplateScope
): 'default' | 'secondary' | 'outline' {
  switch (scope) {
    case 'system':
      return 'default';
    case 'organization':
      return 'secondary';
    case 'user':
      return 'outline';
  }
}

/**
 * Format file size for display
 */
export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/**
 * Get scope from template (computed from organization_id and user_id)
 */
export function getTemplateScope(template: DocumentTemplate): TemplateScope {
  if (template.scope) return template.scope;

  if (!template.organization_id && !template.user_id) {
    return 'system';
  }
  if (template.organization_id && !template.user_id) {
    return 'organization';
  }
  return 'user';
}

/**
 * Check if template belongs to a specific scope
 */
export function isTemplateInScope(
  template: DocumentTemplate,
  scope: TemplateScope
): boolean {
  return getTemplateScope(template) === scope;
}

/**
 * Filter templates by scope
 */
export function filterTemplatesByScope(
  templates: DocumentTemplate[],
  scope: TemplateScope | 'all'
): DocumentTemplate[] {
  if (scope === 'all') return templates;
  return templates.filter((t) => isTemplateInScope(t, scope));
}

/**
 * Sort templates: system first, then organization, then user
 */
export function sortTemplatesByScope(templates: DocumentTemplate[]): DocumentTemplate[] {
  const scopeOrder: Record<TemplateScope, number> = {
    system: 0,
    organization: 1,
    user: 2,
  };

  return [...templates].sort((a, b) => {
    const scopeA = getTemplateScope(a);
    const scopeB = getTemplateScope(b);
    return scopeOrder[scopeA] - scopeOrder[scopeB];
  });
}

import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

interface StatusBadgeProps {
  status: 'verified' | 'not-verified' | 'secure' | 'sensitive' | 'insecure' | 'default' | 'active' | 'inactive';
  label: string;
  className?: string;
}

export function StatusBadge({ status, label, className }: StatusBadgeProps) {
  const variantMap: Record<typeof status, string> = {
    verified: 'bg-green-500/10 text-green-700 dark:text-green-400 border-green-500/20',
    'not-verified': 'bg-red-500/10 text-red-700 dark:text-red-400 border-red-500/20',
    secure: 'bg-green-500/10 text-green-700 dark:text-green-400 border-green-500/20',
    sensitive: 'bg-yellow-500/10 text-yellow-700 dark:text-yellow-400 border-yellow-500/20',
    insecure: 'bg-red-500/10 text-red-700 dark:text-red-400 border-red-500/20',
    default: 'bg-blue-500/10 text-blue-700 dark:text-blue-400 border-blue-500/20',
    active: 'bg-green-500/10 text-green-700 dark:text-green-400 border-green-500/20',
    inactive: 'bg-gray-500/10 text-gray-700 dark:text-gray-400 border-gray-500/20',
  };

  return (
    <Badge variant="outline" className={cn(variantMap[status], className)}>
      {label}
    </Badge>
  );
}

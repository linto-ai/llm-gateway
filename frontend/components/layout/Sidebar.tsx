'use client';

import { useTranslations } from 'next-intl';
import { usePathname } from 'next/navigation';
import Link from 'next/link';
import { cn } from '@/lib/utils';
import { useUIStore } from '@/stores/ui-store';
import {
  LayoutDashboard,
  Server,
  Box,
  Wrench,
  FileText,
  Briefcase,
  Settings2,
  Files,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Sheet, SheetContent, SheetTitle } from '@/components/ui/sheet';
import { APP_NAME } from '@/lib/constants';

interface NavItem {
  href: string;
  labelKey: string;
  icon: React.ComponentType<{ className?: string }>;
}

const navItems: NavItem[] = [
  {
    href: '/',
    labelKey: 'dashboard',
    icon: LayoutDashboard,
  },
  {
    href: '/providers',
    labelKey: 'providers',
    icon: Server,
  },
  {
    href: '/models',
    labelKey: 'models',
    icon: Box,
  },
  {
    href: '/services',
    labelKey: 'services',
    icon: Wrench,
  },
  {
    href: '/prompts',
    labelKey: 'prompts',
    icon: FileText,
  },
  {
    href: '/templates',
    labelKey: 'templates',
    icon: Files,
  },
  {
    href: '/jobs',
    labelKey: 'jobs',
    icon: Briefcase,
  },
  {
    href: '/presets',
    labelKey: 'presets',
    icon: Settings2,
  },
];

function NavLinks({ locale }: { locale: string }) {
  const pathname = usePathname();
  const t = useTranslations('nav');

  return (
    <nav className="flex flex-col gap-1 p-2">
      {navItems.map((item) => {
        const Icon = item.icon;
        const fullHref = `/${locale}${item.href}`;
        const isActive = pathname === fullHref || (item.href !== '/' && pathname.startsWith(fullHref));

        return (
          <Link key={item.href} href={fullHref}>
            <Button
              variant={isActive ? 'secondary' : 'ghost'}
              className={cn(
                'w-full justify-start gap-3',
                isActive && 'bg-secondary font-medium'
              )}
            >
              <Icon className="h-4 w-4" />
              {t(item.labelKey)}
            </Button>
          </Link>
        );
      })}
    </nav>
  );
}

export function Sidebar({ locale }: { locale: string }) {
  const { sidebarOpen, setSidebarOpen } = useUIStore();

  return (
    <>
      {/* Desktop Sidebar */}
      <aside className="hidden lg:block w-64 border-r bg-background">
        <ScrollArea className="h-[calc(100vh-3.5rem)]">
          <NavLinks locale={locale} />
        </ScrollArea>
      </aside>

      {/* Mobile Sidebar */}
      <Sheet open={sidebarOpen} onOpenChange={setSidebarOpen}>
        <SheetContent side="left" className="w-64 p-0">
          <SheetTitle className="sr-only">{APP_NAME}</SheetTitle>
          <ScrollArea className="h-full">
            <NavLinks locale={locale} />
          </ScrollArea>
        </SheetContent>
      </Sheet>
    </>
  );
}

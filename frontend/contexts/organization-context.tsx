'use client';

import React, { createContext, useContext } from 'react';

/**
 * Organization Context
 * Provides a default organization ID to all forms
 * TODO: Replace with user authentication
 */

interface OrganizationContextType {
  organizationId: string;
}

const OrganizationContext = createContext<OrganizationContextType | undefined>(undefined);

interface OrganizationProviderProps {
  children: React.ReactNode;
  organizationId?: string;
}

export function OrganizationProvider({ children, organizationId }: OrganizationProviderProps) {
  // Use environment variable or fallback to a default UUID
  const defaultOrgId = organizationId ||
    process.env.NEXT_PUBLIC_DEFAULT_ORG_ID ||
    '00000000-0000-0000-0000-000000000000';

  return (
    <OrganizationContext.Provider value={{ organizationId: defaultOrgId }}>
      {children}
    </OrganizationContext.Provider>
  );
}

export function useOrganization() {
  const context = useContext(OrganizationContext);
  if (context === undefined) {
    throw new Error('useOrganization must be used within an OrganizationProvider');
  }
  return context;
}

// Flavor preset types

import type { ProcessingMode } from './service';

export interface FlavorPresetConfig {
  processing_mode: ProcessingMode;
  max_new_turns: number | null;
  summary_turns: number;
  reduce_summary: boolean;
  create_new_turn_after: number;
  temperature: number;
  top_p: number;
}

export interface FlavorPreset {
  id: string;
  name: string;
  service_type: string;
  description_en: string | null;
  description_fr: string | null;
  is_system: boolean;
  is_active: boolean;
  config: FlavorPresetConfig;
  created_at: string;
  updated_at: string;
}

export interface CreatePresetRequest {
  name: string;
  service_type: string;
  description_en?: string;
  description_fr?: string;
  config: FlavorPresetConfig;
}

export interface UpdatePresetRequest {
  name?: string;
  description_en?: string;
  description_fr?: string;
  config?: Partial<FlavorPresetConfig>;
  is_active?: boolean;
}

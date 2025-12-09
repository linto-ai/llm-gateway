// Tokenizer types based on API contract

export interface TokenizerInfo {
  id: string;
  source_repo: string;
  type: 'huggingface' | 'tiktoken';
  size_bytes: number;
  created_at: string;
}

export interface TokenizerListResponse {
  tokenizers: TokenizerInfo[];
  storage_path: string;
  total_size_bytes: number;
}

export interface TokenizerPreloadResponse {
  success: boolean;
  model_identifier: string;
  tokenizer_id: string;
  tokenizer_type: 'huggingface' | 'tiktoken';
  cached: boolean;
  message: string;
}

export interface TokenizerDeleteResponse {
  deleted: string;
  freed_bytes: number;
}

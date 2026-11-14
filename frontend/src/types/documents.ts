export interface DocumentItem {
  id: string;
  original_filename: string;
  file_type: string;
  file_size_bytes: number;
  subject?: string;
  status: 'processing' | 'ready' | 'failed';
  chunk_count: number;
  error_message?: string;
  created_at: string;
  updated_at: string;
}

export interface DocumentUploadResponse {
  success: boolean;
  message: string;
  data: DocumentItem;
}


export interface UploadedImageItem {
  id: string;
  original_filename: string;
  file_type: string;
  mime_type: string;
  file_size_bytes: number;
  width: number;
  height: number;
  extracted_text?: string;
  diagram_analysis?: string;
  created_at: string;
}

export interface ExplainImageRequest {
  image_id: string;
  question: string;
  prompt_type?: 'diagram' | 'math';
  extra_context?: string;
}

export interface MixedQueryRequest {
  text_query: string;
  image_id: string;
  document_id?: string;
}


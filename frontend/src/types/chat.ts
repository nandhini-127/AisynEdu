export interface Citation {
  document_id: string;
  document_name: string;
  page_number?: number;
  snippet?: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  created_at: string;
  citations?: Citation[];
  model_used?: string;
  agent_type?: 'tutor' | 'rag' | 'quiz' | 'summarizer' | 'summary' | 'recommender' | 'learning_path' | 'multimodal' | string;
  image_url?: string;
  image_id?: string;
  quiz_data?: any[];
  summary_data?: any;
  recommendations?: string[];
  is_fallback?: boolean;
  fallback_reason?: string;
}

export interface ChatSession {
  id: string;
  title: string;
  subject?: string;
  document_ids?: string[];
  created_at: string;
  updated_at: string;
  last_message_preview?: string;
  message_count?: number;
}

export interface SendMessageRequest {
  message: string;
  session_id?: string;
  difficulty?: 'beginner' | 'intermediate' | 'advanced';
  selected_document_ids?: string[];
  image_id?: string;
  model_provider?: 'gemini' | 'ollama';
}

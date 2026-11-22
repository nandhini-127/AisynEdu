import apiClient, { API_BASE } from './api';
import { ChatMessage, ChatSession } from '../types/chat';

export interface SendMessageParams {
  session_id: string;
  content: string;
  intent?: 'auto' | 'tutor' | 'rag' | 'quiz' | 'summarize' | 'summary' | 'learning_path';
  difficulty?: 'beginner' | 'intermediate' | 'advanced';
  document_ids?: string[];
  llm_override?: 'gemini' | 'ollama';
  question_count?: number;
}

export interface SendMessageResponse {
  user_message: any;
  assistant_message: any;
  resolved_intent: string;
  router_reasoning: string;
  is_document_grounded: boolean;
}

export const chatService = {
  async listSessions(): Promise<ChatSession[]> {
    const res = await apiClient.get('/chat/sessions');
    return (res.data?.data || []).map((s: any) => ({
      id: s.id,
      title: s.title || s.subject || 'Untitled Session',
      created_at: s.created_at,
      updated_at: s.updated_at,
      subject: s.subject,
      document_ids: s.document_ids || [],
    }));
  },

  async createSession(subject: string, title?: string, documentIds: string[] = []): Promise<ChatSession> {
    const res = await apiClient.post('/chat/sessions', {
      subject,
      title: title || subject,
      document_ids: documentIds,
    });
    const s = res.data?.data;
    return {
      id: s.id,
      title: s.title || s.subject,
      created_at: s.created_at,
      updated_at: s.updated_at,
      subject: s.subject,
      document_ids: s.document_ids || [],
    };
  },

  async getSessionMessages(sessionId: string): Promise<ChatMessage[]> {
    const res = await apiClient.get(`/chat/sessions/${sessionId}/messages`);
    const messages = res.data?.data || [];
    return messages.map((m: any) => ({
      id: m.id,
      role: m.role,
      content: m.content,
      created_at: m.created_at,
      citations: m.sources || [],
      model_used: m.llm_provider,
      agent_type: m.intent,
      quiz_data: m.quiz_data,
      summary_data: m.summary_data,
      recommendations: m.recommendations,
      is_fallback: m.is_fallback,
      fallback_reason: m.fallback_reason,
    }));
  },

  async sendMessage(params: SendMessageParams): Promise<SendMessageResponse> {
    const res = await apiClient.post('/chat/message', {
      session_id: params.session_id,
      content: params.content,
      intent: params.intent || 'auto',
      difficulty: params.difficulty || 'intermediate',
      document_ids: params.document_ids || [],
      llm_override: params.llm_override,
      question_count: params.question_count,
    });
    return res.data?.data;
  },

  async streamMessage(
    params: SendMessageParams,
    callbacks: {
      onIntent?: (data: { intent: string; is_grounded: boolean }) => void;
      onCitations?: (citations: any[]) => void;
      onToken?: (token: string) => void;
      onDone?: (data: { message_id: string; tokens: number; latency_ms: number }) => void;
      onError?: (error: string) => void;
    },
    signal?: AbortSignal
  ): Promise<void> {
    const token = localStorage.getItem('edunex_access_token');
    const response = await fetch(`${API_BASE}/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        session_id: params.session_id,
        content: params.content,
        intent: params.intent || 'auto',
        difficulty: params.difficulty || 'intermediate',
        document_ids: params.document_ids || [],
        llm_override: params.llm_override,
        question_count: params.question_count,
      }),
      signal,
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to connect to streaming endpoint');
    }

    const reader = response.body?.getReader();
    if (!reader) return;

    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (!line.trim()) continue;
        const eventMatch = line.match(/^event:\s*(\w+)/m);
        const dataMatch = line.match(/^data:\s*(.+)$/m);

        if (eventMatch && dataMatch) {
          const eventType = eventMatch[1];
          try {
            const data = JSON.parse(dataMatch[1]);
            if (eventType === 'intent' && callbacks.onIntent) {
              callbacks.onIntent(data);
            } else if (eventType === 'citations' && callbacks.onCitations) {
              callbacks.onCitations(data);
            } else if (eventType === 'token' && callbacks.onToken) {
              callbacks.onToken(data.chunk);
            } else if (eventType === 'done' && callbacks.onDone) {
              callbacks.onDone(data);
            } else if (eventType === 'error' && callbacks.onError) {
              callbacks.onError(data.error);
            }
          } catch (e) {
            // Ignore line parse issues
          }
        }
      }
    }
  },

  async clearSessionMessages(sessionId: string): Promise<void> {
    await apiClient.delete(`/chat/sessions/${sessionId}/messages`);
  },

  async exportNotesPDF(params: {
    title: string;
    subject?: string;
    content: string;
  }): Promise<Blob> {
    const res = await apiClient.post('/chat/export-pdf', params, {
      responseType: 'blob',
    });
    return res.data;
  },
};

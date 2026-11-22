import apiClient from './api';
import { DocumentItem } from '../types/documents';

export const documentService = {
  async listDocuments(): Promise<DocumentItem[]> {
    const res = await apiClient.get('/documents');
    return res.data?.data || [];
  },

  async uploadDocument(file: File, subject?: string): Promise<DocumentItem> {
    const formData = new FormData();
    formData.append('file', file);
    if (subject) {
      formData.append('subject', subject);
    }

    const res = await apiClient.post('/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    const payload = res.data?.data;
    if (payload?.document) {
      return payload.document;
    }
    return payload;
  },

  async getDocument(documentId: string): Promise<DocumentItem> {
    const res = await apiClient.get(`/documents/${documentId}`);
    return res.data?.data;
  },

  async deleteDocument(documentId: string): Promise<void> {
    await apiClient.delete(`/documents/${documentId}`);
  },
};


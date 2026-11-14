import apiClient from './api';
import { UploadedImageItem } from '../types/multimodal';

export const multimodalService = {
  async uploadImage(file: File): Promise<UploadedImageItem> {
    const formData = new FormData();
    formData.append('file', file);
    const res = await apiClient.post('/multimodal/upload-image', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return res.data?.data;
  },

  async explainImage(
    imageId: string,
    question: string,
    promptType: 'diagram' | 'math' = 'diagram',
    extraContext?: string
  ): Promise<{ explanation: string; detected_concept?: string }> {
    const res = await apiClient.post('/multimodal/explain-image', {
      image_id: imageId,
      question,
      prompt_type: promptType,
      extra_context: extraContext,
    });
    return res.data?.data;
  },

  async mixedQuery(
    textQuery: string,
    imageId: string,
    documentId?: string
  ): Promise<{ answer: string; image_used: boolean; citations?: any[] }> {
    const res = await apiClient.post('/multimodal/mixed-query', {
      text_query: textQuery,
      image_id: imageId,
      document_id: documentId,
    });
    return res.data?.data;
  },

  async queryPdfPage(
    documentId: string,
    pageNumber: number,
    question: string
  ): Promise<{ answer: string; citations: any[]; page_number: number }> {
    const res = await apiClient.post('/multimodal/pdf-page-query', {
      document_id: documentId,
      page_number: pageNumber,
      question,
    });
    return res.data?.data;
  },

  async listImages(): Promise<UploadedImageItem[]> {
    const res = await apiClient.get('/multimodal/images');
    return res.data?.data || [];
  },

  async deleteImage(imageId: string): Promise<void> {
    await apiClient.delete(`/multimodal/images/${imageId}`);
  },
};


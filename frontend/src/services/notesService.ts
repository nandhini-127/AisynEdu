import apiClient from './api';

export interface SavedNote {
  id: string;
  title: string;
  subject: string;
  content: string;
  document_id?: string | null;
  created_at: string;
}

function getUserNotesKey(userId?: string): string {
  if (userId) return `edunex_saved_study_notes_${userId}`;
  try {
    const rawUser = localStorage.getItem('edunex_user');
    if (rawUser) {
      const u = JSON.parse(rawUser);
      if (u?.id) return `edunex_saved_study_notes_${u.id}`;
    }
  } catch {
    // Ignore parse error
  }
  return 'edunex_saved_study_notes_anonymous';
}

export const notesService = {
  async listNotes(userId?: string): Promise<SavedNote[]> {
    const key = getUserNotesKey(userId);
    try {
      const res = await apiClient.get('/notes');
      const serverNotes = res.data?.data;
      if (Array.isArray(serverNotes)) {
        localStorage.setItem(key, JSON.stringify(serverNotes));
        return serverNotes;
      }
    } catch {
      // Fallback to user-scoped local storage cache
    }
    return notesService.getCachedNotes(userId);
  },

  getCachedNotes(userId?: string): SavedNote[] {
    const key = getUserNotesKey(userId);
    try {
      const raw = localStorage.getItem(key);
      return raw ? JSON.parse(raw) : [];
    } catch {
      return [];
    }
  },

  async createNote(
    data: {
      title: string;
      subject: string;
      content: string;
      document_id?: string;
    },
    userId?: string
  ): Promise<SavedNote> {
    const key = getUserNotesKey(userId);
    let createdNote: SavedNote;
    try {
      const res = await apiClient.post('/notes', data);
      createdNote = res.data?.data;
    } catch {
      // Graceful offline fallback
      createdNote = {
        id: `note-${Date.now()}`,
        title: data.title,
        subject: data.subject,
        content: data.content,
        document_id: data.document_id,
        created_at: new Date().toISOString(),
      };
    }

    try {
      const current = notesService.getCachedNotes(userId);
      const updated = [createdNote, ...current.filter((n) => n.id !== createdNote.id)];
      localStorage.setItem(key, JSON.stringify(updated));
    } catch {
      // Ignore
    }

    return createdNote;
  },

  async deleteNote(noteId: string, userId?: string): Promise<void> {
    const key = getUserNotesKey(userId);
    try {
      await apiClient.delete(`/notes/${noteId}`);
    } catch {
      // Ignore
    }
    try {
      const current = notesService.getCachedNotes(userId);
      const updated = current.filter((n) => n.id !== noteId);
      localStorage.setItem(key, JSON.stringify(updated));
    } catch {
      // Ignore
    }
  },

  clearUserCache(userId?: string): void {
    const key = getUserNotesKey(userId);
    localStorage.removeItem(key);
    localStorage.removeItem('edunex_saved_study_notes'); // Clean up any legacy shared cache
  },
};

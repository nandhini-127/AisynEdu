import React, { useRef, useState } from 'react';
import {
  BookOpen,
  Brain,
  Cpu,
  FileQuestion,
  FileText,
  Image as ImageIcon,
  Loader2,
  Paperclip,
  Send,
  Sparkles,
  X,
} from 'lucide-react';
import { Button } from '../common/Button';

interface ChatInputProps {
  onSend: (params: {
    message: string;
    intent: 'auto' | 'tutor' | 'rag' | 'quiz' | 'summary' | 'learning_path';
    difficulty: 'beginner' | 'intermediate' | 'advanced';
    llmProvider: 'gemini' | 'ollama';
    imageId?: string;
  }) => void;
  isLoading: boolean;
  onOpenImageModal: () => void;
  selectedImage?: { id: string; filename: string } | null;
  onClearSelectedImage?: () => void;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  onSend,
  isLoading,
  onOpenImageModal,
  selectedImage,
  onClearSelectedImage,
}) => {
  const [content, setContent] = useState('');
  const [intent, setIntent] = useState<'auto' | 'tutor' | 'rag' | 'quiz' | 'summary' | 'learning_path'>('auto');
  const [difficulty, setDifficulty] = useState<'beginner' | 'intermediate' | 'advanced'>('intermediate');
  const [llmProvider, setLlmProvider] = useState<'gemini' | 'ollama'>('gemini');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!content.trim() || isLoading) return;

    onSend({
      message: content.trim(),
      intent,
      difficulty,
      llmProvider,
      imageId: selectedImage?.id,
    });

    setContent('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleTextChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setContent(e.target.value);
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`;
    }
  };

  const intentOptions = [
    { value: 'auto', label: 'Auto (Smart Assistant)', icon: Sparkles },
    { value: 'tutor', label: 'Concept Explanation', icon: Brain },
    { value: 'rag', label: 'Search Study Notes', icon: BookOpen },
    { value: 'quiz', label: 'Practice Quiz', icon: FileQuestion },
    { value: 'summary', label: 'Summarize Notes', icon: FileText },
  ];

  return (
    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-lg p-3 sm:p-4">
      {/* Selected Image Banner */}
      {selectedImage && (
        <div className="flex items-center justify-between mb-3 px-3 py-1.5 rounded-xl bg-primary-50 dark:bg-primary-950/60 border border-primary-200 dark:border-primary-800 text-xs">
          <div className="flex items-center gap-2 text-primary-700 dark:text-primary-300 font-medium">
            <ImageIcon className="w-4 h-4" />
            <span>Attached Diagram: <strong className="font-semibold">{selectedImage.filename}</strong></span>
          </div>
          {onClearSelectedImage && (
            <button
              onClick={onClearSelectedImage}
              className="p-1 rounded-md text-primary-600 hover:text-primary-800 dark:hover:text-primary-200 hover:bg-primary-100 dark:hover:bg-primary-900"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      )}

      {/* Input area */}
      <div className="relative">
        <textarea
          ref={textareaRef}
          value={content}
          onChange={handleTextChange}
          onKeyDown={handleKeyDown}
          placeholder="Ask a question, request a concept breakdown, or generate a quiz..."
          rows={1}
          className="w-full resize-none bg-transparent text-sm text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none min-h-[44px] max-h-[180px] py-2.5 px-2"
        />
      </div>

      {/* Controls Bar */}
      <div className="flex flex-wrap items-center justify-between gap-2 pt-3 border-t border-slate-100 dark:border-slate-800 text-xs">
        {/* Left: Capability & Settings selectors */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Intent selector */}
          <select
            value={intent}
            onChange={(e) => setIntent(e.target.value as any)}
            className="px-2.5 py-1.5 rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 font-medium focus:outline-none"
          >
            {intentOptions.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>

          {/* Difficulty selector */}
          <select
            value={difficulty}
            onChange={(e) => setDifficulty(e.target.value as any)}
            className="px-2.5 py-1.5 rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 font-medium focus:outline-none"
          >
            <option value="beginner">Beginner</option>
            <option value="intermediate">Intermediate</option>
            <option value="advanced">Advanced</option>
          </select>

          {/* AI study engine toggle */}
          <button
            type="button"
            onClick={() => setLlmProvider((prev) => (prev === 'gemini' ? 'ollama' : 'gemini'))}
            title="Switch study tutor engine"
            className={`inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg border font-medium transition-colors ${
              llmProvider === 'gemini'
                ? 'bg-indigo-50 border-indigo-200 text-indigo-700 dark:bg-indigo-950/60 dark:border-indigo-800 dark:text-indigo-300'
                : 'bg-emerald-50 border-emerald-200 text-emerald-700 dark:bg-emerald-950/60 dark:border-emerald-800 dark:text-emerald-300'
            }`}
          >
            <Cpu className="w-3.5 h-3.5" />
            <span>{llmProvider === 'gemini' ? 'Gemini Flash' : 'Local Tutor'}</span>
          </button>

          {/* Image/multimodal trigger button */}
          <button
            type="button"
            onClick={onOpenImageModal}
            title="Attach educational diagram or math illustration"
            className="p-1.5 rounded-lg text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          >
            <ImageIcon className="w-4 h-4" />
          </button>
        </div>

        {/* Right: Submit Button */}
        <Button
          size="sm"
          onClick={() => handleSubmit()}
          disabled={!content.trim() || isLoading}
          isLoading={isLoading}
          rightIcon={<Send className="w-3.5 h-3.5" />}
        >
          Send
        </Button>
      </div>
    </div>
  );
};


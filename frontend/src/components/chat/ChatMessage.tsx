import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import { AlertTriangle, Bot, CheckCircle2, ChevronRight, HelpCircle, Sparkles, User } from 'lucide-react';
import { ChatMessage as ChatMessageType } from '../../types/chat';
import { CitationBadge } from './CitationBadge';
import { Badge } from '../common/Badge';

interface ChatMessageProps {
  message: ChatMessageType;
  onSelectTopic?: (topic: string) => void;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({ message, onSelectTopic }) => {
  const isUser = message.role === 'user';

  const intentBadges: Record<string, { label: string; variant: 'primary' | 'success' | 'warning' | 'purple' | 'slate' }> = {
    tutor: { label: 'TUTOR', variant: 'primary' },
    rag: { label: 'FROM STUDY NOTES', variant: 'success' },
    quiz: { label: 'PRACTICE QUIZ', variant: 'warning' },
    summary: { label: 'REVISION NOTES', variant: 'purple' },
    learning_path: { label: 'STUDY COACH', variant: 'primary' },
    multimodal: { label: 'DIAGRAM ANALYSIS', variant: 'primary' },
  };

  const badgeInfo = message.agent_type ? intentBadges[message.agent_type] : null;

  return (
    <div className={`flex gap-3.5 sm:gap-4 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      {/* Avatar */}
      <div
        className={`w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0 text-white font-semibold text-xs shadow-sm ${
          isUser
            ? 'bg-primary-600'
            : 'bg-gradient-to-tr from-indigo-600 to-primary-500'
        }`}
      >
        {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
      </div>

      {/* Message Body */}
      <div className={`flex-1 max-w-3xl ${isUser ? 'items-end' : 'items-start'}`}>
        <div className="flex items-center gap-2 mb-1.5 px-1">
          <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">
            {isUser ? 'You' : 'AisynEdu'}
          </span>
          {badgeInfo && (
            <Badge variant={badgeInfo.variant} size="sm">
              {badgeInfo.label}
            </Badge>
          )}
          {message.model_used && (
            <span className="text-[10px] text-slate-400 font-mono">
              {message.model_used}
            </span>
          )}
          <span className="text-[10px] text-slate-400 ml-auto">
            {new Date(message.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
        </div>

        {/* Bubble */}
        <div
          className={`rounded-2xl px-5 py-3.5 text-sm leading-relaxed shadow-sm ${
            isUser
              ? 'bg-primary-600 text-white rounded-tr-none'
              : 'bg-white dark:bg-slate-900 border border-slate-200/80 dark:border-slate-800 text-slate-900 dark:text-slate-100 rounded-tl-none'
          }`}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap">{message.content}</p>
          ) : (
            <>
              {message.is_fallback && (
                <div className="mb-3 px-3 py-2 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-700 dark:text-amber-300 text-xs flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 shrink-0 text-amber-500" />
                  <span>
                    {message.fallback_reason || 'Live AI generation is temporarily unavailable. Showing topic-aware curriculum explanation.'}
                  </span>
                </div>
              )}
              <div className="prose dark:prose-invert prose-sm max-w-none prose-pre:bg-slate-950 prose-pre:border prose-pre:border-slate-800 prose-headings:font-bold prose-headings:text-slate-900 dark:prose-headings:text-slate-100">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm, remarkMath]}
                  rehypePlugins={[rehypeKatex]}
                >
                  {message.content}
                </ReactMarkdown>
              </div>
            </>
          )}

          {/* Embedded Quiz Data */}
          {(message as any).quiz_data && Array.isArray((message as any).quiz_data) && (
            <div className="mt-4 pt-4 border-t border-slate-200 dark:border-slate-800 space-y-3">
              <div className="flex items-center gap-1.5 text-xs font-bold text-amber-600 dark:text-amber-400 uppercase tracking-wider">
                <HelpCircle className="w-4 h-4" /> Practice Questions
              </div>
              {(message as any).quiz_data.map((q: any, qIdx: number) => (
                <div key={qIdx} className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700">
                  <p className="font-semibold text-xs text-slate-800 dark:text-slate-100 mb-2">
                    {qIdx + 1}. {q.question}
                  </p>
                  <div className="space-y-1.5">
                    {q.options?.map((opt: string, optIdx: number) => (
                      <div
                        key={optIdx}
                        className="px-3 py-1.5 rounded-lg text-xs bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 flex items-center justify-between"
                      >
                        <span>{opt}</span>
                        {q.correct_index === optIdx && (
                          <span className="text-[10px] font-bold text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
                            <CheckCircle2 className="w-3 h-3" /> Correct
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                  {q.explanation && (
                    <p className="mt-2 text-[11px] text-slate-500 dark:text-slate-400 italic">
                      Why: {q.explanation}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Embedded Learning Recommendations */}
          {(message as any).recommendations && Array.isArray((message as any).recommendations) && (
            <div className="mt-3 pt-3 border-t border-slate-200 dark:border-slate-800">
              <p className="text-[11px] font-semibold text-primary-600 dark:text-primary-400 flex items-center gap-1 mb-2">
                <Sparkles className="w-3.5 h-3.5" /> Recommended Next Topics:
              </p>
              <div className="flex flex-wrap gap-1.5">
                {(message as any).recommendations.map((rec: string, i: number) => (
                  <button
                    key={i}
                    onClick={() => onSelectTopic && onSelectTopic(rec)}
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium bg-primary-50 hover:bg-primary-100 dark:bg-primary-950/60 dark:hover:bg-primary-900/60 text-primary-700 dark:text-primary-300 transition-colors border border-primary-200 dark:border-primary-800"
                  >
                    <span>{rec}</span>
                    <ChevronRight className="w-3 h-3" />
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Citations Footer */}
        {message.citations && message.citations.length > 0 && (
          <div className="flex flex-wrap items-center gap-2 mt-2 px-1">
            <span className="text-[11px] font-medium text-slate-400">Sources:</span>
            {message.citations.map((cite, idx) => (
              <CitationBadge key={idx} citation={cite} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};


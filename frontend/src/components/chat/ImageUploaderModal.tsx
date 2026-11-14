import React, { useRef, useState } from 'react';
import { Eye, FileCode, Image as ImageIcon, Loader2, Sparkles, UploadCloud, X } from 'lucide-react';
import { Modal } from '../common/Modal';
import { Button } from '../common/Button';
import { multimodalService } from '../../services/multimodalService';

interface ImageUploaderModalProps {
  isOpen: boolean;
  onClose: () => void;
  onImageSelected: (image: { id: string; filename: string }) => void;
  onDirectExplain?: (explanation: string, imageId: string) => void;
}

export const ImageUploaderModal: React.FC<ImageUploaderModalProps> = ({
  isOpen,
  onClose,
  onImageSelected,
  onDirectExplain,
}) => {
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [analysisType, setAnalysisType] = useState<'diagram' | 'math'>('diagram');
  const [question, setQuestion] = useState('Explain this educational diagram and its core components.');
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selected = e.target.files[0];
      if (selected.size > 10 * 1024 * 1024) {
        setError('Image file exceeds the 10 MB limit.');
        return;
      }
      setFile(selected);
      setError(null);
      setPreviewUrl(URL.createObjectURL(selected));
    }
  };

  const handleUploadAndAttach = async () => {
    if (!file) return;
    setIsUploading(true);
    setError(null);
    try {
      const uploaded = await multimodalService.uploadImage(file);
      onImageSelected({ id: uploaded.id, filename: uploaded.original_filename });
      onClose();
    } catch (err: any) {
      setError(err?.response?.data?.message || 'Failed to upload image.');
    } finally {
      setIsUploading(false);
    }
  };

  const handleDirectExplain = async () => {
    if (!file) return;
    setIsUploading(true);
    setError(null);
    try {
      const uploaded = await multimodalService.uploadImage(file);
      const res = await multimodalService.explainImage(uploaded.id, question, analysisType);
      if (onDirectExplain) {
        onDirectExplain(res.explanation, uploaded.id);
      }
      onClose();
    } catch (err: any) {
      setError(err?.response?.data?.message || 'Failed to analyze diagram.');
    } finally {
      setIsUploading(false);
    }
  };

  const resetState = () => {
    setFile(null);
    setPreviewUrl(null);
    setError(null);
    onClose();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={resetState}
      title="Upload Diagram / Math Illustration"
      description="Attach educational diagrams, architecture maps, or math equations for multimodal understanding."
      maxWidth="lg"
    >
      <div className="space-y-4">
        {/* Drop area */}
        {!previewUrl ? (
          <div
            onClick={() => fileInputRef.current?.click()}
            className="border-2 border-dashed border-slate-300 dark:border-slate-700 hover:border-primary-500 dark:hover:border-primary-400 rounded-2xl p-8 text-center cursor-pointer transition-colors bg-slate-50/50 dark:bg-slate-800/30"
          >
            <input
              ref={fileInputRef}
              type="file"
              accept="image/png,image/jpeg,image/webp"
              onChange={handleFileChange}
              className="hidden"
            />
            <div className="w-12 h-12 rounded-xl bg-primary-50 dark:bg-primary-950/50 text-primary-600 dark:text-primary-400 flex items-center justify-center mx-auto mb-3">
              <UploadCloud className="w-6 h-6" />
            </div>
            <p className="text-sm font-semibold text-slate-800 dark:text-slate-200">
              Click or drag diagram to upload
            </p>
            <p className="text-xs text-slate-400 mt-1">PNG, JPEG, WebP up to 10 MB</p>
          </div>
        ) : (
          <div className="relative rounded-2xl overflow-hidden border border-slate-200 dark:border-slate-800 bg-slate-900/5 max-h-56 flex items-center justify-center">
            <img src={previewUrl} alt="Preview" className="object-contain max-h-56" />
            <button
              onClick={() => {
                setFile(null);
                setPreviewUrl(null);
              }}
              className="absolute top-2 right-2 p-1.5 rounded-full bg-slate-900/70 text-white hover:bg-slate-900 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Options */}
        {file && (
          <div className="space-y-3 pt-2">
            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Analysis Mode
              </label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => {
                    setAnalysisType('diagram');
                    setQuestion('Explain this educational diagram and its core components.');
                  }}
                  className={`p-2.5 rounded-xl border text-xs font-semibold flex items-center gap-2 transition-colors ${
                    analysisType === 'diagram'
                      ? 'border-primary-500 bg-primary-50 text-primary-700 dark:bg-primary-950/60 dark:text-primary-300'
                      : 'border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400'
                  }`}
                >
                  <ImageIcon className="w-4 h-4 text-primary-600" />
                  <span>Diagram / Flowchart</span>
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setAnalysisType('math');
                    setQuestion('Derive and explain the mathematical formulas and geometric relations depicted.');
                  }}
                  className={`p-2.5 rounded-xl border text-xs font-semibold flex items-center gap-2 transition-colors ${
                    analysisType === 'math'
                      ? 'border-indigo-500 bg-indigo-50 text-indigo-700 dark:bg-indigo-950/60 dark:text-indigo-300'
                      : 'border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400'
                  }`}
                >
                  <FileCode className="w-4 h-4 text-indigo-600" />
                  <span>Math / Plot / Formulas</span>
                </button>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
                Your Specific Question
              </label>
              <input
                type="text"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                className="w-full rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 px-3 py-2 text-xs text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-primary-500/20"
              />
            </div>
          </div>
        )}

        {error && <p className="text-xs text-red-500 font-medium">{error}</p>}

        {/* Action Buttons */}
        <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-100 dark:border-slate-800">
          <Button variant="outline" size="sm" onClick={resetState}>
            Cancel
          </Button>
          {file && (
            <>
              <Button
                variant="secondary"
                size="sm"
                onClick={handleUploadAndAttach}
                isLoading={isUploading}
              >
                Attach to Chat
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={handleDirectExplain}
                isLoading={isUploading}
                leftIcon={<Sparkles className="w-3.5 h-3.5" />}
              >
                Analyze with Vision
              </Button>
            </>
          )}
        </div>
      </div>
    </Modal>
  );
};


import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, GraduationCap } from 'lucide-react';
import { Button } from '../components/common/Button';

export const NotFoundPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 flex flex-col items-center justify-center p-4 text-center">
      <div className="w-16 h-16 rounded-2xl bg-primary-50 dark:bg-primary-950/50 text-primary-600 flex items-center justify-center mb-6">
        <GraduationCap className="w-9 h-9" />
      </div>
      <h1 className="text-6xl font-black text-slate-900 dark:text-white tracking-tight">404</h1>
      <h2 className="text-xl font-bold text-slate-800 dark:text-slate-200 mt-2">
        Page Not Found
      </h2>
      <p className="text-xs text-slate-500 dark:text-slate-400 max-w-sm mt-1 mb-8">
        The educational page or study resource you are looking for does not exist or has been moved.
      </p>
      <Link to="/dashboard">
        <Button leftIcon={<ArrowLeft className="w-4 h-4" />}>Back to Dashboard</Button>
      </Link>
    </div>
  );
};


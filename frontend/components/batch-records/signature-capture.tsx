'use client';

import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { X, PenTool, AlertCircle, Eye, EyeOff } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { signStep } from '@/lib/api/batch-records';

interface SignatureCaptureProps {
  stepId: string;
  meaning: string;
  onClose: () => void;
  onComplete: () => void;
}

export function SignatureCapture({
  stepId,
  meaning,
  onClose,
  onComplete,
}: SignatureCaptureProps) {
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');

  const signMutation = useMutation({
    mutationFn: () => signStep(stepId, password, meaning),
    onSuccess: () => {
      onComplete();
    },
    onError: (error: Error & { response?: { data?: { error?: string } } }) => {
      setError(error.response?.data?.error || 'Failed to apply signature');
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!password.trim()) {
      setError('Password is required');
      return;
    }
    setError('');
    signMutation.mutate();
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      <div className="flex min-h-full items-center justify-center p-4">
        {/* Backdrop */}
        <div className="fixed inset-0 bg-black/50" onClick={onClose} />

        {/* Modal */}
        <div className="relative bg-white dark:bg-gray-800 rounded-lg shadow-xl w-full max-w-md">
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-100 dark:bg-blue-900 rounded-lg">
                <PenTool className="w-5 h-5 text-blue-600 dark:text-blue-400" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                  Digital Signature Required
                </h2>
                <p className="text-sm text-gray-500">
                  FDA 21 CFR Part 11 Compliant
                </p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Content */}
          <form onSubmit={handleSubmit}>
            <div className="p-4 space-y-4">
              {/* Signature Meaning */}
              <div className="p-4 bg-gray-50 dark:bg-gray-700 rounded-lg">
                <p className="text-sm text-gray-500 dark:text-gray-400 mb-1">
                  Signature Meaning
                </p>
                <p className="font-medium text-gray-900 dark:text-white">
                  &quot;{meaning}&quot;
                </p>
              </div>

              {/* Legal Notice */}
              <div className="p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg text-sm text-yellow-800 dark:text-yellow-300">
                <p>
                  By signing below, you attest that the information provided is
                  accurate and complete to the best of your knowledge. This
                  electronic signature is legally binding.
                </p>
              </div>

              {error && (
                <div className="flex items-center gap-2 p-3 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 rounded-lg">
                  <AlertCircle className="w-5 h-5 flex-shrink-0" />
                  <span className="text-sm">{error}</span>
                </div>
              )}

              {/* Password Input */}
              <div className="space-y-1">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Enter your password to sign
                </label>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full px-3 py-2 pr-10 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="Enter your password"
                    autoComplete="current-password"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  >
                    {showPassword ? (
                      <EyeOff className="w-4 h-4" />
                    ) : (
                      <Eye className="w-4 h-4" />
                    )}
                  </button>
                </div>
                <p className="text-xs text-gray-500">
                  Your password is used to verify your identity for this signature.
                </p>
              </div>

              {/* Timestamp */}
              <div className="text-sm text-gray-500 dark:text-gray-400">
                <p>
                  Signature timestamp:{' '}
                  <span className="font-mono">
                    {new Date().toISOString()}
                  </span>
                </p>
              </div>
            </div>

            {/* Footer */}
            <div className="flex items-center justify-end gap-3 p-4 border-t border-gray-200 dark:border-gray-700">
              <Button type="button" variant="outline" onClick={onClose}>
                Cancel
              </Button>
              <Button type="submit" loading={signMutation.isPending}>
                <PenTool className="w-4 h-4 mr-2" />
                Apply Signature
              </Button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

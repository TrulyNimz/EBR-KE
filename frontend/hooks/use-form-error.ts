/**
 * Hook for handling form errors with react-hook-form integration.
 */
import { useCallback, useState } from 'react';
import { UseFormSetError, FieldValues, Path } from 'react-hook-form';
import {
  isValidationError,
  isAuthenticationError,
  isPermissionError,
  isNetworkError,
  getErrorMessage,
  ValidationError,
} from '@/lib/errors';
import { useToast } from './use-toast';
import { useRouter } from 'next/navigation';

interface UseFormErrorOptions<T extends FieldValues> {
  setError?: UseFormSetError<T>;
  onAuthError?: () => void;
  onPermissionError?: () => void;
  showToast?: boolean;
}

interface UseFormErrorReturn {
  error: string | null;
  clearError: () => void;
  handleError: (error: unknown) => void;
}

/**
 * Hook for consistent form error handling.
 */
export function useFormError<T extends FieldValues>(
  options: UseFormErrorOptions<T> = {}
): UseFormErrorReturn {
  const { setError, onAuthError, onPermissionError, showToast = true } = options;
  const [error, setErrorState] = useState<string | null>(null);
  const toast = useToast();
  const router = useRouter();

  const clearError = useCallback(() => {
    setErrorState(null);
  }, []);

  const handleError = useCallback(
    (err: unknown) => {
      // Handle validation errors
      if (isValidationError(err) && setError) {
        const fieldErrors = (err as ValidationError).getFlatFieldErrors();

        // Set field-level errors
        Object.entries(fieldErrors).forEach(([field, message]) => {
          setError(field as Path<T>, {
            type: 'server',
            message,
          });
        });

        // Set general error
        setErrorState(err.message);

        if (showToast) {
          toast.error({
            title: 'Validation Error',
            message: 'Please check the form for errors',
          });
        }
        return;
      }

      // Handle authentication errors
      if (isAuthenticationError(err)) {
        if (onAuthError) {
          onAuthError();
        } else {
          router.push('/login');
        }

        if (showToast) {
          toast.error({
            title: 'Authentication Required',
            message: 'Please log in to continue',
          });
        }
        return;
      }

      // Handle permission errors
      if (isPermissionError(err)) {
        if (onPermissionError) {
          onPermissionError();
        }

        setErrorState(getErrorMessage(err));

        if (showToast) {
          toast.error({
            title: 'Permission Denied',
            message: getErrorMessage(err),
          });
        }
        return;
      }

      // Handle network errors
      if (isNetworkError(err)) {
        setErrorState('Unable to connect. Please check your internet connection.');

        if (showToast) {
          toast.error({
            title: 'Network Error',
            message: 'Please check your internet connection',
          });
        }
        return;
      }

      // Generic error
      const message = getErrorMessage(err);
      setErrorState(message);

      if (showToast) {
        toast.error({
          title: 'Error',
          message,
        });
      }
    },
    [setError, onAuthError, onPermissionError, showToast, toast, router]
  );

  return {
    error,
    clearError,
    handleError,
  };
}

/**
 * Hook for async operations with error handling.
 */
interface UseAsyncOptions {
  onSuccess?: () => void;
  onError?: (error: unknown) => void;
  showSuccessToast?: boolean;
  showErrorToast?: boolean;
  successMessage?: string;
}

interface UseAsyncReturn<T> {
  loading: boolean;
  error: string | null;
  execute: (fn: () => Promise<T>) => Promise<T | undefined>;
  reset: () => void;
}

export function useAsync<T = void>(options: UseAsyncOptions = {}): UseAsyncReturn<T> {
  const {
    onSuccess,
    onError,
    showSuccessToast = false,
    showErrorToast = true,
    successMessage,
  } = options;

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const toast = useToast();

  const reset = useCallback(() => {
    setLoading(false);
    setError(null);
  }, []);

  const execute = useCallback(
    async (fn: () => Promise<T>): Promise<T | undefined> => {
      setLoading(true);
      setError(null);

      try {
        const result = await fn();

        if (showSuccessToast && successMessage) {
          toast.success({
            title: 'Success',
            message: successMessage,
          });
        }

        onSuccess?.();
        return result;
      } catch (err) {
        const message = getErrorMessage(err);
        setError(message);

        if (showErrorToast) {
          toast.error({
            title: 'Error',
            message,
          });
        }

        onError?.(err);
        return undefined;
      } finally {
        setLoading(false);
      }
    },
    [onSuccess, onError, showSuccessToast, showErrorToast, successMessage, toast]
  );

  return {
    loading,
    error,
    execute,
    reset,
  };
}

/**
 * Hook for mutation operations (create, update, delete).
 */
interface UseMutationOptions<TData, TVariables> {
  mutationFn: (variables: TVariables) => Promise<TData>;
  onSuccess?: (data: TData, variables: TVariables) => void;
  onError?: (error: unknown, variables: TVariables) => void;
  onSettled?: (data: TData | undefined, error: unknown | null, variables: TVariables) => void;
  successMessage?: string;
  errorMessage?: string;
}

interface UseMutationReturn<TData, TVariables> {
  mutate: (variables: TVariables) => Promise<TData | undefined>;
  mutateAsync: (variables: TVariables) => Promise<TData>;
  isLoading: boolean;
  isError: boolean;
  isSuccess: boolean;
  error: string | null;
  data: TData | undefined;
  reset: () => void;
}

export function useMutation<TData = void, TVariables = void>(
  options: UseMutationOptions<TData, TVariables>
): UseMutationReturn<TData, TVariables> {
  const {
    mutationFn,
    onSuccess,
    onError,
    onSettled,
    successMessage,
    errorMessage,
  } = options;

  const [isLoading, setIsLoading] = useState(false);
  const [isError, setIsError] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<TData | undefined>(undefined);
  const toast = useToast();

  const reset = useCallback(() => {
    setIsLoading(false);
    setIsError(false);
    setIsSuccess(false);
    setError(null);
    setData(undefined);
  }, []);

  const mutateAsync = useCallback(
    async (variables: TVariables): Promise<TData> => {
      setIsLoading(true);
      setIsError(false);
      setIsSuccess(false);
      setError(null);

      try {
        const result = await mutationFn(variables);
        setData(result);
        setIsSuccess(true);

        if (successMessage) {
          toast.success({
            title: 'Success',
            message: successMessage,
          });
        }

        onSuccess?.(result, variables);
        onSettled?.(result, null, variables);

        return result;
      } catch (err) {
        const message = errorMessage || getErrorMessage(err);
        setError(message);
        setIsError(true);

        toast.error({
          title: 'Error',
          message,
        });

        onError?.(err, variables);
        onSettled?.(undefined, err, variables);

        throw err;
      } finally {
        setIsLoading(false);
      }
    },
    [mutationFn, onSuccess, onError, onSettled, successMessage, errorMessage, toast]
  );

  const mutate = useCallback(
    async (variables: TVariables): Promise<TData | undefined> => {
      try {
        return await mutateAsync(variables);
      } catch {
        return undefined;
      }
    },
    [mutateAsync]
  );

  return {
    mutate,
    mutateAsync,
    isLoading,
    isError,
    isSuccess,
    error,
    data,
    reset,
  };
}

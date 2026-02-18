'use client';

import { useMemo } from 'react';
import { CheckCircle, Circle, Clock, ArrowRight } from 'lucide-react';

interface WorkflowState {
  id: string;
  code: string;
  name: string;
  is_initial: boolean;
  is_terminal: boolean;
  color: string;
}

interface WorkflowTransition {
  id: string;
  code: string;
  name: string;
  from_state: string;
  to_state: string;
}

interface WorkflowVisualizerProps {
  states: WorkflowState[];
  transitions: WorkflowTransition[];
  currentStateId?: string;
  completedStateIds?: string[];
  onStateClick?: (state: WorkflowState) => void;
  onTransitionClick?: (transition: WorkflowTransition) => void;
}

export function WorkflowVisualizer({
  states,
  transitions,
  currentStateId,
  completedStateIds = [],
  onStateClick,
  onTransitionClick,
}: WorkflowVisualizerProps) {
  // Build a linear flow from states (simplified visualization)
  const orderedStates = useMemo(() => {
    // Find initial state
    const initial = states.find((s) => s.is_initial);
    if (!initial) return states;

    const ordered: WorkflowState[] = [initial];
    const visited = new Set([initial.id]);

    // Follow transitions to build order
    let current = initial;
    while (current) {
      const nextTransition = transitions.find(
        (t) => t.from_state === current.id && !visited.has(t.to_state)
      );
      if (!nextTransition) break;

      const nextState = states.find((s) => s.id === nextTransition.to_state);
      if (!nextState) break;

      ordered.push(nextState);
      visited.add(nextState.id);
      current = nextState;
    }

    // Add any remaining states not in the order
    states.forEach((s) => {
      if (!visited.has(s.id)) {
        ordered.push(s);
      }
    });

    return ordered;
  }, [states, transitions]);

  const getStateStatus = (state: WorkflowState) => {
    if (completedStateIds.includes(state.id)) return 'completed';
    if (state.id === currentStateId) return 'current';
    return 'pending';
  };

  const getTransitionForStates = (fromId: string, toId: string) => {
    return transitions.find(
      (t) => t.from_state === fromId && t.to_state === toId
    );
  };

  return (
    <div className="p-4 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
      <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-4">
        Workflow Progress
      </h3>

      {/* Linear Flow View */}
      <div className="flex items-center overflow-x-auto pb-4">
        {orderedStates.map((state, index) => {
          const status = getStateStatus(state);
          const nextState = orderedStates[index + 1];
          const transition = nextState
            ? getTransitionForStates(state.id, nextState.id)
            : null;

          return (
            <div key={state.id} className="flex items-center">
              {/* State Node */}
              <button
                onClick={() => onStateClick?.(state)}
                className={`flex flex-col items-center min-w-[100px] p-2 rounded-lg transition-colors ${
                  onStateClick
                    ? 'hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer'
                    : ''
                }`}
              >
                <div
                  className={`w-10 h-10 rounded-full flex items-center justify-center ${
                    status === 'completed'
                      ? 'bg-green-100 text-green-600 dark:bg-green-900 dark:text-green-400'
                      : status === 'current'
                      ? 'bg-blue-100 text-blue-600 dark:bg-blue-900 dark:text-blue-400 ring-2 ring-blue-500 ring-offset-2 dark:ring-offset-gray-800'
                      : 'bg-gray-100 text-gray-400 dark:bg-gray-700 dark:text-gray-500'
                  }`}
                >
                  {status === 'completed' ? (
                    <CheckCircle className="w-5 h-5" />
                  ) : status === 'current' ? (
                    <Clock className="w-5 h-5" />
                  ) : (
                    <Circle className="w-5 h-5" />
                  )}
                </div>
                <span
                  className={`mt-2 text-xs font-medium text-center ${
                    status === 'current'
                      ? 'text-blue-600 dark:text-blue-400'
                      : status === 'completed'
                      ? 'text-green-600 dark:text-green-400'
                      : 'text-gray-500 dark:text-gray-400'
                  }`}
                >
                  {state.name}
                </span>
                {state.is_terminal && (
                  <span className="mt-1 text-[10px] text-gray-400 uppercase">
                    Final
                  </span>
                )}
              </button>

              {/* Transition Arrow */}
              {nextState && (
                <button
                  onClick={() => transition && onTransitionClick?.(transition)}
                  className={`flex flex-col items-center mx-2 ${
                    onTransitionClick && transition
                      ? 'hover:text-blue-500 cursor-pointer'
                      : ''
                  }`}
                >
                  <div
                    className={`w-12 h-0.5 ${
                      completedStateIds.includes(state.id)
                        ? 'bg-green-400'
                        : 'bg-gray-300 dark:bg-gray-600'
                    }`}
                  />
                  <ArrowRight
                    className={`w-4 h-4 -mt-2.5 ${
                      completedStateIds.includes(state.id)
                        ? 'text-green-400'
                        : 'text-gray-300 dark:text-gray-600'
                    }`}
                  />
                  {transition && (
                    <span className="text-[10px] text-gray-400 mt-1 whitespace-nowrap">
                      {transition.name}
                    </span>
                  )}
                </button>
              )}
            </div>
          );
        })}
      </div>

      {/* Legend */}
      <div className="flex items-center gap-6 mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-green-500" />
          <span className="text-xs text-gray-500">Completed</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-blue-500" />
          <span className="text-xs text-gray-500">Current</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 rounded-full bg-gray-300 dark:bg-gray-600" />
          <span className="text-xs text-gray-500">Pending</span>
        </div>
      </div>
    </div>
  );
}

// Compact version for inline display
export function WorkflowProgressBar({
  states,
  currentStateId,
  completedStateIds = [],
}: {
  states: WorkflowState[];
  currentStateId?: string;
  completedStateIds?: string[];
}) {
  const orderedStates = states.sort((a, b) => {
    if (a.is_initial) return -1;
    if (b.is_initial) return 1;
    if (a.is_terminal) return 1;
    if (b.is_terminal) return -1;
    return 0;
  });

  const currentIndex = orderedStates.findIndex((s) => s.id === currentStateId);
  const progress = currentIndex >= 0 ? ((currentIndex + 1) / orderedStates.length) * 100 : 0;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-xs text-gray-500">
        <span>{orderedStates[0]?.name || 'Start'}</span>
        <span>{orderedStates[orderedStates.length - 1]?.name || 'End'}</span>
      </div>
      <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
        <div
          className="bg-blue-600 h-2 rounded-full transition-all duration-300"
          style={{ width: `${progress}%` }}
        />
      </div>
      <div className="flex justify-center">
        <span className="text-xs text-gray-500">
          {orderedStates.find((s) => s.id === currentStateId)?.name || 'Not Started'}
        </span>
      </div>
    </div>
  );
}

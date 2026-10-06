import { create } from 'zustand';
import { getAccessToken } from '@/lib/api-client';
import { useNotificationStore } from './use-notification-store';

export type PipelineStageStatus = 'queued' | 'running' | 'completed' | 'failed' | 'cached';

export interface PipelineStageProgress {
  stage: string;
  status: PipelineStageStatus;
  startTime?: number;
  endTime?: number;
  error?: string;
  cacheHit?: boolean;
}

export interface PipelineProgress {
  projectId: string;
  status: 'idle' | 'running' | 'completed' | 'failed';
  currentStage: string | null;
  stages: Record<string, PipelineStageProgress>;
  startTime: number;
  endTime?: number;
  eventSource?: EventSource;
}

interface PipelineState {
  activePipelines: Record<string, PipelineProgress>;
  beginPipeline: (projectId: string, stage?: string, startFromStage?: string) => void;
  finishPipeline: (projectId: string, status: 'completed' | 'failed') => void;
  startPipeline: (projectId: string, stage?: string) => void;
  stopPipeline: (projectId: string) => void;
  getPipeline: (projectId: string) => PipelineProgress | null;
  updateStage: (projectId: string, stage: string, update: Partial<PipelineStageProgress>) => void;
}

const STAGE_ORDER = [
  'dna', 'features', 'roadmap', 'team', 'swot', 'cost', 'legal_compliance',
  'competitive_moat', 'stress_test', 'financial_intelligence',
  'investment_committee', 'product_execution', 'global_expansion', 'blueprint',
];

export const usePipelineStore = create<PipelineState>((set, get) => ({
  activePipelines: {},

  beginPipeline: (projectId: string, stage?: string, startFromStage?: string) => {
    const startIndex = startFromStage ? STAGE_ORDER.indexOf(startFromStage) : 0;
    const stagesToRun = stage
      ? [stage]
      : STAGE_ORDER.slice(Math.max(startIndex, 0));
    const stages: Record<string, PipelineStageProgress> = {};
    if (startFromStage) {
      STAGE_ORDER.slice(0, startIndex).forEach((completedStage) => {
        stages[completedStage] = { stage: completedStage, status: 'completed' };
      });
    }
    stagesToRun.forEach((s) => {
      stages[s] = { stage: s, status: 'queued' };
    });

    const pipeline: PipelineProgress = {
      projectId,
      status: 'running',
      currentStage: stagesToRun[0],
      stages,
      startTime: Date.now(),
    };

    set((state) => ({
      activePipelines: { ...state.activePipelines, [projectId]: pipeline },
    }));
  },

  finishPipeline: (projectId, status) => {
    set((state) => {
      const pipeline = state.activePipelines[projectId];
      if (!pipeline) return state;

      return {
        activePipelines: {
          ...state.activePipelines,
          [projectId]: { ...pipeline, status, currentStage: null, endTime: Date.now() },
        },
      };
    });
  },

  startPipeline: (projectId: string, stage?: string) => {
    get().beginPipeline(projectId, stage);
    // Start SSE connection
    connectSSE(projectId, stage);
  },

  stopPipeline: (projectId: string) => {
    const pipeline = get().activePipelines[projectId];
    if (pipeline?.eventSource) {
      pipeline.eventSource.close();
    }
    set((state) => ({
      activePipelines: {
        ...state.activePipelines,
        [projectId]: { ...pipeline, status: 'failed', endTime: Date.now() },
      },
    }));
  },

  getPipeline: (projectId: string) => {
    return get().activePipelines[projectId] || null;
  },

  updateStage: (projectId: string, stage: string, update: Partial<PipelineStageProgress>) => {
    set((state) => {
      const pipeline = state.activePipelines[projectId];
      if (!pipeline) return state;

      const stages = { ...pipeline.stages };
      const currentStageIndex = STAGE_ORDER.indexOf(stage);
      if (update.status === 'running' && Object.keys(stages).length > 1 && currentStageIndex > 0) {
        for (const previousStage of STAGE_ORDER.slice(0, currentStageIndex)) {
          if (stages[previousStage]?.status === 'queued') {
            stages[previousStage] = { ...stages[previousStage], status: 'completed' };
          }
        }
      }

      return {
        activePipelines: {
          ...state.activePipelines,
          [projectId]: {
            ...pipeline,
            currentStage: update.status === 'running'
              ? stage
              : pipeline.currentStage === stage
                ? null
                : pipeline.currentStage,
            stages: {
              ...stages,
              [stage]: { ...stages[stage], ...update, stage },
            },
          },
        },
      };
    });
  },
}));

function connectSSE(projectId: string, targetStage?: string) {
  const token = getAccessToken();
  if (!token) return;

  const url = `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/streams/progress/${projectId}?token=${encodeURIComponent(token)}`;
  const es = new EventSource(url);
  const store = usePipelineStore.getState();
  const notify = useNotificationStore.getState();

  // Store event source for cleanup
  set((state) => ({
    activePipelines: {
      ...state.activePipelines,
      [projectId]: { ...state.activePipelines[projectId], eventSource: es },
    },
  }));

  let reconnectAttempts = 0;
  const MAX_RECONNECT = 5;

  es.addEventListener('system:init', () => {
    reconnectAttempts = 0;
  });

  es.addEventListener('module:started', (e: any) => {
    try {
      const data = JSON.parse(e.data);
      const stageName = data.module_info?.module_name;
      if (stageName) {
        store.updateStage(projectId, stageName, {
          status: 'running',
          startTime: Date.now(),
        });
        // Dispatch custom event for UI updates
        window.dispatchEvent(new CustomEvent('pipeline:stage-started', {
          detail: { projectId, stage: stageName },
        }));
      }
    } catch (err) {
      console.error('module:started parse error', err);
    }
  });

  es.addEventListener('module:completed', (e: any) => {
    try {
      const data = JSON.parse(e.data);
      const stageName = data.module_info?.module_name;
      if (stageName) {
        store.updateStage(projectId, stageName, {
          status: 'completed',
          endTime: Date.now(),
        });
        // Dispatch custom event for UI updates
        window.dispatchEvent(new CustomEvent('pipeline:stage-completed', {
          detail: { projectId, stage: stageName, result: data.result_info },
        }));
      }
    } catch (err) {
      console.error('module:completed parse error', err);
    }
  });

  es.addEventListener('module:failed', (e: any) => {
    try {
      const data = JSON.parse(e.data);
      const stageName = data.module_info?.module_name;
      const errMsg = data.error_info?.error_message || 'Unknown error';
      if (stageName) {
        store.updateStage(projectId, stageName, {
          status: 'failed',
          error: errMsg,
          endTime: Date.now(),
        });
      }
    } catch (err) {
      console.error('module:failed parse error', err);
    }
  });

  es.addEventListener('workflow:completed', () => {
    es.close();
    const pipeline = usePipelineStore.getState().activePipelines[projectId];
    if (pipeline) {
      usePipelineStore.setState((state) => ({
        activePipelines: {
          ...state.activePipelines,
          [projectId]: { ...pipeline, status: 'completed', endTime: Date.now() },
        },
      }));
    }
    notify.addNotification({
      title: 'Pipeline Complete',
      message: 'Your venture blueprint has been generated successfully.',
      type: 'success',
    });
    window.dispatchEvent(new CustomEvent('pipeline:completed', { detail: { projectId } }));
  });

  es.addEventListener('workflow:failed', (e: any) => {
    es.close();
    const initialPipeline = usePipelineStore.getState().activePipelines[projectId];
    let message = 'Generation failed.';
    try {
      message = JSON.parse(e.data).error_info?.error_message || message;
    } catch {
      // Keep the generic failure message when the stream payload is malformed.
    }
    const runningStage = Object.values(initialPipeline?.stages || {})
      .find((pipelineStage) => pipelineStage.status === 'running')?.stage;
    if (runningStage) {
      usePipelineStore.getState().updateStage(projectId, runningStage, {
        status: 'failed',
        error: message,
        endTime: Date.now(),
      });
    }
    const pipeline = usePipelineStore.getState().activePipelines[projectId];
    if (pipeline) {
      usePipelineStore.setState((state) => ({
        activePipelines: {
          ...state.activePipelines,
          [projectId]: { ...pipeline, status: 'failed', endTime: Date.now() },
        },
      }));
    }
    notify.addNotification({
      title: 'Pipeline Failed',
      message,
      type: 'error',
    });
    window.dispatchEvent(new CustomEvent('pipeline:failed', { detail: { projectId } }));
  });

  es.onerror = () => {
    reconnectAttempts++;
    if (reconnectAttempts >= MAX_RECONNECT) {
      es.close();
      notify.addNotification({
        title: 'Connection Lost',
        message: 'Lost connection to the pipeline. Processing continues in background.',
        type: 'warning',
      });
    }
  };
}

// Helper to set state from outside the store (for SSE callbacks)
function set(state: (prev: PipelineState) => Partial<PipelineState>) {
  usePipelineStore.setState(state);
}

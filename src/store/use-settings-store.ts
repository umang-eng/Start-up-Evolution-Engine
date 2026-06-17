import { create } from 'zustand';

export interface SettingsState {
  founderName: string;
  founderTitle: string;
  model: string;
  temperature: number;
  customApiKey: string;
  currencySymbol: string;
  costBuffer: number; // percentage (0 - 50%)
  theme: 'light' | 'dark';

  // Actions
  updateSettings: (updates: Partial<Omit<SettingsState, 'updateSettings'>>) => void;
  resetSettings: () => void;
}

const DEFAULT_SETTINGS: Omit<SettingsState, 'updateSettings' | 'resetSettings'> = {
  founderName: 'Founder Member',
  founderTitle: 'CEO & Founder',
  model: 'gemini-2.0-flash',
  temperature: 0.3,
  customApiKey: '',
  currencySymbol: '$',
  costBuffer: 0,
  theme: 'light',
};

export const useSettingsStore = create<SettingsState>()((set) => {
  // Safe load from localStorage (Client-only)
  let initialSettings = { ...DEFAULT_SETTINGS };
  if (typeof window !== 'undefined') {
    try {
      const stored = localStorage.getItem('evolution-engine-settings');
      if (stored) {
        initialSettings = { ...DEFAULT_SETTINGS, ...JSON.parse(stored) };
        // Apply theme on load
        if (initialSettings.theme === 'dark') {
          document.documentElement.classList.add('dark');
        } else {
          document.documentElement.classList.remove('dark');
        }
      }
    } catch (e) {
      console.error('Failed to load settings:', e);
    }
  }

  return {
    ...initialSettings,
    updateSettings: (updates) => set((state) => {
      const newState = { ...state, ...updates };
      // Strip out actions before storing
      const { updateSettings, resetSettings, ...serializableState } = newState;
      if (typeof window !== 'undefined') {
        localStorage.setItem('evolution-engine-settings', JSON.stringify(serializableState));
        // Apply theme changes
        if (updates.theme) {
          if (updates.theme === 'dark') {
            document.documentElement.classList.add('dark');
          } else {
            document.documentElement.classList.remove('dark');
          }
        }
      }
      return newState;
    }),
    resetSettings: () => set(() => {
      if (typeof window !== 'undefined') {
        localStorage.removeItem('evolution-engine-settings');
        document.documentElement.classList.remove('dark');
      }
      return { ...DEFAULT_SETTINGS };
    }),
  };
});

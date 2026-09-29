export {};

declare global {
  interface PuterSpeech2TxtOptions {
    provider?: 'openai' | 'xai';
    model?: string;
    language?: string;
    response_format?: 'json' | 'text';
    translate?: boolean;
    prompt?: string;
    temperature?: number;
    chunking_strategy?: 'auto';
  }

  interface PuterSpeech2TxtResult {
    text?: string;
    language?: string;
    duration?: number;
    segments?: Array<{
      start?: number;
      end?: number;
      text?: string;
      speaker?: string;
    }>;
  }

  interface PuterAI {
    speech2txt(
      source: Blob | File | string,
      options?: PuterSpeech2TxtOptions,
      testMode?: boolean,
    ): Promise<PuterSpeech2TxtResult | string>;
  }

  interface PuterGlobal {
    ai: PuterAI;
    auth: {
      isSignedIn: () => boolean;
      signIn: () => Promise<void>;
    };
  }

  interface Window {
    puter?: PuterGlobal;
  }
}

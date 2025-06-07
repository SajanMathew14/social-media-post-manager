import { LLMProvider, TopicMapping } from './types';

// LLM Provider Configurations
export const LLM_PROVIDERS: Record<string, LLMProvider> = {
  'claude-3-5-sonnet': {
    name: 'claude-3-5-sonnet',
    displayName: 'Claude 3.5 Sonnet',
    description: 'Anthropic\'s most capable model for complex reasoning and analysis',
    maxTokens: 200000,
    costPer1kTokens: 0.003
  },
  'gpt-4-turbo': {
    name: 'gpt-4-turbo',
    displayName: 'GPT-4 Turbo',
    description: 'OpenAI\'s latest model with improved performance and lower costs',
    maxTokens: 128000,
    costPer1kTokens: 0.01
  },
  'gemini-pro': {
    name: 'gemini-pro',
    displayName: 'Gemini Pro',
    description: 'Google\'s advanced model for multimodal understanding',
    maxTokens: 32000,
    costPer1kTokens: 0.0005
  }
};

// Default Topic Configurations
export const DEFAULT_TOPIC_MAPPING: TopicMapping = {
  ai: {
    topicName: 'ai',
    keywords: ['AI', 'Artificial Intelligence', 'Machine Learning', 'Deep Learning', 'Neural Networks', 'LLM', 'GPT', 'Claude'],
    trustedSources: [
      'techcrunch.com',
      'venturebeat.com',
      'mit.edu',
      'nvidia.com',
      'openai.com',
      'anthropic.com',
      'arxiv.org',
      'nature.com'
    ],
    priorityWeight: 1.2
  },
  finance: {
    topicName: 'finance',
    keywords: ['fintech', 'finance', 'markets', 'banking', 'cryptocurrency', 'blockchain', 'trading', 'investment'],
    trustedSources: [
      'bloomberg.com',
      'forbes.com',
      'wsj.com',
      'economist.com',
      'reuters.com',
      'ft.com',
      'cnbc.com',
      'marketwatch.com'
    ],
    priorityWeight: 1.1
  },
  healthcare: {
    topicName: 'healthcare',
    keywords: ['healthcare', 'medical', 'biotech', 'pharma', 'medicine', 'clinical', 'health tech'],
    trustedSources: [
      'nejm.org',
      'nature.com',
      'statnews.com',
      'fiercehealthcare.com',
      'medscape.com',
      'healthline.com',
      'who.int'
    ],
    priorityWeight: 1.0
  },
  technology: {
    topicName: 'technology',
    keywords: ['technology', 'tech', 'software', 'hardware', 'startup', 'innovation', 'digital'],
    trustedSources: [
      'techcrunch.com',
      'theverge.com',
      'wired.com',
      'arstechnica.com',
      'engadget.com',
      'zdnet.com',
      'cnet.com'
    ],
    priorityWeight: 1.0
  },
  business: {
    topicName: 'business',
    keywords: ['business', 'enterprise', 'corporate', 'management', 'strategy', 'leadership', 'entrepreneurship'],
    trustedSources: [
      'harvard.edu',
      'mckinsey.com',
      'businessinsider.com',
      'fortune.com',
      'inc.com',
      'fastcompany.com',
      'hbr.org'
    ],
    priorityWeight: 1.0
  }
};

// API Configuration
export const API_CONFIG = {
  QUOTA_LIMITS: {
    DAILY: 10,
    MONTHLY: 300
  },
  NEWS_LIMITS: {
    MIN_TOP_N: 1,
    MAX_TOP_N: 12,
    DEFAULT_TOP_N: 5
  },
  CACHE_TTL: {
    NEWS_ARTICLES: 3600, // 1 hour in seconds
    TOPIC_CONFIG: 86400, // 24 hours in seconds
    SESSION: 2592000 // 30 days in seconds
  }
};

// Error Messages
export const ERROR_MESSAGES = {
  QUOTA_EXCEEDED: 'Daily quota exceeded. Please try again tomorrow.',
  INVALID_TOPIC: 'Please provide a valid topic.',
  INVALID_DATE: 'Please provide a valid date in YYYY-MM-DD format.',
  INVALID_TOP_N: `Top N must be between ${API_CONFIG.NEWS_LIMITS.MIN_TOP_N} and ${API_CONFIG.NEWS_LIMITS.MAX_TOP_N}.`,
  INVALID_LLM_MODEL: 'Please select a valid LLM model.',
  NEWS_FETCH_FAILED: 'Failed to fetch news articles. Please try again.',
  LLM_PROVIDER_ERROR: 'LLM provider is currently unavailable. Trying fallback provider.',
  SESSION_EXPIRED: 'Your session has expired. Please refresh the page.',
  DUPLICATE_REQUEST: 'This request was already processed recently. Please try a different topic or date.'
};

// Success Messages
export const SUCCESS_MESSAGES = {
  NEWS_FETCHED: 'Successfully fetched and processed news articles.',
  SESSION_CREATED: 'Session created successfully.',
  PREFERENCES_SAVED: 'Preferences saved successfully.'
};

// Processing Steps
export const PROCESSING_STEPS = {
  VALIDATE_INPUT: 'Validating input parameters',
  CHECK_QUOTA: 'Checking quota limits',
  CHECK_CACHE: 'Checking for cached results',
  FETCH_NEWS: 'Fetching news from Serper API',
  FILTER_ARTICLES: 'Filtering articles by relevance',
  SUMMARIZE_CONTENT: 'Generating summaries with LLM',
  SAVE_RESULTS: 'Saving results to cache',
  COMPLETE: 'Processing complete'
};

// Date Utilities
export const DATE_FORMATS = {
  API_DATE: 'YYYY-MM-DD',
  DISPLAY_DATE: 'MMM DD, YYYY',
  TIMESTAMP: 'YYYY-MM-DD HH:mm:ss'
};

// Regular Expressions
export const REGEX_PATTERNS = {
  DATE: /^\d{4}-\d{2}-\d{2}$/,
  URL: /^https?:\/\/.+/,
  EMAIL: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
  UUID: /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i
};

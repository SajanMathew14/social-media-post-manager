// User and Session Types
export interface Session {
  id: string;
  createdAt: Date;
  preferences: UserPreferences;
  lastActive: Date;
}

export interface UserPreferences {
  defaultTopic?: string;
  defaultLLMModel?: LLMModel;
  defaultTopN?: number;
}

// News and Content Types
export interface NewsRequest {
  topic: string;
  date: string; // YYYY-MM-DD format
  topN: number; // 1-12
  llmModel: LLMModel;
  sessionId: string;
}

export interface NewsArticle {
  id?: string;
  title: string;
  url: string;
  source: string;
  summary: string;
  publishedAt?: Date;
  relevanceScore?: number;
  contentHash?: string;
}

export interface NewsResponse {
  articles: NewsArticle[];
  totalFound: number;
  processingTime: number;
  quotaRemaining: number;
  workflowId?: string;
  llmProviderUsed?: string;
  cacheHit?: boolean;
}

// LLM and Processing Types
export type LLMModel = 'claude-3-5-sonnet' | 'gpt-4-turbo' | 'gemini-pro';

export interface LLMProvider {
  name: LLMModel;
  displayName: string;
  description: string;
  maxTokens: number;
  costPer1kTokens: number;
}

// Topic Configuration Types
export interface TopicConfig {
  topicName: string;
  keywords: string[];
  trustedSources: string[];
  priorityWeight: number;
}

export interface TopicMapping {
  [key: string]: TopicConfig;
}

// API Response Types
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface QuotaInfo {
  dailyUsed: number;
  dailyLimit: number;
  monthlyUsed: number;
  monthlyLimit: number;
  resetTime: Date;
}

// LangGraph State Types
export interface NewsState {
  topic: string;
  date: string;
  topN: number;
  llmModel: LLMModel;
  sessionId: string;
  rawArticles: any[];
  filteredArticles: NewsArticle[];
  summarizedArticles: NewsArticle[];
  quotaInfo: QuotaInfo;
  processingSteps: ProcessingStep[];
}

export interface ProcessingStep {
  step: string;
  status: 'pending' | 'processing' | 'completed' | 'error';
  message?: string;
  timestamp: Date;
}

// Database Types
export interface UserRequest {
  id: number;
  sessionId: string;
  requestType: string;
  topic: string;
  dateRequested: string;
  requestHash: string;
  createdAt: Date;
}

export interface NewsCache {
  id: number;
  topic: string;
  dateFetched: string;
  source: string;
  title: string;
  url: string;
  summary: string;
  contentHash: string;
  createdAt: Date;
}

// Post Generation Types
export interface PostGenerationRequest {
  articles: NewsArticle[];
  topic: string;
  llmModel: LLMModel;
  sessionId: string;
  newsWorkflowId: string;
}

export interface PostGenerationResponse {
  workflowId: string;
  processingTime: number;
  llmModelUsed: string;
  posts: {
    linkedin?: {
      content: string;
      charCount: number;
      hashtags: string[];
    };
    x?: {
      content: string;
      charCount: number;
      hashtags: string[];
      shortenedUrls?: Record<string, string>;
    };
  };
}

export interface GeneratedPost {
  id: string;
  sessionId: string;
  postType: 'linkedin' | 'x';
  content: string;
  originalContent?: string;
  charCount: number;
  edited: boolean;
  modelUsed: string;
  newsWorkflowId: string;
  articlesCount: number;
  topic: string;
  createdAt: Date;
  updatedAt: Date;
}

// Error Types
export interface AppError {
  code: string;
  message: string;
  details?: any;
}

export class QuotaExceededError extends Error {
  constructor(quotaInfo: QuotaInfo) {
    super(`Daily quota exceeded. Used: ${quotaInfo.dailyUsed}/${quotaInfo.dailyLimit}`);
    this.name = 'QuotaExceededError';
  }
}

export class LLMProviderError extends Error {
  constructor(provider: LLMModel, originalError: string) {
    super(`${provider} provider error: ${originalError}`);
    this.name = 'LLMProviderError';
  }
}

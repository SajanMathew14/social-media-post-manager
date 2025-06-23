import { REGEX_PATTERNS, API_CONFIG } from './constants';
import { NewsRequest, LLMModel } from './types';

// Browser-safe hash function
const createHash = (algorithm: string) => {
  // Simple hash implementation for browser compatibility
  return {
    update: (data: string) => ({
      digest: (format: string) => {
        // Simple hash function for browser
        let hash = 0;
        for (let i = 0; i < data.length; i++) {
          const char = data.charCodeAt(i);
          hash = ((hash << 5) - hash) + char;
          hash = hash & hash; // Convert to 32bit integer
        }
        // Convert to hex string
        const hexHash = Math.abs(hash).toString(16);
        // Pad with zeros to ensure consistent length
        return hexHash.padStart(32, '0');
      }
    })
  };
};

// Validation Utilities
export const validateDate = (date: string): boolean => {
  if (!REGEX_PATTERNS.DATE.test(date)) {
    return false;
  }
  
  const parsedDate = new Date(date);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  
  // Check if date is valid and not in the future
  return !isNaN(parsedDate.getTime()) && parsedDate <= today;
};

export const validateTopN = (topN: number): boolean => {
  return Number.isInteger(topN) && 
         topN >= API_CONFIG.NEWS_LIMITS.MIN_TOP_N && 
         topN <= API_CONFIG.NEWS_LIMITS.MAX_TOP_N;
};

export const validateLLMModel = (model: string): model is LLMModel => {
  return ['claude-3-5-sonnet', 'gpt-4-turbo', 'gemini-pro'].includes(model);
};

export const validateNewsRequest = (request: Partial<NewsRequest>): string[] => {
  const errors: string[] = [];
  
  if (!request.topic || request.topic.trim().length === 0) {
    errors.push('Topic is required');
  }
  
  if (!request.date || !validateDate(request.date)) {
    errors.push('Valid date is required (YYYY-MM-DD format, not in future)');
  }
  
  if (request.topN === undefined || !validateTopN(request.topN)) {
    errors.push(`Top N must be between ${API_CONFIG.NEWS_LIMITS.MIN_TOP_N} and ${API_CONFIG.NEWS_LIMITS.MAX_TOP_N}`);
  }
  
  if (!request.llmModel || !validateLLMModel(request.llmModel)) {
    errors.push('Valid LLM model is required');
  }
  
  if (!request.sessionId || !REGEX_PATTERNS.UUID.test(request.sessionId)) {
    errors.push('Valid session ID is required');
  }
  
  return errors;
};

// Hash Utilities
export const generateRequestHash = (topic: string, date: string): string => {
  const input = `${topic.toLowerCase().trim()}-${date}`;
  return createHash('md5').update(input).digest('hex').substring(0, 32);
};

export const generateContentHash = (content: string): string => {
  return createHash('md5').update(content).digest('hex').substring(0, 32);
};

// Date Utilities
export const formatDate = (date: Date, format: 'api' | 'display' | 'timestamp' = 'api'): string => {
  switch (format) {
    case 'api':
      return date.toISOString().split('T')[0]; // YYYY-MM-DD
    case 'display':
      return date.toLocaleDateString('en-US', { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric' 
      }); // MMM DD, YYYY
    case 'timestamp':
      return date.toISOString().replace('T', ' ').substring(0, 19); // YYYY-MM-DD HH:mm:ss
    default:
      return date.toISOString().split('T')[0];
  }
};

export const getTodayString = (): string => {
  return formatDate(new Date(), 'api');
};

export const getYesterdayString = (): string => {
  const yesterday = new Date();
  yesterday.setDate(yesterday.getDate() - 1);
  return formatDate(yesterday, 'api');
};

export const isToday = (dateString: string): boolean => {
  return dateString === getTodayString();
};

// Session Utilities
export const generateSessionId = (): string => {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = Math.random() * 16 | 0;
    const v = c === 'x' ? r : (r & 0x3 | 0x8);
    return v.toString(16);
  });
};

export const isValidSessionId = (sessionId: string): boolean => {
  return REGEX_PATTERNS.UUID.test(sessionId);
};

// Topic Utilities
export const normalizeTopicName = (topic: string): string => {
  return topic.toLowerCase().trim().replace(/\s+/g, '-');
};

export const extractKeywordsFromTopic = (topic: string): string[] => {
  return topic
    .toLowerCase()
    .split(/[\s,.-]+/)
    .filter(word => word.length > 2)
    .map(word => word.trim());
};

// URL Utilities
export const isValidUrl = (url: string): boolean => {
  return REGEX_PATTERNS.URL.test(url);
};

export const extractDomain = (url: string): string => {
  try {
    const urlObj = new URL(url);
    return urlObj.hostname.replace('www.', '');
  } catch {
    return '';
  }
};

// Array Utilities
export const shuffleArray = <T>(array: T[]): T[] => {
  const shuffled = [...array];
  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
  }
  return shuffled;
};

export const removeDuplicates = <T>(array: T[], keyFn?: (item: T) => string): T[] => {
  if (!keyFn) {
    return [...new Set(array)];
  }
  
  const seen = new Set<string>();
  return array.filter(item => {
    const key = keyFn(item);
    if (seen.has(key)) {
      return false;
    }
    seen.add(key);
    return true;
  });
};

// Error Utilities
export const createErrorResponse = (message: string, code?: string): { success: false; error: string; code?: string } => {
  return {
    success: false,
    error: message,
    ...(code && { code })
  };
};

export const createSuccessResponse = <T>(data: T, message?: string): { success: true; data: T; message?: string } => {
  return {
    success: true,
    data,
    ...(message && { message })
  };
};

// Retry Utilities
export const sleep = (ms: number): Promise<void> => {
  return new Promise(resolve => setTimeout(resolve, ms));
};

export const retryWithBackoff = async <T>(
  fn: () => Promise<T>,
  maxRetries: number = 3,
  baseDelay: number = 1000
): Promise<T> => {
  let lastError: Error;
  
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error as Error;
      
      if (attempt === maxRetries) {
        throw lastError;
      }
      
      const delay = baseDelay * Math.pow(2, attempt);
      await sleep(delay);
    }
  }
  
  throw lastError!;
};

// Text Utilities
export const truncateText = (text: string, maxLength: number, suffix: string = '...'): string => {
  if (text.length <= maxLength) {
    return text;
  }
  
  return text.substring(0, maxLength - suffix.length) + suffix;
};

export const capitalizeFirst = (text: string): string => {
  return text.charAt(0).toUpperCase() + text.slice(1);
};

export const sanitizeText = (text: string): string => {
  return text
    .replace(/[<>]/g, '') // Remove potential HTML tags
    .replace(/\s+/g, ' ') // Normalize whitespace
    .trim();
};

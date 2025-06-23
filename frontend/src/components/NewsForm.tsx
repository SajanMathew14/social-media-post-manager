'use client'

import { useState } from 'react'
import { 
  NewsRequest, 
  LLMModel, 
  LLM_PROVIDERS, 
  DEFAULT_TOPIC_MAPPING,
  validateNewsRequest,
  API_CONFIG
} from '@social-media-manager/shared'

interface NewsFormProps {
  onSubmit: (request: Omit<NewsRequest, 'sessionId'>) => void
  isLoading: boolean
  defaultValues: {
    topic: string
    date: string
    topN: number
    llmModel: LLMModel
  }
}

export function NewsForm({ onSubmit, isLoading, defaultValues }: NewsFormProps) {
  const [formData, setFormData] = useState(defaultValues)
  const [errors, setErrors] = useState<string[]>([])

  const topicSuggestions = Object.keys(DEFAULT_TOPIC_MAPPING)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    
    // Validate form data (excluding sessionId which is handled by parent)
    const errors: string[] = []
    
    if (!formData.topic || formData.topic.trim().length === 0) {
      errors.push('Topic is required')
    }
    
    if (!formData.date) {
      errors.push('Date is required')
    }
    
    if (formData.topN === undefined || formData.topN < API_CONFIG.NEWS_LIMITS.MIN_TOP_N || formData.topN > API_CONFIG.NEWS_LIMITS.MAX_TOP_N) {
      errors.push(`Number of articles must be between ${API_CONFIG.NEWS_LIMITS.MIN_TOP_N} and ${API_CONFIG.NEWS_LIMITS.MAX_TOP_N}`)
    }
    
    if (!formData.llmModel) {
      errors.push('AI Model is required')
    }
    
    if (errors.length > 0) {
      setErrors(errors)
      return
    }
    
    setErrors([])
    onSubmit(formData)
  }

  const handleInputChange = (field: keyof typeof formData, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }))
    // Clear errors when user starts typing
    if (errors.length > 0) {
      setErrors([])
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Topic Input */}
      <div>
        <label htmlFor="topic" className="block text-sm font-medium text-gray-700 mb-2">
          Topic
        </label>
        <input
          type="text"
          id="topic"
          value={formData.topic}
          onChange={(e) => handleInputChange('topic', e.target.value)}
          placeholder="e.g., AI, finance, healthcare"
          className="input-field"
          disabled={isLoading}
          list="topic-suggestions"
        />
        <datalist id="topic-suggestions">
          {topicSuggestions.map(topic => (
            <option key={topic} value={topic} />
          ))}
        </datalist>
        <p className="mt-1 text-xs text-secondary-500">
          Try: {topicSuggestions.slice(0, 3).join(', ')}
        </p>
      </div>

      {/* Date Input */}
      <div>
        <label htmlFor="date" className="block text-sm font-medium text-gray-700 mb-2">
          Date
        </label>
        <input
          type="date"
          id="date"
          value={formData.date}
          onChange={(e) => handleInputChange('date', e.target.value)}
          max={new Date().toISOString().split('T')[0]}
          className="input-field"
          disabled={isLoading}
        />
        <p className="mt-1 text-xs text-secondary-500">
          Select a date to fetch news from (today or earlier)
        </p>
      </div>

      {/* Top N Selector */}
      <div>
        <label htmlFor="topN" className="block text-sm font-medium text-gray-700 mb-2">
          Number of Articles ({formData.topN})
        </label>
        <input
          type="range"
          id="topN"
          min={API_CONFIG.NEWS_LIMITS.MIN_TOP_N}
          max={API_CONFIG.NEWS_LIMITS.MAX_TOP_N}
          value={formData.topN}
          onChange={(e) => handleInputChange('topN', parseInt(e.target.value))}
          className="w-full h-2 bg-secondary-200 rounded-lg appearance-none cursor-pointer slider"
          disabled={isLoading}
        />
        <div className="flex justify-between text-xs text-secondary-500 mt-1">
          <span>{API_CONFIG.NEWS_LIMITS.MIN_TOP_N}</span>
          <span>{API_CONFIG.NEWS_LIMITS.MAX_TOP_N}</span>
        </div>
      </div>

      {/* LLM Model Selector */}
      <div>
        <label htmlFor="llmModel" className="block text-sm font-medium text-gray-700 mb-2">
          AI Model
        </label>
        <select
          id="llmModel"
          value={formData.llmModel}
          onChange={(e) => handleInputChange('llmModel', e.target.value as LLMModel)}
          className="input-field"
          disabled={isLoading}
        >
          {Object.values(LLM_PROVIDERS).map(provider => (
            <option key={provider.name} value={provider.name}>
              {provider.displayName}
            </option>
          ))}
        </select>
        <p className="mt-1 text-xs text-secondary-500">
          {LLM_PROVIDERS[formData.llmModel]?.description}
        </p>
      </div>

      {/* Error Display */}
      {errors.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">
                Please fix the following errors:
              </h3>
              <ul className="mt-1 text-sm text-red-700 list-disc list-inside">
                {errors.map((error, index) => (
                  <li key={index}>{error}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Submit Button */}
      <button
        type="submit"
        disabled={isLoading || !formData.topic.trim()}
        className="btn-primary w-full flex items-center justify-center"
      >
        {isLoading ? (
          <>
            <div className="loading-spinner mr-2"></div>
            Fetching News...
          </>
        ) : (
          <>
            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            Fetch News
          </>
        )}
      </button>
    </form>
  )
}

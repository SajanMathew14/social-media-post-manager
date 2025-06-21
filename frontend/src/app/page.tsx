'use client'

import { useState, useEffect } from 'react'
import { NewsForm } from '@/components/NewsForm'
import { NewsResults } from '@/components/NewsResults'
import { QuotaDisplay } from '@/components/QuotaDisplay'
import { LoadingState } from '@/components/LoadingState'
import { 
  NewsRequest, 
  NewsResponse, 
  QuotaInfo, 
  ProcessingStep,
  generateSessionId,
  getTodayString,
  API_CONFIG
} from '@social-media-manager/shared'

export default function HomePage() {
  const [sessionId, setSessionId] = useState<string>('')
  const [isSessionReady, setIsSessionReady] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [newsData, setNewsData] = useState<NewsResponse | null>(null)
  const [quotaInfo, setQuotaInfo] = useState<QuotaInfo>({
    dailyUsed: 0,
    dailyLimit: API_CONFIG.QUOTA_LIMITS.DAILY,
    monthlyUsed: 0,
    monthlyLimit: API_CONFIG.QUOTA_LIMITS.MONTHLY,
    resetTime: new Date()
  })
  const [processingSteps, setProcessingSteps] = useState<ProcessingStep[]>([])
  const [error, setError] = useState<string | null>(null)
  const [lastRequestData, setLastRequestData] = useState<{topic: string, llmModel: string} | null>(null)

  // Initialize session on component mount
  useEffect(() => {
    // Generate session ID immediately if not in localStorage
    const initializeSession = () => {
      try {
        const storedSessionId = typeof window !== 'undefined' ? localStorage.getItem('sessionId') : null
        if (storedSessionId && storedSessionId.length > 0) {
          setSessionId(storedSessionId)
        } else {
          const newSessionId = generateSessionId()
          setSessionId(newSessionId)
          if (typeof window !== 'undefined') {
            localStorage.setItem('sessionId', newSessionId)
          }
        }
        setIsSessionReady(true)
      } catch (err) {
        console.error('Error initializing session:', err)
        // Fallback: generate a new session ID without localStorage
        const newSessionId = generateSessionId()
        setSessionId(newSessionId)
        setIsSessionReady(true)
      }
    }

    initializeSession()
  }, [])

  const handleNewsRequest = async (request: Omit<NewsRequest, 'sessionId'>) => {
    if (!sessionId || !isSessionReady) {
      setError('Session not initialized. Please refresh the page.')
      return
    }

    setIsLoading(true)
    setError(null)
    setNewsData(null)
    setProcessingSteps([])

    const fullRequest: NewsRequest = {
      ...request,
      sessionId
    }

    // Store the request data for passing to NewsResults
    setLastRequestData({
      topic: request.topic,
      llmModel: request.llmModel
    })

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/news/fetch`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(fullRequest),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.error || 'Failed to fetch news')
      }

      const data: NewsResponse = await response.json()
      setNewsData(data)
      setQuotaInfo(prev => ({
        ...prev,
        dailyUsed: prev.dailyUsed + 1,
        monthlyUsed: prev.monthlyUsed + 1
      }))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unexpected error occurred')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          LinkedIn Content Manager
        </h1>
        <p className="text-lg text-secondary-600">
          Discover trending news and generate AI-powered content for your LinkedIn posts
        </p>
      </div>

      {/* Quota Display */}
      <div className="mb-8">
        <QuotaDisplay quotaInfo={quotaInfo} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* News Request Form */}
        <div className="lg:col-span-1">
          <div className="card sticky top-8">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">
              Fetch News
            </h2>
            {!isSessionReady ? (
              <div className="text-center py-8">
                <div className="loading-spinner mx-auto mb-4"></div>
                <p className="text-secondary-600">Initializing session...</p>
              </div>
            ) : (
              <NewsForm 
                onSubmit={handleNewsRequest}
                isLoading={isLoading}
                defaultValues={{
                  topic: '',
                  date: getTodayString(),
                  topN: API_CONFIG.NEWS_LIMITS.DEFAULT_TOP_N,
                  llmModel: 'claude-3-5-sonnet'
                }}
              />
            )}
          </div>
        </div>

        {/* Results Area */}
        <div className="lg:col-span-2">
          {isLoading && (
            <LoadingState 
              steps={processingSteps}
              currentStep="Fetching news articles..."
            />
          )}

          {error && (
            <div className="card border-red-200 bg-red-50">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-red-800">
                    Error fetching news
                  </h3>
                  <p className="mt-1 text-sm text-red-700">{error}</p>
                </div>
              </div>
            </div>
          )}

          {newsData && !isLoading && lastRequestData && (
            <NewsResults 
              newsData={newsData}
              onRetry={() => window.location.reload()}
              sessionId={sessionId}
              topic={lastRequestData.topic}
              llmModel={lastRequestData.llmModel}
            />
          )}

          {!newsData && !isLoading && !error && (
            <div className="card text-center py-12">
              <div className="mx-auto h-12 w-12 text-secondary-400 mb-4">
                <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z" />
                </svg>
              </div>
              <h3 className="text-lg font-medium text-secondary-900 mb-2">
                Ready to fetch news
              </h3>
              <p className="text-secondary-600">
                Select a topic, date, and preferences to get started with AI-powered news aggregation.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

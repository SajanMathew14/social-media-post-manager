'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { LoadingState } from '@/components/LoadingState'
import { generatePosts } from '@/lib/api/posts'
import { 
  NewsArticle, 
  PostGenerationResponse,
  ProcessingStep 
} from '@social-media-manager/shared'

interface PostsData {
  articles: NewsArticle[]
  topic: string
  llmModel: string
  sessionId: string
  newsWorkflowId: string
}

export default function PostsPage() {
  const router = useRouter()
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [postsResponse, setPostsResponse] = useState<PostGenerationResponse | null>(null)
  const [processingSteps, setProcessingSteps] = useState<ProcessingStep[]>([])
  const [postsData, setPostsData] = useState<PostsData | null>(null)

  useEffect(() => {
    // Get data from sessionStorage
    const storedData = sessionStorage.getItem('postsData')
    if (!storedData) {
      setError('No articles data found. Please generate news first.')
      setIsLoading(false)
      return
    }

    try {
      const data: PostsData = JSON.parse(storedData)
      setPostsData(data)
      generatePostsFromArticles(data)
    } catch (err) {
      setError('Invalid data format. Please try again.')
      setIsLoading(false)
    }

    // Clear sessionStorage after retrieving data
    sessionStorage.removeItem('postsData')
  }, [])

  const generatePostsFromArticles = async (data: PostsData) => {
    setIsLoading(true)
    setError(null)
    setProcessingSteps([
      { step: 'Analyzing articles', status: 'processing', timestamp: new Date() },
      { step: 'Generating LinkedIn post', status: 'pending', timestamp: new Date() },
      { step: 'Generating X post', status: 'pending', timestamp: new Date() },
    ])

    try {
      // Update steps as we progress
      setTimeout(() => {
        setProcessingSteps(prev => [
          { ...prev[0], status: 'completed' },
          { ...prev[1], status: 'processing' },
          prev[2]
        ])
      }, 1000)

      const response = await generatePosts(
        data.articles,
        data.topic,
        data.llmModel,
        data.sessionId,
        data.newsWorkflowId
      )

      setPostsResponse(response)
      setProcessingSteps(prev => prev.map(step => ({ ...step, status: 'completed' })))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate posts')
      setProcessingSteps(prev => prev.map(step => 
        step.status === 'processing' ? { ...step, status: 'error' } : step
      ))
    } finally {
      setIsLoading(false)
    }
  }

  const handleBack = () => {
    router.push('/')
  }

  const handleEdit = (postType: 'linkedin' | 'x') => {
    // TODO: Implement edit functionality
    console.log(`Edit ${postType} post`)
  }

  if (isLoading) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <LoadingState 
          steps={processingSteps}
          currentStep="Generating social media posts..."
        />
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="card border-red-200 bg-red-50">
          <div className="flex items-center mb-4">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">
                Error generating posts
              </h3>
              <p className="mt-1 text-sm text-red-700">{error}</p>
            </div>
          </div>
          <button onClick={handleBack} className="btn-secondary">
            Back to News
          </button>
        </div>
      </div>
    )
  }

  if (!postsResponse || !postsData) {
    return null
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-8">
        <button
          onClick={handleBack}
          className="inline-flex items-center text-secondary-600 hover:text-secondary-900 mb-4"
        >
          <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          Back to News
        </button>
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          Generated Posts
        </h1>
        <p className="text-lg text-secondary-600">
          Review and edit your AI-generated social media posts for {postsData.topic}
        </p>
      </div>

      {/* Processing Info */}
      <div className="card mb-8">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-secondary-600">
              Generated from {postsData.articles.length} articles • 
              Processing time: {postsResponse.processingTime.toFixed(2)}s • 
              Model: {postsResponse.llmModelUsed}
            </p>
          </div>
        </div>
      </div>

      {/* Posts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* LinkedIn Post */}
        {postsResponse.posts.linkedin && (
          <div className="space-y-4">
            <h2 className="text-xl font-semibold text-gray-900 flex items-center">
              <svg className="w-6 h-6 mr-2 text-blue-700" fill="currentColor" viewBox="0 0 24 24">
                <path d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.238-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.79-1.75-1.764s.784-1.764 1.75-1.764 1.75.79 1.75 1.764-.783 1.764-1.75 1.764zm13.5 12.268h-3v-5.604c0-3.368-4-3.113-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.777 7 2.476v6.759z"/>
              </svg>
              LinkedIn Post
            </h2>
            <div className="card">
              <div className="mb-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-secondary-700">
                    Character Count
                  </span>
                  <span className={`text-sm font-medium ${
                    postsResponse.posts.linkedin.charCount > 2900 ? 'text-red-600' :
                    postsResponse.posts.linkedin.charCount > 2700 ? 'text-yellow-600' :
                    'text-green-600'
                  }`}>
                    {postsResponse.posts.linkedin.charCount} / 3000
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div 
                    className={`h-2 rounded-full ${
                      postsResponse.posts.linkedin.charCount > 2900 ? 'bg-red-600' :
                      postsResponse.posts.linkedin.charCount > 2700 ? 'bg-yellow-600' :
                      'bg-green-600'
                    }`}
                    style={{ width: `${Math.min((postsResponse.posts.linkedin.charCount / 3000) * 100, 100)}%` }}
                  />
                </div>
              </div>
              <div className="prose prose-sm max-w-none mb-4">
                <p className="whitespace-pre-wrap text-gray-800">
                  {postsResponse.posts.linkedin.content}
                </p>
              </div>
              {postsResponse.posts.linkedin.hashtags.length > 0 && (
                <div className="flex flex-wrap gap-2 mb-4">
                  {postsResponse.posts.linkedin.hashtags.map((tag, index) => (
                    <span key={index} className="text-blue-600 text-sm">
                      {tag}
                    </span>
                  ))}
                </div>
              )}
              <div className="flex justify-end space-x-3">
                <button
                  onClick={() => navigator.clipboard.writeText(postsResponse.posts.linkedin!.content)}
                  className="btn-secondary"
                >
                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                  Copy
                </button>
                <button
                  onClick={() => handleEdit('linkedin')}
                  className="btn-primary"
                >
                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                  </svg>
                  Edit
                </button>
              </div>
            </div>
          </div>
        )}

        {/* X Post */}
        {postsResponse.posts.x && (
          <div className="space-y-4">
            <h2 className="text-xl font-semibold text-gray-900 flex items-center">
              <svg className="w-6 h-6 mr-2" fill="currentColor" viewBox="0 0 24 24">
                <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
              </svg>
              X Post
            </h2>
            <div className="card">
              <div className="mb-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-secondary-700">
                    Character Count
                  </span>
                  <span className={`text-sm font-medium ${
                    postsResponse.posts.x.charCount > 240 ? 'text-red-600' :
                    postsResponse.posts.x.charCount > 220 ? 'text-yellow-600' :
                    'text-green-600'
                  }`}>
                    {postsResponse.posts.x.charCount} / 250
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div 
                    className={`h-2 rounded-full ${
                      postsResponse.posts.x.charCount > 240 ? 'bg-red-600' :
                      postsResponse.posts.x.charCount > 220 ? 'bg-yellow-600' :
                      'bg-green-600'
                    }`}
                    style={{ width: `${Math.min((postsResponse.posts.x.charCount / 250) * 100, 100)}%` }}
                  />
                </div>
              </div>
              <div className="prose prose-sm max-w-none mb-4">
                <p className="whitespace-pre-wrap text-gray-800">
                  {postsResponse.posts.x.content}
                </p>
              </div>
              {postsResponse.posts.x.hashtags.length > 0 && (
                <div className="flex flex-wrap gap-2 mb-4">
                  {postsResponse.posts.x.hashtags.map((tag, index) => (
                    <span key={index} className="text-blue-600 text-sm">
                      {tag}
                    </span>
                  ))}
                </div>
              )}
              <div className="flex justify-end space-x-3">
                <button
                  onClick={() => navigator.clipboard.writeText(postsResponse.posts.x!.content)}
                  className="btn-secondary"
                >
                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                  Copy
                </button>
                <button
                  onClick={() => handleEdit('x')}
                  className="btn-primary"
                >
                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                  </svg>
                  Edit
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

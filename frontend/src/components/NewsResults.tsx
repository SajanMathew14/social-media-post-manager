'use client'

import { useRouter } from 'next/navigation'
import { NewsResponse, NewsArticle, formatDate, extractDomain } from '@social-media-manager/shared'

interface NewsResultsProps {
  newsData: NewsResponse
  onRetry: () => void
  sessionId: string
  topic: string
  llmModel: string
}

export function NewsResults({ newsData, onRetry, sessionId, topic, llmModel }: NewsResultsProps) {
  const router = useRouter()
  const { articles, totalFound, processingTime, quotaRemaining, workflowId } = newsData

  const handleGeneratePosts = () => {
    // Navigate to posts page with necessary data
    const postsData = {
      articles,
      topic,
      llmModel,
      sessionId,
      newsWorkflowId: workflowId
    }
    
    // Store data in sessionStorage for the posts page
    sessionStorage.setItem('postsData', JSON.stringify(postsData))
    router.push('/posts')
  }

  if (!articles || articles.length === 0) {
    return (
      <div className="card text-center py-8">
        <div className="mx-auto h-12 w-12 text-secondary-400 mb-4">
          <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9.172 16.172a4 4 0 015.656 0M9 12h6m-6-4h6m2 5.291A7.962 7.962 0 0112 15c-2.34 0-4.44-.816-6.12-2.18C5.44 12.108 5 11.097 5 10c0-1.657.895-3.1 2.227-3.894a4.006 4.006 0 017.546 0C16.105 6.9 17 8.343 17 10c0 1.097-.44 2.108-.88 2.82A7.962 7.962 0 0112 15z" />
          </svg>
        </div>
        <h3 className="text-lg font-medium text-secondary-900 mb-2">
          No articles found
        </h3>
        <p className="text-secondary-600 mb-4">
          Try adjusting your search criteria or selecting a different date.
        </p>
        <button onClick={onRetry} className="btn-secondary">
          Try Again
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Results Header */}
      <div className="card">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">
              News Results
            </h2>
            <p className="text-sm text-secondary-600">
              Found {totalFound} articles • Processed in {processingTime.toFixed(2)}s • {quotaRemaining} requests remaining
            </p>
          </div>
          <button onClick={onRetry} className="btn-secondary">
            <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Refresh
          </button>
        </div>
      </div>

      {/* Articles Grid */}
      <div className="grid gap-4">
        {articles.map((article, index) => (
          <NewsArticleCard key={index} article={article} index={index} />
        ))}
      </div>

      {/* Generate Posts Button */}
      <button 
        onClick={handleGeneratePosts}
        className="btn-primary w-full mt-6 flex items-center justify-center"
        disabled={articles.length === 0}
      >
        <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
        </svg>
        Generate LinkedIn & X Posts
      </button>
    </div>
  )
}

interface NewsArticleCardProps {
  article: NewsArticle
  index: number
}

function NewsArticleCard({ article, index }: NewsArticleCardProps) {
  const domain = extractDomain(article.url)
  
  return (
    <div className="news-card animate-slide-up" style={{ animationDelay: `${index * 100}ms` }}>
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center space-x-2">
          <span className="inline-flex items-center justify-center w-6 h-6 bg-primary-100 text-primary-700 text-xs font-medium rounded-full">
            {index + 1}
          </span>
          <span className="text-sm text-secondary-500">{domain}</span>
          {article.relevanceScore && (
            <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
              {Math.round(article.relevanceScore * 100)}% relevant
            </span>
          )}
        </div>
        <div className="flex items-center space-x-2">
          {article.publishedAt && (
            <span className="text-xs text-secondary-500">
              {formatDate(new Date(article.publishedAt), 'display')}
            </span>
          )}
        </div>
      </div>

      <h3 className="text-lg font-semibold text-gray-900 mb-2 line-clamp-2">
        {article.title}
      </h3>

      <p className="text-secondary-700 mb-4 line-clamp-3">
        {article.summary}
      </p>

      <div className="flex items-center justify-between">
        <a
          href={article.url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center text-primary-600 hover:text-primary-700 font-medium text-sm transition-colors"
        >
          Read Full Article
          <svg className="w-4 h-4 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
          </svg>
        </a>

        <div className="flex items-center space-x-2">
          <button
            onClick={() => navigator.clipboard.writeText(article.url)}
            className="p-2 text-secondary-400 hover:text-secondary-600 transition-colors"
            title="Copy URL"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
          </button>
          
          <button
            onClick={() => {
              const shareText = `${article.title}\n\n${article.summary}\n\nRead more: ${article.url}`
              navigator.clipboard.writeText(shareText)
            }}
            className="p-2 text-secondary-400 hover:text-secondary-600 transition-colors"
            title="Copy for LinkedIn"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.367 2.684 3 3 0 00-5.367-2.684z" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  )
}

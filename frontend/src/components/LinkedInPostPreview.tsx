'use client'

import { useState } from 'react'

interface LinkedInPostPreviewProps {
  content: string
  charCount: number
  hashtags: string[]
  onEdit: () => void
  onCopy: () => void
}

export function LinkedInPostPreview({ 
  content, 
  charCount, 
  hashtags, 
  onEdit, 
  onCopy 
}: LinkedInPostPreviewProps) {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    onCopy()
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const getCharCountColor = () => {
    if (charCount > 2900) return 'text-red-600'
    if (charCount > 2700) return 'text-yellow-600'
    return 'text-green-600'
  }

  const getProgressBarColor = () => {
    if (charCount > 2900) return 'bg-red-600'
    if (charCount > 2700) return 'bg-yellow-600'
    return 'bg-green-600'
  }

  return (
    <div className="post-preview-card">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900 flex items-center">
          <svg className="w-5 h-5 mr-2 text-blue-700" fill="currentColor" viewBox="0 0 24 24">
            <path d="M19 0h-14c-2.761 0-5 2.239-5 5v14c0 2.761 2.239 5 5 5h14c2.762 0 5-2.239 5-5v-14c0-2.761-2.238-5-5-5zm-11 19h-3v-11h3v11zm-1.5-12.268c-.966 0-1.75-.79-1.75-1.764s.784-1.764 1.75-1.764 1.75.79 1.75 1.764-.783 1.764-1.75 1.764zm13.5 12.268h-3v-5.604c0-3.368-4-3.113-4 0v5.604h-3v-11h3v1.765c1.396-2.586 7-2.777 7 2.476v6.759z"/>
          </svg>
          LinkedIn Post
        </h3>
        <button
          onClick={onEdit}
          className="p-2 text-secondary-400 hover:text-secondary-600 transition-colors"
          title="Edit post"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
          </svg>
        </button>
      </div>

      {/* Character Count */}
      <div className="mb-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-secondary-700">
            Character Count
          </span>
          <span className={`text-sm font-medium char-counter ${getCharCountColor()}`}>
            {charCount} / 3000
          </span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div 
            className={`h-2 rounded-full transition-all duration-300 ${getProgressBarColor()}`}
            style={{ width: `${Math.min((charCount / 3000) * 100, 100)}%` }}
          />
        </div>
      </div>

      {/* Post Content */}
      <div className="mb-4">
        <div className="prose prose-sm max-w-none">
          <p className="whitespace-pre-wrap text-gray-800 leading-relaxed">
            {content}
          </p>
        </div>
      </div>

      {/* Hashtags */}
      {hashtags.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-4">
          {hashtags.map((tag, index) => (
            <span 
              key={index} 
              className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-700"
            >
              {tag}
            </span>
          ))}
        </div>
      )}

      {/* Actions */}
      <div className="flex justify-end space-x-3 pt-4 border-t border-gray-200">
        <button
          onClick={handleCopy}
          className="btn-secondary flex items-center"
        >
          {copied ? (
            <>
              <svg className="w-4 h-4 mr-2 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              Copied!
            </>
          ) : (
            <>
              <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
              Copy
            </>
          )}
        </button>
        <button
          onClick={onEdit}
          className="btn-primary flex items-center"
        >
          <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
          </svg>
          Edit Post
        </button>
      </div>
    </div>
  )
}

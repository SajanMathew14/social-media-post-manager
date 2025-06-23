import { 
  NewsArticle, 
  PostGenerationRequest, 
  PostGenerationResponse,
  GeneratedPost,
  LLMModel
} from '@social-media-manager/shared'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/**
 * Generate LinkedIn and X posts from news articles
 */
export async function generatePosts(
  articles: NewsArticle[],
  topic: string,
  llmModel: string,
  sessionId: string,
  newsWorkflowId: string
): Promise<PostGenerationResponse> {
  const request: PostGenerationRequest = {
    articles,
    topic,
    llmModel: llmModel as LLMModel,
    sessionId,
    newsWorkflowId
  }

  const response = await fetch(`${API_BASE_URL}/api/posts/generate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail?.message || 'Failed to generate posts')
  }

  return response.json()
}

/**
 * Update the content of a generated post
 */
export async function updatePost(
  postId: string,
  content: string
): Promise<GeneratedPost> {
  const response = await fetch(`${API_BASE_URL}/api/posts/${postId}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ content }),
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail?.message || 'Failed to update post')
  }

  return response.json()
}

/**
 * Get all posts for a session
 */
export async function getSessionPosts(
  sessionId: string,
  postType?: 'linkedin' | 'x'
): Promise<GeneratedPost[]> {
  const params = new URLSearchParams({ session_id: sessionId })
  if (postType) {
    params.append('post_type', postType)
  }

  const response = await fetch(`${API_BASE_URL}/api/posts/session/${sessionId}?${params}`)

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail?.message || 'Failed to fetch posts')
  }

  return response.json()
}

/**
 * Get a specific post by ID
 */
export async function getPost(postId: string): Promise<GeneratedPost> {
  const response = await fetch(`${API_BASE_URL}/api/posts/${postId}`)

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail?.message || 'Failed to fetch post')
  }

  return response.json()
}

/**
 * Delete a generated post
 */
export async function deletePost(postId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/posts/${postId}`, {
    method: 'DELETE',
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail?.message || 'Failed to delete post')
  }
}

import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Social Media Post Manager',
  description: 'AI-powered LinkedIn content manager for professionals',
  keywords: ['LinkedIn', 'content management', 'AI', 'social media', 'news'],
  authors: [{ name: 'Social Media Post Manager Team' }],
  viewport: 'width=device-width, initial-scale=1',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50">
        <div className="flex flex-col min-h-screen">
          <header className="bg-white shadow-sm border-b border-secondary-200">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              <div className="flex justify-between items-center h-16">
                <div className="flex items-center">
                  <h1 className="text-xl font-bold text-gradient">
                    Social Media Manager
                  </h1>
                  <span className="ml-2 px-2 py-1 text-xs bg-primary-100 text-primary-700 rounded-full">
                    MVP
                  </span>
                </div>
                <nav className="flex items-center space-x-4">
                  <span className="text-sm text-secondary-600">
                    LinkedIn Content Manager
                  </span>
                </nav>
              </div>
            </div>
          </header>
          
          <main className="flex-1">
            {children}
          </main>
          
          <footer className="bg-white border-t border-secondary-200 py-6">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              <div className="text-center text-sm text-secondary-500">
                <p>© 2025 Social Media Post Manager. Built with Next.js, FastAPI, and LangGraph.</p>
                <p className="mt-1">Phase 1: LinkedIn News Aggregation & Content Generation</p>
              </div>
            </div>
          </footer>
        </div>
      </body>
    </html>
  )
}

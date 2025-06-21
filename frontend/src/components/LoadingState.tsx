'use client'

import { ProcessingStep } from '@social-media-manager/shared'

interface LoadingStateProps {
  steps?: ProcessingStep[]
  currentStep: string
}

export function LoadingState({ steps = [], currentStep }: LoadingStateProps) {
  return (
    <div className="card">
      <div className="flex items-center justify-center mb-6">
        <div className="loading-spinner mr-3"></div>
        <h3 className="text-lg font-medium text-gray-900">
          Processing your request...
        </h3>
      </div>

      <div className="space-y-3">
        {steps.length > 0 ? (
          steps.map((step, index) => (
            <div key={index} className="flex items-center space-x-3">
              <div className="flex-shrink-0">
                {step.status === 'completed' && (
                  <div className="w-5 h-5 bg-green-500 rounded-full flex items-center justify-center">
                    <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                  </div>
                )}
                {step.status === 'processing' && (
                  <div className="w-5 h-5 border-2 border-primary-600 border-t-transparent rounded-full animate-spin"></div>
                )}
                {step.status === 'pending' && (
                  <div className="w-5 h-5 bg-secondary-300 rounded-full"></div>
                )}
                {step.status === 'error' && (
                  <div className="w-5 h-5 bg-red-500 rounded-full flex items-center justify-center">
                    <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                    </svg>
                  </div>
                )}
              </div>
              <div className="flex-1">
                <p className={`text-sm ${
                  step.status === 'completed' ? 'text-green-700' :
                  step.status === 'processing' ? 'text-primary-700' :
                  step.status === 'error' ? 'text-red-700' :
                  'text-secondary-500'
                }`}>
                  {step.step}
                </p>
                {step.message && (
                  <p className="text-xs text-secondary-500 mt-1">{step.message}</p>
                )}
              </div>
            </div>
          ))
        ) : (
          <div className="text-center py-4">
            <p className="text-secondary-600">{currentStep}</p>
          </div>
        )}
      </div>

      <div className="mt-6 bg-secondary-50 rounded-lg p-4">
        <div className="flex items-center">
          <div className="flex-shrink-0">
            <svg className="h-5 w-5 text-secondary-400" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
            </svg>
          </div>
          <div className="ml-3">
            <p className="text-sm text-secondary-700">
              This may take 15-30 seconds depending on the complexity of your request.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

'use client'

import { QuotaInfo } from '@social-media-manager/shared'

interface QuotaDisplayProps {
  quotaInfo: QuotaInfo
}

export function QuotaDisplay({ quotaInfo }: QuotaDisplayProps) {
  const { dailyUsed, dailyLimit, monthlyUsed, monthlyLimit } = quotaInfo
  
  const dailyPercentage = (dailyUsed / dailyLimit) * 100
  const monthlyPercentage = (monthlyUsed / monthlyLimit) * 100
  
  const getDailyColor = () => {
    if (dailyPercentage >= 90) return 'bg-red-500'
    if (dailyPercentage >= 70) return 'bg-yellow-500'
    return 'bg-primary-600'
  }

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-medium text-gray-900">Usage Quota</h3>
        <span className="text-sm text-secondary-500">
          Resets daily at midnight
        </span>
      </div>
      
      <div className="space-y-4">
        {/* Daily Quota */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">Daily Usage</span>
            <span className="text-sm text-secondary-600">
              {dailyUsed} / {dailyLimit} requests
            </span>
          </div>
          <div className="quota-bar">
            <div 
              className={`quota-fill ${getDailyColor()}`}
              style={{ width: `${Math.min(dailyPercentage, 100)}%` }}
            />
          </div>
        </div>

        {/* Monthly Quota */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">Monthly Usage</span>
            <span className="text-sm text-secondary-600">
              {monthlyUsed} / {monthlyLimit} requests
            </span>
          </div>
          <div className="quota-bar">
            <div 
              className="quota-fill bg-secondary-400"
              style={{ width: `${Math.min(monthlyPercentage, 100)}%` }}
            />
          </div>
        </div>
      </div>

      {dailyUsed >= dailyLimit && (
        <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-700">
            Daily quota exceeded. Please try again tomorrow.
          </p>
        </div>
      )}
    </div>
  )
}

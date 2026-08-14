import React from 'react'
import ReactDOM from 'react-dom/client'
import { RouterProvider } from 'react-router-dom'
import { QueryClientProvider } from '@tanstack/react-query'
import { TooltipProvider } from '@/components/ui/tooltip'
import { Toaster } from 'sonner'
import { queryClient } from '@/lib/query'
import { router } from '@/app/router'
import '@/index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <TooltipProvider delayDuration={200}>
        <RouterProvider router={router} />
        <Toaster
          theme="dark"
          position="top-right"
          richColors
          toastOptions={{
            style: { background: 'hsl(var(--card))', border: '1px solid hsl(var(--border))' },
          }}
        />
      </TooltipProvider>
    </QueryClientProvider>
  </React.StrictMode>,
)

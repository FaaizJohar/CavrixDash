import { createBrowserRouter, Navigate, useParams } from 'react-router-dom'
import { AppShell } from '@/components/layout/app-shell'
import { ProtectedRoute } from '@/app/protected-route'
import { Splash } from '@/components/shared/splash'
import { LoginPage } from '@/features/auth/login'
import { RegisterPage } from '@/features/auth/register'
import { ForgotPasswordPage } from '@/features/auth/forgot-password'
import { ResetPasswordPage } from '@/features/auth/reset-password'
import { VerifyEmailPage } from '@/features/auth/verify-email'
import { TwoFactorPage } from '@/features/auth/two-factor'
import { TwoFactorSetupPage } from '@/features/auth/two-factor-setup'
import { OverviewPage } from '@/features/dashboard/overview'
import { EarnPage } from '@/features/earn/earn-page'
import { MyTasks } from '@/features/earn/my-tasks'
import { OfferwallPage } from '@/features/earn/offerwall'
import { RewardsPage } from '@/features/rewards/rewards-page'
import { WalletPage } from '@/features/rewards/wallet'
import { ServersRewardPage } from '@/features/rewards/servers'
import { UpgradesPage } from '@/features/rewards/upgrades'
import { MyServersPage } from '@/features/minecraft/my-servers'
import { CreateServerPage } from '@/features/minecraft/create-server'
import { TemplatesPage } from '@/features/minecraft/templates'
import { ServerDetailPage } from '@/features/minecraft/server-detail'
import { ServerConsole } from '@/features/minecraft/console'
import { AnalyticsPage } from '@/features/analytics/analytics-page'
import { ReferralsPage } from '@/features/referrals/referrals-page'
import { SupportPage } from '@/features/support/support-page'
import { SettingsPage } from '@/features/settings/settings-page'
import { AdminLayout } from '@/features/admin/admin-layout'
import { AdminRoute } from '@/app/admin-route'
import { AdminOverviewPage } from '@/features/admin/overview'
import { AdminUsersPage } from '@/features/admin/users'
import { AdminOffersPage } from '@/features/admin/offers'
import { AdminProvidersPage } from '@/features/admin/providers'
import { AdminConversionsPage } from '@/features/admin/conversions'
import { AdminEconomyPage } from '@/features/admin/economy'
import { AdminMinecraftPage } from '@/features/admin/minecraft'
import { AdminRevenuePage } from '@/features/admin/revenue'
import { AdminFraudPage } from '@/features/admin/fraud'
import { AdminAnalyticsPage } from '@/features/admin/analytics'
import { AdminSupportPage } from '@/features/admin/support'
import { AdminAnnouncementsPage } from '@/features/admin/announcements'
import { AdminAuditPage } from '@/features/admin/audit'
import { AdminSettingsPage } from '@/features/admin/settings'
import { AdminSecretsPage } from '@/features/admin/secrets'

export const router = createBrowserRouter([
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    path: '/register',
    element: <RegisterPage />,
  },
  {
    path: '/forgot-password',
    element: <ForgotPasswordPage />,
  },
  {
    path: '/reset-password',
    element: <ResetPasswordPage />,
  },
  {
    path: '/verify-email',
    element: <VerifyEmailPage />,
  },
  {
    path: '/2fa',
    element: <TwoFactorPage />,
  },
  {
    path: '/2fa/setup',
    element: <TwoFactorSetupPage />,
  },
  {
    path: '/',
    element: (
      <ProtectedRoute>
        <AppShell />
      </ProtectedRoute>
    ),
    children: [
      { index: true, element: <OverviewPage /> },
      { path: 'earn', element: <EarnPage /> },
      { path: 'earn/offerwall', element: <OfferwallPage /> },
      { path: 'earn/my-tasks', element: <MyTasks /> },
      { path: 'rewards', element: <RewardsPage /> },
      { path: 'rewards/wallet', element: <WalletPage /> },
      { path: 'rewards/servers', element: <ServersRewardPage /> },
      { path: 'rewards/upgrades', element: <UpgradesPage /> },
      { path: 'minecraft', element: <MyServersPage /> },
      { path: 'minecraft/new', element: <CreateServerPage /> },
      { path: 'minecraft/templates', element: <TemplatesPage /> },
      { path: 'minecraft/:id', element: <ServerDetailPage /> },
      { path: 'minecraft/:id/console', element: <ConsoleRoute /> },
      { path: 'analytics', element: <AnalyticsPage /> },
      { path: 'referrals', element: <ReferralsPage /> },
      { path: 'support', element: <SupportPage /> },
      { path: 'settings', element: <SettingsPage /> },
      {
        path: 'admin',
        element: (
          <AdminRoute>
            <AdminLayout />
          </AdminRoute>
        ),
        children: [
          { index: true, element: <AdminOverviewPage /> },
          { path: 'users', element: <AdminUsersPage /> },
          { path: 'offers', element: <AdminOffersPage /> },
          { path: 'providers', element: <AdminProvidersPage /> },
          { path: 'conversions', element: <AdminConversionsPage /> },
          { path: 'economy', element: <AdminEconomyPage /> },
          { path: 'minecraft', element: <AdminMinecraftPage /> },
          { path: 'revenue', element: <AdminRevenuePage /> },
          { path: 'fraud', element: <AdminFraudPage /> },
          { path: 'analytics', element: <AdminAnalyticsPage /> },
          { path: 'support', element: <AdminSupportPage /> },
          { path: 'announcements', element: <AdminAnnouncementsPage /> },
          { path: 'audit', element: <AdminAuditPage /> },
          { path: 'settings', element: <AdminSettingsPage /> },
          { path: 'secrets', element: <AdminSecretsPage /> },
        ],
      },
    ],
  },
  {
    path: '*',
    element: <Navigate to="/" replace />,
  },
])

function ConsoleRoute() {
  const { id } = useParams()
  if (!id) return <Navigate to="/minecraft" replace />
  return <ServerConsole serverId={id} />
}

export { Splash }

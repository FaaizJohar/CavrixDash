// Mirrors backend/app/schemas — keep in sync with the API contract.

export interface ApiErrorDetail {
  message: string
  code: string
  ref: string
  details?: unknown
}

export interface ApiErrorResponse {
  detail: ApiErrorDetail
}

export interface Paginated<T> {
  items: T[]
  total: number
  page: number
  pages: number
  page_size: number
}

export interface UserOut {
  id: string
  email: string
  username: string
  display_name: string
  avatar_url: string
  referral_code: string
  email_verified: boolean
  twofa_enabled: boolean
  status: string
  roles: string[]
  created_at?: string | null
  updated_at?: string | null
}

export interface UserMe extends UserOut {
  cvx_balance: number
  cvx_lifetime_earned: number
  cvx_lifetime_spent: number
  tasks_completed: number
  conversions_approved: number
  conversions_pending: number
  active_servers: number
  server_limit: number
  is_super_admin: boolean
  is_admin: boolean
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
  user: UserOut
}

export interface MfaSetupInfo {
  secret: string
  uri: string
  qr_base64: string
}

export interface TwoFaSetupLoginResponse extends TokenResponse {
  backup_codes: string[]
}

export interface SessionOut {
  id: string
  device_name: string
  ip: string
  created_at?: string | null
  last_seen_at: string
  current: boolean
}

export interface SecurityState {
  email_verified: boolean
  twofa_enabled: boolean
  has_backup_codes: boolean
  password_last_changed?: string | null
  sessions: SessionOut[]
}

export interface TwoFaSetupResponse {
  secret: string
  uri: string
  qr_base64: string
  backup_codes: string[]
}

export interface OfferOut {
  id: string
  provider_code: string
  provider_name: string
  provider_kind: string
  title: string
  description: string
  category: string
  icon_url: string
  reward: number
  estimated_time: number
  countries: string[]
  devices: string[]
  requirements: string
  conversion_event: string
  featured: boolean
  priority: number
  status: string
  conversion_rate: number
  approval_rate: number
  completion_count: number
  effective_reward: number
  click_url: string
  starts_at: string
  expires_at: string
  created_at?: string | null
}

export interface OfferDetail extends OfferOut {
  landing_url: string
}

export interface ClickResponse {
  click_id: string
  redirect_url: string
  expires_in: number
}

export interface TaskOut {
  id: string
  click_id: string
  offer_id: string
  offer_title: string
  provider_code: string
  category: string
  reward_offered: number
  status: string
  risk_score: number
  external_tx_id: string
  created_at?: string | null
  updated_at?: string | null
}

export interface ConversionOut {
  id: string
  click_id: string
  offer_id: string
  offer_title: string
  provider_code: string
  conversion_id: string
  status: string
  reward_amount: number
  risk_score: number
  created_at?: string | null
  updated_at?: string | null
}

export interface WalletOut {
  balance: number
  lifetime_earned: number
  lifetime_spent: number
  daily_limit: number
  hourly_limit: number
  max_balance: number
  earned_today: number
  earned_this_hour: number
}

export interface LedgerEntry {
  id: string
  transaction_type: string
  amount: number
  balance_after: number
  reference_type: string
  reference_id: string
  description: string
  created_at?: string | null
}

export interface CvxRuleOut {
  key: string
  value: string
  kind: string
  label: string
  section: string
}

export interface PlanOut {
  id: string
  name: string
  description: string
  cpu: number
  ram_mb: number
  disk_mb: number
  backups: number
  databases: number
  allocations: number
  region: string
  egg_id: string
  nest_id: string
  docker_image: string
  startup: string
  cvx_cost: number
  renewal_cost: number
  duration_days: number
  max_servers_per_user: number
  status: string
  sort_order: number
  created_at?: string | null
}

export interface ServerLive {
  status?: string
  online?: boolean
  cpu_absolute?: number
  cpu_percent?: number
  memory_bytes?: number
  memory_percent?: number
  disk_bytes?: number
  disk_percent?: number
  network_rx?: number
  network_tx?: number
  players?: number
  uptime?: number
  ip?: string
  port?: number
}

export interface ServerOut {
  id: string
  plan_id: string
  plan_name: string
  pterodactyl_server_id: string
  name: string
  region: string
  status: string
  ip: string
  port: number
  cpu: number
  ram_mb: number
  disk_mb: number
  backups: number
  databases: number
  allocations: number
  software: string
  version: string
  expires_at: string
  node?: unknown
  live?: ServerLive
  created_at?: string | null
}

export interface RegionOut {
  code: string
  name: string
  flag: string
  enabled: boolean
  priority: number
}

export interface NodeOut {
  id: string
  name: string
  region: string
  fqdn: string
  memory_allocated: number
  memory_limit: number
  disk_allocated: number
  disk_limit: number
  enabled: boolean
  status: string
}

export interface TemplateOut {
  id: string
  name: string
  software: string
  versions: string[]
  egg_id: string
  nest_id: string
  docker_image: string
  startup: string
  default_plan_id: string
  enabled: boolean
}

export interface UpgradePriceOut {
  upgrade_type: string
  label: string
  unit: string
  unit_size: number
  cvx_cost: number
  enabled: boolean
}

export interface UpgradeQuote {
  server_id: string
  upgrade_type: string
  amount: number
  cvx_cost: number
  label: string
  unit: string
  new_value: number
  current_value: number
}

export interface UpgradeOut {
  id: string
  server_id: string
  upgrade_type: string
  label: string
  amount: number
  unit: string
  cvx_cost: number
  status: string
  created_at?: string | null
}

export interface ReferralSummary {
  code: string
  url: string
  reward: number
  total_invited: number
  verified: number
  rewarded: number
  pending: number
  earnings: number
  max_monthly: number
  referrals_this_month: number
}

export interface ReferralRow {
  id: string
  invitee_email: string
  status: string
  reward_amount: number
  rewarded_at: string
  risk_score: number
  created_at?: string | null
}

export interface OverviewStats {
  cvx_balance: number
  cvx_symbol: string
  active_servers: number
  server_limit: number
  tasks_completed: number
  conversions_approved: number
  conversions_pending: number
  daily_limit: number
  earned_today: number
  next_reward_target: number
  next_reward_progress: number
  recent_ledger: Array<Record<string, unknown>>
  recommended_offers: Array<Record<string, unknown>>
  servers: Array<Record<string, unknown>>
  notifications: Array<Record<string, unknown>>
  server_health: Record<string, unknown>
}

export interface NotificationOut {
  id: string
  kind: string
  title: string
  body: string
  link: string
  read: boolean
  priority: string
  created_at?: string | null
}

export interface TicketOut {
  id: string
  subject: string
  category: string
  status: string
  priority: string
  created_at?: string | null
  updated_at?: string | null
  last_message: string
}

export interface TicketDetail {
  id: string
  subject: string
  category: string
  status: string
  priority: string
  messages: Array<Record<string, unknown>>
  created_at?: string | null
}

// ---------------- Admin ----------------

export interface Kpi {
  key: string
  label: string
  value: unknown
  delta?: unknown
}

export interface AdminOverview {
  total_revenue: number
  today_revenue: number
  pending_revenue: number
  users: number
  active_users: number
  active_servers: number
  tasks_completed: number
  approved: number
  rejected: number
  reversed: number
  cvx_issued: number
  cvx_spent: number
  cvx_outstanding: number
  provider_revenue: Array<Record<string, unknown>>
  revenue_7d: Array<Record<string, unknown>>
  risk_events_24h: number
}

export interface AdminUserRow {
  id: string
  email: string
  username: string
  display_name: string
  email_verified: boolean
  twofa_enabled: boolean
  status: string
  risk_score: number
  cvx_balance: number
  tasks_completed: number
  conversions_approved: number
  active_servers: number
  roles: string[]
  created_at?: string | null
}

export interface ProviderOut {
  id: string
  code: string
  name: string
  kind: string
  enabled: boolean
  status: string
  priority: number
  reward_multiplier: number
  reliability: number
  revenue_tracked: number
  last_synced_at: string
  last_error: string
  credentials_masked: Record<string, string>
  meta: Record<string, unknown>
  created_at?: string | null
}

export interface AuditRow {
  id: string
  actor_name: string
  action: string
  category: string
  target_type: string
  target_id: string
  old_value: string
  new_value: string
  ip: string
  result: string
  created_at?: string | null
}

export interface AnnouncementOut {
  id: string
  title: string
  message: string
  audience: string
  priority: string
  starts_at: string
  ends_at: string
  enabled: boolean
  created_at?: string | null
}

export interface FraudEventOut {
  id: string
  user_id: string
  event_type: string
  severity: string
  description: string
  details: string
  created_at?: string | null
}

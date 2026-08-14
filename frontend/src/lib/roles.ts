export type AdminScope = 'super' | 'admin' | 'finance' | 'infra'

const ROLE_SCOPE: Record<string, AdminScope> = {
  super_admin: 'super',
  admin: 'admin',
  finance_admin: 'finance',
  infra_admin: 'infra',
}

export function adminScopes(roles: string[]): AdminScope[] {
  return roles.map((r) => ROLE_SCOPE[r]).filter((s): s is AdminScope => !!s)
}

export function canAccessAdmin(roles: string[]): boolean {
  return adminScopes(roles).length > 0
}

export function adminTitle(roles: string[]): string {
  const scopes = adminScopes(roles)
  if (scopes.includes('super')) return 'Super Admin'
  if (scopes.includes('admin')) return 'Admin'
  if (scopes.includes('finance') && scopes.includes('infra')) return 'Finance & Infra Admin'
  if (scopes.includes('finance')) return 'Finance Admin'
  if (scopes.includes('infra')) return 'Infra Admin'
  return 'Admin'
}

export function hasScope(roles: string[], scope: AdminScope): boolean {
  return adminScopes(roles).includes(scope)
}
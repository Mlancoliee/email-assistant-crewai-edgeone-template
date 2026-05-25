/**
 * Linear-style design tokens — aligned with the sibling
 * marketing-campaign-planner-crewai template so the whole Pages Agents
 * template family feels like one product (white surface, neutral grays,
 * single brand purple, 4/8 spacing scale, subtle borders).
 */

export const tokens = {
  color: {
    // Surfaces — layered: bg (canvas) → surface (panel) → surfaceElevated (card)
    bg: '#ffffff',
    surface: '#fafafa',
    surfaceHover: '#f4f4f5',
    surfaceMuted: '#f8fafc',
    surfaceElevated: '#ffffff',
    // Subtle gradient used for hero / brand surfaces (ConversationStream
    // onboarding, header accent line)
    gradientBrand: 'linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%)',
    gradientBrandStrong: 'linear-gradient(135deg, #7c3aed 0%, #a855f7 100%)',

    // Borders — borderSubtle for ultra-quiet dividers (inside cards)
    border: '#e5e7eb',
    borderStrong: '#d4d4d8',
    borderSubtle: '#f1f1f3',

    // Text
    text: '#0a0a0a',
    textMuted: '#52525b',
    textSubtle: '#71717a',
    textDisabled: '#a1a1aa',
    textInverted: '#ffffff',

    // Brand
    brand: '#7c3aed',
    brandHover: '#6d28d9',
    brandSoft: '#f5f3ff',
    brandSofter: '#faf8ff',
    brandBorder: '#ddd6fe',

    // Status
    success: '#16a34a',
    successSoft: '#f0fdf4',
    warning: '#ca8a04',
    warningSoft: '#fefce8',
    danger: '#dc2626',
    dangerSoft: '#fef2f2',
    info: '#0ea5e9',
    infoSoft: '#f0f9ff',

    // Email category palette (semantic mapping for the inbox tree)
    categoryUrgent: '#dc2626',
    categoryMeeting: '#0ea5e9',
    categoryInternal: '#7c3aed',
    categoryMarketing: '#ca8a04',
    categoryNotification: '#52525b',
    categoryFollowup: '#16a34a',
    categorySpam: '#a1a1aa',
    categoryBilling: '#7c3aed',
    categoryOther: '#71717a',
  },

  font: {
    sans: "'Inter', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    mono: "'JetBrains Mono', ui-monospace, 'SF Mono', Menlo, monospace",
  },

  fontSize: {
    xs: 11,
    sm: 12,
    base: 13,
    md: 14,
    lg: 15,
    xl: 18,
    '2xl': 22,
    '3xl': 28,
  },

  fontWeight: {
    regular: 400,
    medium: 500,
    semibold: 600,
    bold: 700,
  },

  lineHeight: {
    tight: 1.3,
    snug: 1.45,
    normal: 1.6,
  },

  space: {
    1: 4,
    2: 8,
    3: 12,
    4: 16,
    5: 20,
    6: 24,
    8: 32,
    10: 40,
    12: 48,
  },

  radius: {
    sm: 4,
    md: 6,
    lg: 8,
    xl: 12,
    '2xl': 16,
    pill: 999,
  },

  shadow: {
    sm: '0 1px 2px rgba(15, 23, 42, 0.04)',
    md: '0 1px 3px rgba(15, 23, 42, 0.06), 0 1px 2px rgba(15, 23, 42, 0.04)',
    pop: '0 8px 24px rgba(15, 23, 42, 0.08), 0 2px 4px rgba(15, 23, 42, 0.04)',
    // Used on the active "in flight" node + DraftReviewCard for that
    // "this is the focal point of the screen" feeling.
    focus: '0 4px 16px rgba(124, 58, 237, 0.12), 0 1px 3px rgba(124, 58, 237, 0.08)',
    inset: 'inset 0 0 0 1px rgba(15, 23, 42, 0.04)',
  },

  motion: {
    fast: '120ms ease',
    base: '180ms ease',
    slow: '240ms cubic-bezier(0.2, 0, 0, 1)',
    spring: '320ms cubic-bezier(0.34, 1.56, 0.64, 1)',
  },
} as const;

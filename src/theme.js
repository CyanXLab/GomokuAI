/**
 * Theme manager for GomokuAI.
 * Supports 'auto' (follow system), 'light', and 'dark'.
 * Applies theme by setting data-theme attribute on <html> and CSS variables.
 */

const THEME_STORAGE_KEY = 'gomokuai_theme'

export const THEMES = ['auto', 'light', 'dark']

let mediaQuery = null
let currentThemeMode = 'auto'

/** Get the system dark-mode preference. */
function getSystemTheme() {
  return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches
    ? 'dark'
    : 'light'
}

/** Apply the resolved theme to the document root. */
function applyResolvedTheme(resolved) {
  document.documentElement.setAttribute('data-theme', resolved)
  // Update theme-color meta for mobile browser UI
  const metaTheme = document.querySelector('meta[name="theme-color"]')
  if (metaTheme) {
    metaTheme.setAttribute('content', resolved === 'dark' ? '#1f1f1f' : '#0078d4')
  }
}

/** Resolve 'auto' to actual light/dark based on system preference. */
function resolveTheme(mode) {
  return mode === 'auto' ? getSystemTheme() : mode
}

/** Set the theme mode and apply it. */
export function setTheme(mode) {
  if (!THEMES.includes(mode)) mode = 'auto'
  currentThemeMode = mode
  localStorage.setItem(THEME_STORAGE_KEY, mode)
  applyResolvedTheme(resolveTheme(mode))

  // Listen for system theme changes when in auto mode
  if (mode === 'auto' && window.matchMedia) {
    if (!mediaQuery) {
      mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
      mediaQuery.addEventListener('change', () => {
        if (currentThemeMode === 'auto') {
          applyResolvedTheme(getSystemTheme())
        }
      })
    }
  }
}

/** Get the stored theme mode, defaulting to 'auto'. */
export function getStoredTheme() {
  const stored = localStorage.getItem(THEME_STORAGE_KEY)
  return THEMES.includes(stored) ? stored : 'auto'
}

/** Initialize theme on app startup. Call this as early as possible. */
export function initTheme() {
  setTheme(getStoredTheme())
}

/**
 * Inline script to run before the app renders, to prevent flash of wrong theme.
 * Inject this into index.html <head>.
 */
export const themeInlineScript = `
<script>
(function() {
  try {
    var t = localStorage.getItem('gomokuai_theme') || 'auto';
    var dark = t === 'dark' || (t === 'auto' && window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches);
    document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light');
  } catch(e) {}
})();
<\/script>
`

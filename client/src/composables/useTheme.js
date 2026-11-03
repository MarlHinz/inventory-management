import { ref } from 'vue'

// Module-level so every caller shares one theme. Initial value comes from the
// attribute the inline script in index.html already set before first paint.
const theme = ref(document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light')

const apply = (value) => {
  theme.value = value
  document.documentElement.dataset.theme = value
  try {
    localStorage.setItem('theme', value)
  } catch (e) {
    // Storage can be blocked (private mode); the theme still applies for this session.
  }
}

export function useTheme() {
  const toggleTheme = () => apply(theme.value === 'dark' ? 'light' : 'dark')
  return { theme, toggleTheme }
}

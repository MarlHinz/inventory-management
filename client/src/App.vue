<template>
  <div class="app">
    <!-- Mobile top bar (< 1024px): hamburger + logo -->
    <header class="topbar">
      <button
        ref="menuButton"
        class="icon-btn"
        type="button"
        aria-controls="app-sidebar"
        :aria-expanded="drawerOpen ? 'true' : 'false'"
        :aria-label="t('nav.openMenu')"
        @click="openDrawer"
      >
        <svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M4 6h16 M4 12h16 M4 18h16" /></svg>
      </button>
      <BrandLogo class="topbar-logo" />
    </header>

    <div class="overlay" :class="{ visible: drawerOpen }" aria-hidden="true" @click="closeDrawer"></div>

    <aside id="app-sidebar" ref="sidebar" class="sidebar" :class="{ open: drawerOpen }" tabindex="-1">
      <div class="sidebar-head">
        <div class="logo">
          <BrandLogo class="logo-mark" />
          <span class="logo-sub">{{ t('nav.subtitle') }}</span>
        </div>
        <button class="icon-btn close-drawer" type="button" :aria-label="t('nav.closeMenu')" @click="closeDrawer">
          <svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12 M18 6L6 18" /></svg>
        </button>
      </div>

      <nav class="sidebar-nav" :aria-label="t('nav.mainNav')">
        <router-link
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="nav-link"
          active-class=""
          exact-active-class="active"
        >
          <svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path :d="item.icon" /></svg>
          <span>{{ t(item.label) }}</span>
        </router-link>
      </nav>

      <div class="sidebar-footer">
        <div class="footer-row">
          <LanguageSwitcher />
          <button
            class="theme-toggle"
            type="button"
            :aria-pressed="theme === 'dark' ? 'true' : 'false'"
            :aria-label="t('nav.darkMode')"
            :title="t('nav.darkMode')"
            @click="toggleTheme"
          >
            <svg v-if="theme === 'dark'" class="icon" viewBox="0 0 24 24" aria-hidden="true">
              <path d="M12 8a4 4 0 100 8 4 4 0 000-8z M12 2v2 M12 20v2 M4.9 4.9l1.4 1.4 M17.7 17.7l1.4 1.4 M2 12h2 M20 12h2 M4.9 19.1l1.4-1.4 M17.7 6.3l1.4-1.4" />
            </svg>
            <svg v-else class="icon" viewBox="0 0 24 24" aria-hidden="true">
              <path d="M21 12.8A9 9 0 1111.2 3a7 7 0 009.8 9.8z" />
            </svg>
          </button>
        </div>
        <ProfileMenu
          @show-profile-details="showProfileDetails = true"
          @show-tasks="showTasks = true"
        />
      </div>
    </aside>

    <div class="content">
      <FilterBar />
      <main class="main-content">
        <router-view />
      </main>
    </div>

    <ProfileDetailsModal
      :is-open="showProfileDetails"
      @close="showProfileDetails = false"
    />

    <TasksModal
      :is-open="showTasks"
      :tasks="tasks"
      @close="showTasks = false"
      @add-task="addTask"
      @delete-task="deleteTask"
      @toggle-task="toggleTask"
    />
  </div>
</template>

<script>
import { ref, onMounted, onBeforeUnmount, computed, watch, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { api } from './api'
import { useAuth } from './composables/useAuth'
import { useI18n } from './composables/useI18n'
import { useTheme } from './composables/useTheme'
import FilterBar from './components/FilterBar.vue'
import ProfileMenu from './components/ProfileMenu.vue'
import ProfileDetailsModal from './components/ProfileDetailsModal.vue'
import TasksModal from './components/TasksModal.vue'
import LanguageSwitcher from './components/LanguageSwitcher.vue'
import BrandLogo from './components/BrandLogo.vue'

// 24x24 stroke icons, one path string each
const navItems = [
  { to: '/', label: 'nav.overview', icon: 'M3 3h7v7H3z M14 3h7v7h-7z M14 14h7v7h-7z M3 14h7v7H3z' },
  { to: '/inventory', label: 'nav.inventory', icon: 'M21 8l-9-5-9 5v8l9 5 9-5z M3 8l9 5 9-5 M12 13v8' },
  { to: '/orders', label: 'nav.orders', icon: 'M9 4h6a1 1 0 011 1v1H8V5a1 1 0 011-1z M8 6H6a1 1 0 00-1 1v13a1 1 0 001 1h12a1 1 0 001-1V7a1 1 0 00-1-1h-2 M9 12h6 M9 16h4' },
  { to: '/spending', label: 'nav.finance', icon: 'M12 2v20 M17 6H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6' },
  { to: '/demand', label: 'nav.demandForecast', icon: 'M3 17l6-6 4 4 8-8 M15 7h6v6' },
  { to: '/restocking', label: 'nav.restocking', icon: 'M21 12a9 9 0 01-15.5 6.2 M3 12A9 9 0 0118.5 5.8 M21 4v5h-5 M3 20v-5h5' },
  { to: '/reports', label: 'nav.reports', icon: 'M14 3H7a2 2 0 00-2 2v14a2 2 0 002 2h10a2 2 0 002-2V8z M14 3v5h5 M9 13h6 M9 17h6' }
]

export default {
  name: 'App',
  components: {
    FilterBar,
    ProfileMenu,
    ProfileDetailsModal,
    TasksModal,
    LanguageSwitcher,
    BrandLogo
  },
  setup() {
    const { currentUser } = useAuth()
    const { t } = useI18n()
    const { theme, toggleTheme } = useTheme()
    const route = useRoute()
    const showProfileDetails = ref(false)
    const showTasks = ref(false)
    const apiTasks = ref([])

    // Mobile drawer
    const drawerOpen = ref(false)
    const menuButton = ref(null)
    const sidebar = ref(null)

    const openDrawer = async () => {
      drawerOpen.value = true
      // Wait for the drawer to become visible (it is visibility:hidden while closed,
      // so it cannot take focus before this tick), then move focus inside it.
      await nextTick()
      sidebar.value?.querySelector('.nav-link')?.focus()
    }

    const closeDrawer = () => {
      if (!drawerOpen.value) return
      drawerOpen.value = false
      // Return focus to the control that opened the drawer
      menuButton.value?.focus()
    }

    const onKeydown = (e) => {
      if (e.key === 'Escape' && drawerOpen.value) closeDrawer()
    }

    // Close on navigation without stealing focus from the new page
    watch(() => route.path, () => { drawerOpen.value = false })

    onMounted(() => window.addEventListener('keydown', onKeydown))
    onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))

    // Merge mock tasks from currentUser with API tasks
    const tasks = computed(() => {
      return [...currentUser.value.tasks, ...apiTasks.value]
    })

    const loadTasks = async () => {
      try {
        apiTasks.value = await api.getTasks()
      } catch (err) {
        console.error('Failed to load tasks:', err)
      }
    }

    const addTask = async (taskData) => {
      try {
        const newTask = await api.createTask(taskData)
        // Add new task to the beginning of the array
        apiTasks.value.unshift(newTask)
      } catch (err) {
        console.error('Failed to add task:', err)
      }
    }

    const deleteTask = async (taskId) => {
      try {
        // Check if it's a mock task (from currentUser)
        const isMockTask = currentUser.value.tasks.some(t => t.id === taskId)

        if (isMockTask) {
          // Remove from mock tasks
          const index = currentUser.value.tasks.findIndex(t => t.id === taskId)
          if (index !== -1) {
            currentUser.value.tasks.splice(index, 1)
          }
        } else {
          // Remove from API tasks
          await api.deleteTask(taskId)
          apiTasks.value = apiTasks.value.filter(t => t.id !== taskId)
        }
      } catch (err) {
        console.error('Failed to delete task:', err)
      }
    }

    const toggleTask = async (taskId) => {
      try {
        // Check if it's a mock task (from currentUser)
        const mockTask = currentUser.value.tasks.find(t => t.id === taskId)

        if (mockTask) {
          // Toggle mock task status
          mockTask.status = mockTask.status === 'pending' ? 'completed' : 'pending'
        } else {
          // Toggle API task
          const updatedTask = await api.toggleTask(taskId)
          const index = apiTasks.value.findIndex(t => t.id === taskId)
          if (index !== -1) {
            apiTasks.value[index] = updatedTask
          }
        }
      } catch (err) {
        console.error('Failed to toggle task:', err)
      }
    }

    onMounted(loadTasks)

    return {
      t,
      navItems,
      theme,
      toggleTheme,
      drawerOpen,
      menuButton,
      sidebar,
      openDrawer,
      closeDrawer,
      showProfileDetails,
      showTasks,
      tasks,
      addTask,
      deleteTask,
      toggleTask
    }
  }
}
</script>

<style>
/* ===== Design tokens (roles, not colors) - Horváth AI brand =====
   Petrol scale: 50 #eef6f9 / 100 #d5e8ef / 200 #aacfdd / 300 #6fa9bf / 400 #3a7f9a / 500 #17607c / 600 #0a4d68 / 700 #05415a (brand) / 800 #043447 / 900 #03283a / 950 #021b27
   Cyan #14e6d7 is a HIGHLIGHT only (nav indicator, focus ring, charts, progress, glow): never text or thin icons on light surfaces. */
:root {
  /* surfaces */
  --bg: #f2f6f8; --surface: #ffffff; --surface-2: #e9f0f3; --border: #d9e4ea; --border-strong: #b9cbd4;
  /* text (muted/faint checked >= 4.5:1 on surface, surface-2 and bg) */
  --text: #0a1f2b; --text-muted: #46606f; --text-faint: #5b7381;
  /* brand */
  --accent: #05415a; --accent-hover: #0a5473; --accent-contrast: #ffffff;
  --accent-soft: color-mix(in srgb, var(--accent) 10%, transparent);
  --highlight: #14e6d7;
  --glow: 0 0 0 3px color-mix(in srgb, var(--highlight) 35%, transparent);
  /* status (AA text on surface; badges mix toward --text) */
  --success: #047857; --warning: #b45309; --danger: #c0262d; --info: #0369a1;
  /* charts: an ordered categorical palette, used in this order */
  --chart-1: #05415a; --chart-2: #14e6d7; --chart-3: #f2b134; --chart-4: #e5645a; --chart-5: #7c6bd6; --chart-6: #2f7ea3;
  /* sidebar (petrol in both themes; text on it is white-ish) */
  --sidebar-bg: #05415a; --sidebar-bg-grad: linear-gradient(180deg, #06475f 0%, #05415a 45%, #032e41 100%);
  --sidebar-text: #bdd6e0; --sidebar-active: #ffffff; --sidebar-w: 248px;
  --logo-petrol: #05415a;
  /* shape and space */
  --radius-sm: 6px; --radius: 10px; --radius-lg: 14px;
  --shadow-sm: 0 1px 2px rgb(5 65 90 / .06); --shadow: 0 6px 20px -6px rgb(5 65 90 / .16);
  --space-1: 4px; --space-2: 8px; --space-3: 12px; --space-4: 16px; --space-5: 24px; --space-6: 32px;
  --font-sans: "Inter", system-ui, -apple-system, "Segoe UI", sans-serif;
  --font-mono: "JetBrains Mono", ui-monospace, Consolas, monospace;
  /* additions beyond the skill sheet: modal scrim + elevated shadow, mobile top bar height */
  --overlay: rgb(3 24 34 / .55); --shadow-lg: 0 20px 50px -12px rgb(3 40 58 / .3);
  --topbar-h: 56px;
}
[data-theme="dark"] {
  --bg: #04131b; --surface: #082230; --surface-2: #0c2c3d; --border: #14394d; --border-strong: #215168;
  --text: #e6f1f5; --text-muted: #9fbac8; --text-faint: #86a3b2;
  --accent: #14e6d7; --accent-hover: #5ff0e5; --accent-contrast: #03283a;
  --success: #34d399; --warning: #fbbf24; --danger: #f87171; --info: #38bdf8;
  --chart-1: #6aa8c4; --chart-2: #14e6d7; --chart-3: #f2b134; --chart-4: #f0786e; --chart-5: #9a8cf0; --chart-6: #4aa0c4;
  --sidebar-bg: #03202d; --sidebar-bg-grad: linear-gradient(180deg, #04293a 0%, #03202d 50%, #021821 100%);
  --shadow-sm: none; --shadow: 0 0 0 1px var(--border);
  --overlay: rgb(0 0 0 / .65); --shadow-lg: 0 0 0 1px var(--border-strong), 0 20px 50px -12px rgb(0 0 0 / .6);
}
@media (min-width: 1024px) {
  :root { --topbar-h: 0px; }
}

/* ===== Base ===== */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html {
  color-scheme: light;
}
html[data-theme="dark"] {
  color-scheme: dark;
}

body {
  font-family: var(--font-sans);
  background: var(--bg);
  background-image: radial-gradient(900px 340px at 100% -10%, color-mix(in srgb, var(--highlight) 9%, transparent), transparent 70%);
  background-attachment: fixed;
  color: var(--text);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

:focus-visible {
  /* accent outline keeps 3:1 on any surface; the cyan halo adds the brand glow */
  outline: 2px solid var(--accent);
  outline-offset: 2px;
  box-shadow: var(--glow);
}
/* on the petrol sidebar the cyan itself is the contrasting ring */
.sidebar :focus-visible, .topbar :focus-visible {
  outline-color: var(--highlight);
  box-shadow: none;
}

input[type="range"] {
  accent-color: var(--accent);
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    transition-duration: 0.01ms !important;
    animation-duration: 0.01ms !important;
  }
}

/* ===== Shell (mobile first) ===== */
.app {
  display: block;
  min-height: 100dvh;
}

.topbar {
  position: sticky;
  top: 0;
  z-index: 40;
  height: var(--topbar-h);
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: 0 var(--space-4);
  background: var(--sidebar-bg-grad);
  color: var(--sidebar-active);
  --logo-petrol: #ffffff;
  border-bottom: 1px solid color-mix(in srgb, var(--highlight) 30%, transparent);
}

.topbar-logo {
  width: 112px;
}

.icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  background: transparent;
  border: 0;
  border-radius: var(--radius);
  color: inherit;
  cursor: pointer;
  transition: background-color 0.15s ease;
}
.icon-btn:hover {
  background: color-mix(in srgb, var(--sidebar-active) 10%, transparent);
}

.icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.75;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.overlay {
  position: fixed;
  inset: 0;
  z-index: 50;
  background: var(--overlay);
  opacity: 0;
  visibility: hidden;
  transition: opacity 0.2s ease, visibility 0s linear 0.2s;
}
.overlay.visible {
  opacity: 1;
  visibility: visible;
  transition-delay: 0s;
}

.sidebar {
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  z-index: 60;
  width: min(var(--sidebar-w), 85vw);
  display: flex;
  flex-direction: column;
  background: var(--sidebar-bg-grad);
  color: var(--sidebar-text);
  /* the logo's petrol parts would vanish on the petrol sidebar: render them white here */
  --logo-petrol: #ffffff;
  box-shadow: 1px 0 0 color-mix(in srgb, var(--highlight) 14%, transparent);
  transform: translateX(-100%);
  /* visibility keeps the closed drawer out of the tab order; delayed so the slide-out is still visible */
  visibility: hidden;
  transition: transform 0.2s ease, visibility 0s linear 0.2s;
}
.sidebar.open {
  transform: none;
  visibility: visible;
  transition-delay: 0s;
}
.sidebar:focus {
  outline: none;
}

.sidebar-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  padding: var(--space-5) var(--space-4) var(--space-4);
}

.logo {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  min-width: 0;
}
.logo-mark {
  width: 148px;
  max-width: 100%;
}
.logo-sub {
  font-size: 0.75rem;
  color: var(--sidebar-text);
  margin-top: var(--space-2);
}

.sidebar-nav {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  padding: var(--space-2) var(--space-3);
}

.nav-link {
  position: relative;
  display: flex;
  align-items: center;
  gap: var(--space-3);
  min-height: 40px;
  padding: 0 var(--space-3);
  border-radius: var(--radius);
  color: var(--sidebar-text);
  text-decoration: none;
  font-size: 0.875rem;
  font-weight: 500;
  transition: background-color 0.15s ease, color 0.15s ease;
}
.nav-link:hover {
  color: var(--sidebar-active);
  background: color-mix(in srgb, var(--sidebar-active) 6%, transparent);
}
.nav-link.active {
  color: var(--sidebar-active);
  background: linear-gradient(90deg, color-mix(in srgb, var(--highlight) 18%, transparent), color-mix(in srgb, var(--sidebar-active) 6%, transparent));
}
.nav-link.active .icon {
  color: var(--highlight);
}
/* accent bar on the left edge of the active item */
.nav-link.active::before {
  content: '';
  position: absolute;
  left: calc(var(--space-3) * -1);
  top: var(--space-2);
  bottom: var(--space-2);
  width: 3px;
  border-radius: 0 3px 3px 0;
  background: var(--highlight);
  box-shadow: 0 0 10px color-mix(in srgb, var(--highlight) 70%, transparent);
}
.nav-link:focus-visible,
.sidebar .icon-btn:focus-visible {
  outline-offset: -2px;
}

/* Footer is deliberately overflow:visible so the upward dropdowns are not clipped */
.sidebar-footer {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-3) var(--space-4);
  border-top: 1px solid color-mix(in srgb, var(--sidebar-active) 10%, transparent);
}
.footer-row {
  display: flex;
  gap: var(--space-2);
}
.footer-row > .language-switcher {
  flex: 1;
  min-width: 0;
}

.theme-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  flex-shrink: 0;
  background: color-mix(in srgb, var(--sidebar-active) 8%, transparent);
  border: 1px solid color-mix(in srgb, var(--sidebar-active) 12%, transparent);
  border-radius: var(--radius);
  color: var(--sidebar-active);
  cursor: pointer;
  transition: background-color 0.15s ease;
}
.theme-toggle .icon {
  color: var(--highlight);
}
.theme-toggle:hover {
  background: color-mix(in srgb, var(--sidebar-active) 14%, transparent);
  box-shadow: var(--glow);
}

@keyframes page-in {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: none; }
}
.main-content > * {
  animation: page-in 0.28s ease both;
}

.content {
  min-width: 0; /* lets wide children (tables) scroll inside instead of stretching the grid column */
}

.main-content {
  width: 100%;
  max-width: 1440px;
  margin: 0 auto;
  padding: var(--space-4);
}

.close-drawer {
  flex-shrink: 0;
}

@media (min-width: 640px) {
  .main-content {
    padding: var(--space-6);
  }
}

/* ===== Desktop: persistent sidebar ===== */
@media (min-width: 1024px) {
  .app {
    display: grid;
    grid-template-columns: var(--sidebar-w) minmax(0, 1fr);
  }
  .topbar,
  .overlay,
  .close-drawer {
    display: none;
  }
  .sidebar {
    position: sticky;
    bottom: auto;
    height: 100dvh;
    width: auto;
    z-index: 30;
    transform: none;
    visibility: visible;
  }
}

/* ===== Shared page classes (views depend on these names) ===== */
.page-header {
  margin-bottom: var(--space-5);
}

.page-header h2 {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text);
  margin-bottom: var(--space-1);
  letter-spacing: -0.02em;
}

.page-header p {
  color: var(--text-muted);
  font-size: 0.875rem;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 240px), 1fr));
  gap: var(--space-4);
  margin-bottom: var(--space-5);
}

.stat-card {
  position: relative;
  overflow: hidden;
  background: var(--surface);
  padding: var(--space-5);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border);
  box-shadow: var(--shadow-sm);
  transition: border-color 0.15s ease, box-shadow 0.15s ease, transform 0.15s ease;
}

/* thin petrol-to-cyan accent along the top edge of every KPI tile */
.stat-card::before {
  content: '';
  position: absolute;
  inset: 0 0 auto 0;
  height: 3px;
  background: linear-gradient(90deg, var(--chart-1), var(--highlight));
}

.stat-card:hover {
  border-color: var(--border-strong);
  box-shadow: var(--shadow);
  transform: translateY(-1px);
}

.stat-label {
  color: var(--text-muted);
  font-size: 0.75rem;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: var(--space-2);
}

.stat-value {
  font-size: 1.75rem;
  font-weight: 600;
  color: var(--text);
  letter-spacing: -0.02em;
  font-variant-numeric: tabular-nums;
  overflow-wrap: anywhere;
}

.stat-card.warning .stat-value { color: var(--warning); }
.stat-card.success .stat-value { color: var(--success); }
.stat-card.danger .stat-value { color: var(--danger); }
.stat-card.info .stat-value { color: var(--info); }

.card {
  background: var(--surface);
  border-radius: var(--radius-lg);
  padding: var(--space-5);
  border: 1px solid var(--border);
  box-shadow: var(--shadow-sm);
  margin-bottom: var(--space-5);
}

.card-header {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-4);
  padding-bottom: var(--space-3);
  border-bottom: 1px solid var(--border);
}

.card-title {
  font-size: 1rem;
  font-weight: 600;
  color: var(--text);
  letter-spacing: -0.01em;
}

.table-container {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
}

thead {
  background: var(--surface-2);
  border-bottom: 2px solid color-mix(in srgb, var(--accent) 35%, var(--border));
}

th {
  position: sticky;
  top: 0;
  background: var(--surface-2);
  text-align: left;
  padding: var(--space-3) var(--space-4);
  font-weight: 600;
  color: var(--text);
  font-size: 0.6875rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  white-space: nowrap;
}

td {
  height: 44px;
  padding: var(--space-2) var(--space-4);
  border-top: 1px solid var(--border);
  color: var(--text);
  font-size: 0.875rem;
  font-variant-numeric: tabular-nums;
}

/* Opt-in helpers for views: right-align numbers, mono for SKUs / order ids */
th.num, td.num {
  text-align: right;
}
.mono {
  font-family: var(--font-mono);
  font-weight: 500;
  font-variant-numeric: tabular-nums;
}

tbody tr {
  transition: background-color 0.15s ease;
}

tbody tr:hover {
  background: var(--surface-2);
}

/* Badge: pill, tinted bg from --c, text = --c darkened toward body text for contrast */
.badge {
  --c: var(--text-muted);
  display: inline-block;
  padding: var(--space-1) var(--space-3);
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 500;
  white-space: nowrap;
  background: color-mix(in srgb, var(--c) 14%, transparent);
  color: color-mix(in srgb, var(--c) 80%, var(--text));
}
.badge.success, .badge.increasing { --c: var(--success); }
.badge.warning, .badge.medium { --c: var(--warning); }
.badge.danger, .badge.decreasing, .badge.high { --c: var(--danger); }
.badge.info, .badge.low { --c: var(--info); }
.badge.stable { --c: var(--accent); }

/* Buttons */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  min-height: 40px;
  padding: 0 var(--space-4);
  border-radius: var(--radius);
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text);
  font-family: inherit;
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: background-color 0.15s ease, border-color 0.15s ease;
}
.btn:hover:not(:disabled) {
  background: var(--surface-2);
  border-color: var(--border-strong);
}
.btn-primary {
  background: var(--accent);
  border-color: var(--accent);
  color: var(--accent-contrast);
}
.btn-primary:hover:not(:disabled) {
  box-shadow: var(--glow);
  background: var(--accent-hover);
  border-color: var(--accent-hover);
}
.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
@media (min-width: 1024px) {
  .btn { min-height: 36px; }
}

.loading {
  text-align: center;
  padding: var(--space-6);
  color: var(--text-muted);
  font-size: 0.875rem;
}

.error {
  background: color-mix(in srgb, var(--danger) 10%, transparent);
  border: 1px solid color-mix(in srgb, var(--danger) 30%, transparent);
  color: var(--danger);
  padding: var(--space-4);
  border-radius: var(--radius);
  margin: var(--space-4) 0;
  font-size: 0.875rem;
}
</style>

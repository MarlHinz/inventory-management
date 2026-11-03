<template>
  <div class="filters-bar">
    <div class="filters-container">
      <div class="filters-grid">
        <div class="filter-group">
          <label>{{ t('filters.timePeriod') }}</label>
          <select v-model="selectedPeriod" class="filter-select">
            <option value="all">{{ t('filters.allMonths') }}</option>
            <option value="2025-01">{{ t('months.january') }}</option>
            <option value="2025-02">{{ t('months.february') }}</option>
            <option value="2025-03">{{ t('months.march') }}</option>
            <option value="2025-04">{{ t('months.april') }}</option>
            <option value="2025-05">{{ t('months.may') }}</option>
            <option value="2025-06">{{ t('months.june') }}</option>
            <option value="2025-07">{{ t('months.july') }}</option>
            <option value="2025-08">{{ t('months.august') }}</option>
            <option value="2025-09">{{ t('months.september') }}</option>
            <option value="2025-10">{{ t('months.october') }}</option>
            <option value="2025-11">{{ t('months.november') }}</option>
            <option value="2025-12">{{ t('months.december') }}</option>
          </select>
        </div>

        <div class="filter-group">
          <label>{{ t('filters.location') }}</label>
          <select v-model="selectedLocation" class="filter-select">
            <option value="all">{{ t('filters.all') }}</option>
            <option value="San Francisco">{{ t('warehouses.sanFrancisco') }}</option>
            <option value="London">{{ t('warehouses.london') }}</option>
            <option value="Tokyo">{{ t('warehouses.tokyo') }}</option>
          </select>
        </div>

        <div class="filter-group">
          <label>{{ t('filters.category') }}</label>
          <select v-model="selectedCategory" class="filter-select">
            <option value="all">{{ t('filters.all') }}</option>
            <option value="circuit boards">{{ t('categories.circuitBoards') }}</option>
            <option value="sensors">{{ t('categories.sensors') }}</option>
            <option value="actuators">{{ t('categories.actuators') }}</option>
            <option value="controllers">{{ t('categories.controllers') }}</option>
            <option value="power supplies">{{ t('categories.powerSupplies') }}</option>
          </select>
        </div>

        <div class="filter-group">
          <label>{{ t('filters.orderStatus') }}</label>
          <select v-model="selectedStatus" class="filter-select">
            <option value="all">{{ t('filters.all') }}</option>
            <option value="delivered">{{ t('status.delivered') }}</option>
            <option value="shipped">{{ t('status.shipped') }}</option>
            <option value="processing">{{ t('status.processing') }}</option>
            <option value="backordered">{{ t('status.backordered') }}</option>
          </select>
        </div>
      </div>

      <button
        class="reset-filters-btn"
        @click="resetFilters"
        :disabled="!hasActiveFilters"
        title="Reset all filters"
      >
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clip-rule="evenodd" />
        </svg>
      </button>
    </div>
  </div>
</template>

<script>
import { useFilters } from '../composables/useFilters'
import { useI18n } from '../composables/useI18n'

export default {
  name: 'FilterBar',
  setup() {
    const {
      selectedPeriod,
      selectedLocation,
      selectedCategory,
      selectedStatus,
      hasActiveFilters,
      resetFilters
    } = useFilters()

    const { t } = useI18n()

    return {
      t,
      selectedPeriod,
      selectedLocation,
      selectedCategory,
      selectedStatus,
      hasActiveFilters,
      resetFilters
    }
  }
}
</script>

<style scoped>
/* Sticky at the top of the content column. --topbar-h is 56px under 1024px (mobile top bar) and 0 above. */
.filters-bar {
  background: var(--bg);
  border-bottom: 1px solid var(--border);
  padding: var(--space-3) var(--space-4);
  position: sticky;
  top: var(--topbar-h);
  z-index: 20;
}

.filters-container {
  max-width: 1440px;
  margin: 0 auto;
  display: flex;
  align-items: flex-end;
  gap: var(--space-3);
}

/* Phones: 2-column grid of full-width controls */
.filters-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-3);
  flex: 1;
  min-width: 0;
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  min-width: 0;
}

.filter-group label {
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--text-muted);
  white-space: nowrap;
}

.filter-select {
  width: 100%;
  min-height: 40px;
  padding: 0 var(--space-3);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  font-family: inherit;
  font-size: 0.8125rem;
  color: var(--text);
  background: var(--surface);
  cursor: pointer;
  transition: border-color 0.15s ease;
  font-weight: 500;
}

.filter-select:hover {
  border-color: var(--border-strong);
}

.filter-select:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
  border-color: var(--accent);
}

.reset-filters-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  color: var(--text-muted);
  cursor: pointer;
  transition: background-color 0.15s ease, color 0.15s ease;
  flex-shrink: 0;
}

.reset-filters-btn:hover:not(:disabled) {
  background: var(--surface-2);
  color: var(--text);
}

.reset-filters-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.reset-filters-btn svg {
  width: 18px;
  height: 18px;
}

@media (min-width: 640px) {
  .filters-bar {
    padding: var(--space-3) var(--space-6);
  }
  .filters-grid {
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  }
}

@media (min-width: 1024px) {
  .filter-select,
  .reset-filters-btn {
    min-height: 36px;
    height: 36px;
  }
  .reset-filters-btn {
    width: 36px;
  }
}
</style>

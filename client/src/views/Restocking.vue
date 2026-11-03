<template>
  <div class="restocking">
    <div class="page-header">
      <h2>{{ t('restocking.title') }}</h2>
      <p>{{ t('restocking.description') }}</p>
    </div>

    <div class="card budget-card">
      <div class="budget-row">
        <label for="budget-slider" class="budget-label">{{ t('restocking.budgetSlider') }}</label>
        <!-- @input only updates the displayed value; the API is hit on @change (release),
             otherwise every pixel of a drag would fire a request. -->
        <input
          id="budget-slider"
          type="range"
          min="0"
          step="250"
          :max="sliderMax"
          :value="budget"
          @input="budget = Number($event.target.value)"
          @change="loadRecommendations"
        />
        <label for="budget-number" class="budget-label">{{ t('restocking.budgetInput') }} ({{ currencySymbol }})</label>
        <input
          id="budget-number"
          class="budget-number"
          type="number"
          min="0"
          step="250"
          :max="sliderMax"
          :value="budget"
          @change="onNumberCommit"
        />
      </div>
      <!-- Selected total as a share of budget; capped at 100% visually, turns red when over -->
      <div v-if="data" class="usage" :class="{ over: overBudget }" role="img"
           :aria-label="`${money(selectedTotal)} / ${money(budget)}`">
        <div class="usage-fill" :style="{ width: usagePct + '%' }"></div>
      </div>
    </div>

    <div v-if="error" class="error">{{ error }}</div>
    <div v-if="loading && !data" class="loading">{{ t('common.loading') }}</div>

    <div v-if="data">
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-label">{{ t('restocking.budget') }}</div>
          <div class="stat-value">{{ money(budget) }}</div>
        </div>
        <div class="stat-card" :class="overBudget ? 'danger' : 'info'">
          <div class="stat-label">{{ t('restocking.selectedTotal') }}</div>
          <div class="stat-value">{{ money(selectedTotal) }}</div>
        </div>
        <div class="stat-card" :class="overBudget ? 'danger' : 'success'">
          <div class="stat-label">{{ t('restocking.remaining') }}</div>
          <div class="stat-value">{{ money(budget - selectedTotal) }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">{{ t('restocking.itemCount') }}</div>
          <div class="stat-value">{{ selectedItems.length }} / {{ data.items.length }}</div>
        </div>
      </div>

      <div v-if="placedOrder" class="confirmation" role="status">
        {{ t('restocking.orderPlaced', { orderNumber: placedOrder.order_number, date: formatDate(placedOrder.expected_delivery) }) }}
        <router-link to="/orders">{{ t('restocking.viewOrders') }}</router-link>
      </div>
      <div v-if="placeError" class="error" role="alert">{{ placeError }}</div>

      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('restocking.recommendations') }}</h3>
          <div class="place-order">
            <span v-if="overBudget" class="over-budget">{{ t('restocking.overBudget') }}</span>
            <button type="button" class="btn btn-primary" :disabled="!canPlace" @click="placeOrder">
              {{ submitting ? t('restocking.placing') : t('restocking.placeOrder') }}
            </button>
          </div>
        </div>
        <div v-if="data.items.length === 0" class="empty">{{ t('restocking.noRecommendations') }}</div>
        <div v-else class="table-container">
          <table>
            <thead>
              <tr>
                <th>{{ t('restocking.table.select') }}</th>
                <th>{{ t('restocking.table.sku') }}</th>
                <th>{{ t('restocking.table.item') }}</th>
                <th>{{ t('restocking.table.trend') }}</th>
                <th class="num">{{ t('restocking.table.gap') }}</th>
                <th class="num">{{ t('restocking.table.quantity') }}</th>
                <th class="num">{{ t('restocking.table.unitCost') }}</th>
                <th class="num">{{ t('restocking.table.lineTotal') }}</th>
                <th class="num">{{ t('restocking.table.leadTime') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in data.items" :key="item.sku">
                <td>
                  <input
                    type="checkbox"
                    :aria-label="`${t('restocking.table.select')} ${item.sku}`"
                    :checked="!deselected.has(item.sku)"
                    @change="toggle(item.sku)"
                  />
                </td>
                <td class="mono">{{ item.sku }}</td>
                <td>{{ translateProductName(item.name) }}</td>
                <td>
                  <span :class="['badge', item.trend]">{{ t(`trends.${item.trend}`) }}</span>
                </td>
                <td class="num">{{ num(item.gap) }}</td>
                <td class="num">{{ num(item.quantity) }}</td>
                <td class="num">{{ money(item.unit_cost) }}</td>
                <td class="num"><strong>{{ money(item.total_cost) }}</strong></td>
                <td class="num">{{ item.lead_time_days }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { api } from '../api'
import { useI18n } from '../composables/useI18n'
import { formatCurrencyWithDecimals } from '../utils/currency'

const DEFAULT_BUDGET = 5000

export default {
  name: 'Restocking',
  setup() {
    const { t, currentLocale, currentCurrency, translateProductName } = useI18n()

    // Server budget and costs are USD. The budget input/slider stays in USD (sent to the API as-is),
    // so its label keeps '$'; displayed amounts go through the shared util (JPY conversion + app locale).
    const currencySymbol = '$'
    const money = (v) => formatCurrencyWithDecimals(Number(v), currentCurrency.value, 2)
    // Plain counts use the app locale, not the browser default
    const num = (v) => Number(v).toLocaleString(currentLocale.value === 'ja' ? 'ja-JP' : 'en-US')
    const formatDate = (s) => {
      const d = new Date(s)
      if (isNaN(d.getTime())) return s
      return d.toLocaleDateString(currentLocale.value === 'ja' ? 'ja-JP' : 'en-US', {
        year: 'numeric', month: 'short', day: 'numeric'
      })
    }

    const budget = ref(DEFAULT_BUDGET)
    // Budget the current `data` was loaded for; differs from `budget` while the slider is mid-drag.
    const loadedBudget = ref(null)
    const data = ref(null)
    const loading = ref(false)
    const error = ref(null)
    const submitting = ref(false)
    const placeError = ref(null)
    const placedOrder = ref(null)
    // Lines the user unchecked; everything else is selected by default.
    const deselected = ref(new Set())
    const sliderMax = ref(10000)

    // Guards against an older, slower response overwriting a newer one.
    let requestId = 0

    const loadRecommendations = async () => {
      const id = ++requestId
      loading.value = true
      error.value = null
      const requested = budget.value
      try {
        const res = await api.getRestockRecommendations(requested)
        if (id !== requestId) return
        data.value = res
        loadedBudget.value = requested
        // Keep the user's deselections for SKUs that are still recommended.
        const skus = new Set(res.items.map(i => i.sku))
        deselected.value = new Set([...deselected.value].filter(sku => skus.has(sku)))
        // Placed orders shrink the remaining gap, so full coverage can drop below the current budget.
        // Never shrink the max under the budget, or the thumb would misrepresent the value.
        sliderMax.value = Math.max(500, budget.value, Math.ceil(res.full_coverage_cost / 500) * 500)
      } catch (err) {
        if (id !== requestId) return
        error.value = t('restocking.loadFailed') + ': ' + err.message
      } finally {
        if (id === requestId) loading.value = false
      }
    }

    const onNumberCommit = (e) => {
      const v = Number(e.target.value)
      // Server rejects negative budgets (422); clamp to [0, sliderMax] and ignore blanks.
      if (e.target.value === '' || isNaN(v)) {
        e.target.value = budget.value
        return
      }
      budget.value = Math.min(sliderMax.value, Math.max(0, v))
      // Vue won't re-render if budget is unchanged, so a typed out-of-range value would linger; write it back.
      e.target.value = budget.value
      loadRecommendations()
    }

    const toggle = (sku) => {
      const next = new Set(deselected.value)
      if (next.has(sku)) next.delete(sku)
      else next.add(sku)
      deselected.value = next
    }

    const selectedItems = computed(() =>
      data.value ? data.value.items.filter(i => !deselected.value.has(i.sku)) : []
    )
    const selectedTotal = computed(() =>
      selectedItems.value.reduce((sum, i) => sum + i.total_cost, 0)
    )
    // Small epsilon so float rounding on cent values can't block a valid order.
    const overBudget = computed(() => selectedTotal.value > budget.value + 0.005)
    const usagePct = computed(() =>
      budget.value > 0 ? Math.min(100, (selectedTotal.value / budget.value) * 100) : (selectedTotal.value > 0 ? 100 : 0)
    )
    const canPlace = computed(
      () => selectedItems.value.length > 0 && !submitting.value && !overBudget.value &&
        // Block while the list is stale (slider moved, not yet reloaded) or a reload is in flight.
        !loading.value && budget.value === loadedBudget.value
    )

    const placeOrder = async () => {
      if (!canPlace.value) return
      submitting.value = true
      placeError.value = null
      placedOrder.value = null
      try {
        placedOrder.value = await api.placeRestockOrder({
          budget: budget.value,
          items: selectedItems.value.map(i => ({ sku: i.sku, quantity: i.quantity }))
        })
      } catch (err) {
        const detail = err.response?.data?.detail
        // 400: string; 422: array of { msg }.
        placeError.value = typeof detail === 'string'
          ? detail
          : Array.isArray(detail) && detail.length
            ? detail.map(d => d.msg).join('; ')
            : t('restocking.placeFailed')
        return
      } finally {
        submitting.value = false
      }
      // Refresh outside the POST try: a reload failure must not look like a failed order (risks a duplicate).
      // loadRecommendations already catches and surfaces its own error via `error`.
      await loadRecommendations()
    }

    onMounted(loadRecommendations)

    return {
      t, currencySymbol, money, num, formatDate, translateProductName,
      budget, data, loading, error, submitting, placeError, placedOrder,
      deselected, sliderMax, usagePct, selectedItems, selectedTotal, overBudget, canPlace,
      loadRecommendations, onNumberCommit, toggle, placeOrder
    }
  }
}
</script>

<style scoped>
.budget-card {
  padding: var(--space-4) var(--space-5);
}

/* Mobile first: label / slider / label / number stack, then flow in one row from 640px */
.budget-row {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--space-2) var(--space-4);
  align-items: center;
}

@media (min-width: 640px) {
  .budget-row {
    grid-template-columns: auto minmax(120px, 1fr) auto auto;
  }
}

.budget-label {
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

/* Custom range track and thumb, themed through tokens */
.budget-row input[type='range'] {
  width: 100%;
  min-width: 0;
  height: 40px;
  background: transparent;
  accent-color: var(--accent);
  cursor: pointer;
}
.budget-row input[type='range']::-webkit-slider-runnable-track {
  height: 6px;
  border-radius: 999px;
  background: var(--border-strong);
}
.budget-row input[type='range']::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 20px;
  height: 20px;
  margin-top: -7px;
  border-radius: 50%;
  background: var(--accent);
  border: 3px solid var(--surface);
  box-shadow: 0 0 0 1px var(--accent), var(--shadow-sm);
  transition: transform 0.15s ease;
}
.budget-row input[type='range']:hover::-webkit-slider-thumb {
  transform: scale(1.1);
}
.budget-row input[type='range']::-moz-range-track {
  height: 6px;
  border-radius: 999px;
  background: var(--border-strong);
}
.budget-row input[type='range']::-moz-range-thumb {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: var(--accent);
  border: 3px solid var(--surface);
  box-shadow: 0 0 0 1px var(--accent);
}

.budget-number {
  width: 100%;
  min-height: 40px;
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface);
  color: var(--text);
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  font-size: 0.875rem;
  transition: border-color 0.15s ease;
}
.budget-number:focus {
  border-color: var(--accent);
}
@media (min-width: 640px) {
  .budget-number {
    width: 140px;
  }
}

.usage {
  height: 6px;
  margin-top: var(--space-3);
  border-radius: 999px;
  background: var(--surface-2);
  overflow: hidden;
}
.usage-fill {
  height: 100%;
  background: var(--success);
  transition: width 0.2s ease;
}
.usage.over .usage-fill {
  background: var(--danger);
}

.place-order {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-3);
}

.over-budget {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--danger);
}

/* Success message, same tint recipe as the global .error */
.confirmation {
  background: color-mix(in srgb, var(--success) 10%, transparent);
  border: 1px solid color-mix(in srgb, var(--success) 30%, transparent);
  color: var(--success);
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius);
  margin-bottom: var(--space-5);
  font-size: 0.875rem;
}

.confirmation a {
  margin-left: var(--space-3);
  font-weight: 600;
  color: var(--accent);
}

.empty {
  padding: var(--space-6);
  text-align: center;
  color: var(--text-muted);
}

tbody input[type='checkbox'] {
  width: 18px;
  height: 18px;
  accent-color: var(--accent);
  cursor: pointer;
}
</style>

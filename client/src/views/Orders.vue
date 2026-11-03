<template>
  <div class="orders">
    <div class="page-header">
      <h2>{{ t('orders.title') }}</h2>
      <p>{{ t('orders.description') }}</p>
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else>
      <div class="stats-grid">
        <div class="stat-card success">
          <div class="stat-label">{{ t('status.delivered') }}</div>
          <div class="stat-value">{{ getOrdersByStatus('Delivered').length }}</div>
        </div>
        <div class="stat-card info">
          <div class="stat-label">{{ t('status.shipped') }}</div>
          <div class="stat-value">{{ getOrdersByStatus('Shipped').length }}</div>
        </div>
        <div class="stat-card warning">
          <div class="stat-label">{{ t('status.processing') }}</div>
          <div class="stat-value">{{ getOrdersByStatus('Processing').length }}</div>
        </div>
        <div class="stat-card danger">
          <div class="stat-label">{{ t('status.backordered') }}</div>
          <div class="stat-value">{{ getOrdersByStatus('Backordered').length }}</div>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('orders.allOrders') }} ({{ orders.length }})</h3>
        </div>
        <div class="table-container">
          <table class="orders-table">
            <thead>
              <tr>
                <th class="col-order-number">{{ t('orders.table.orderNumber') }}</th>
                <th class="col-customer">{{ t('orders.table.customer') }}</th>
                <th class="col-items">{{ t('orders.table.items') }}</th>
                <th class="col-status">{{ t('orders.table.status') }}</th>
                <th class="col-date">{{ t('orders.table.orderDate') }}</th>
                <th class="col-date">{{ t('orders.table.expectedDelivery') }}</th>
                <th class="col-value num">{{ t('orders.table.totalValue') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="order in orders" :key="order.id">
                <td class="col-order-number mono">{{ order.order_number }}</td>
                <td class="col-customer">{{ translateCustomerName(order.customer) }}</td>
                <td class="col-items">
                  <details class="items-details">
                    <summary class="items-summary">
                      {{ t('orders.itemsCount', { count: order.items.length }) }}
                    </summary>
                    <div class="items-dropdown">
                      <div v-for="(item, idx) in order.items" :key="idx" class="item-entry">
                        <span class="item-name">{{ translateProductName(item.name) }}</span>
                        <span class="item-meta">{{ t('orders.quantity') }}: {{ item.quantity }} @ {{ money(item.unit_price) }}</span>
                      </div>
                    </div>
                  </details>
                </td>
                <td class="col-status">
                  <span :class="['badge', getOrderStatusClass(order.status)]">
                    {{ t(`status.${order.status.toLowerCase()}`) }}
                  </span>
                </td>
                <td class="col-date">{{ formatDate(order.order_date) }}</td>
                <td class="col-date">{{ formatDate(order.expected_delivery) }}</td>
                <td class="col-value num"><strong>{{ money(order.total_value) }}</strong></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Restocking orders: independent of the global filters and the main loading state -->
    <div class="card submitted-card">
      <div class="card-header">
        <div>
          <h3 class="card-title">{{ t('orders.submittedOrders') }} ({{ submittedOrders.length }})</h3>
          <p class="card-hint">{{ t('orders.submittedOrdersHint') }}</p>
        </div>
      </div>
      <div v-if="submittedError" class="error">{{ submittedError }}</div>
      <div v-else-if="submittedOrders.length === 0" class="empty-state">{{ t('orders.noSubmittedOrders') }}</div>
      <div v-else class="table-container">
        <table class="orders-table">
          <thead>
            <tr>
              <th class="col-order-number">{{ t('orders.table.orderNumber') }}</th>
              <th class="col-items">{{ t('orders.table.items') }}</th>
              <th class="col-value num">{{ t('orders.table.totalValue') }}</th>
              <th class="col-date">{{ t('orders.table.orderDate') }}</th>
              <th class="col-date num">{{ t('orders.table.leadTime') }}</th>
              <th class="col-date">{{ t('orders.table.expectedDelivery') }}</th>
              <th class="col-status">{{ t('orders.table.status') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="order in submittedOrders" :key="order.id">
              <td class="col-order-number mono">{{ order.order_number }}</td>
              <td class="col-items">
                <details class="items-details">
                  <summary class="items-summary">
                    {{ t('orders.itemsCount', { count: order.items.length }) }}
                  </summary>
                  <div class="items-dropdown">
                    <div v-for="item in order.items" :key="item.sku" class="item-entry">
                      <span class="item-name">{{ translateProductName(item.name) }}</span>
                      <span class="item-meta">{{ t('orders.quantity') }}: {{ item.quantity }} @ {{ money(item.unit_cost) }}</span>
                    </div>
                  </div>
                </details>
              </td>
              <td class="col-value num"><strong>{{ money(order.total_value) }}</strong></td>
              <td class="col-date">{{ formatDate(order.order_date) }}</td>
              <td class="col-date num">{{ order.lead_time_days }}</td>
              <td class="col-date">{{ formatDate(order.expected_delivery) }}</td>
              <td class="col-status">
                <span :class="['badge', getOrderStatusClass(order.status)]">
                  {{ t(`status.${order.status.toLowerCase()}`) }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, watch, computed } from 'vue'
import { api } from '../api'
import { useFilters } from '../composables/useFilters'
import { useI18n } from '../composables/useI18n'
import { formatCurrencyWithDecimals } from '../utils/currency'

export default {
  name: 'Orders',
  setup() {
    const { t, currentCurrency, translateProductName, translateCustomerName } = useI18n()

    const currencySymbol = computed(() => {
      return currentCurrency.value === 'JPY' ? '¥' : '$'
    })
    const loading = ref(true)
    const error = ref(null)
    const orders = ref([])
    const submittedOrders = ref([])
    const submittedError = ref(null)

    // Use shared filters
    const {
      selectedPeriod,
      selectedLocation,
      selectedCategory,
      selectedStatus,
      getCurrentFilters
    } = useFilters()

    const loadOrders = async () => {
      try {
        loading.value = true
        const filters = getCurrentFilters()
        const fetchedOrders = await api.getOrders(filters)

        // Sort orders by order_date (earliest first)
        orders.value = fetchedOrders.sort((a, b) => {
          const dateA = new Date(a.order_date)
          const dateB = new Date(b.order_date)
          return dateA - dateB
        })
      } catch (err) {
        error.value = 'Failed to load orders: ' + err.message
      } finally {
        loading.value = false
      }
    }

    // Shared util: app-locale grouping and USD->JPY conversion, 2 decimals for USD
    const money = (v) => formatCurrencyWithDecimals(v, currentCurrency.value, 2)

    const loadSubmittedOrders = async () => {
      try {
        submittedOrders.value = await api.getSubmittedOrders()
      } catch (err) {
        submittedError.value = 'Failed to load submitted orders: ' + err.message
      }
    }

    // Watch for filter changes and reload data
    watch([selectedPeriod, selectedLocation, selectedCategory, selectedStatus], () => {
      loadOrders()
    })

    const getOrdersByStatus = (status) => {
      return orders.value.filter(order => order.status === status)
    }

    const getOrderStatusClass = (status) => {
      const statusMap = {
        'Delivered': 'success',
        'Shipped': 'info',
        'Processing': 'warning',
        'Backordered': 'danger',
        'Submitted': 'info'
      }
      return statusMap[status] || 'info'
    }

    const formatDate = (dateString) => {
      const { currentLocale } = useI18n()
      const locale = currentLocale.value === 'ja' ? 'ja-JP' : 'en-US'
      return new Date(dateString).toLocaleDateString(locale, {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      })
    }

    onMounted(() => {
      loadOrders()
      loadSubmittedOrders()
    })

    return {
      t,
      loading,
      error,
      orders,
      submittedOrders,
      submittedError,
      getOrdersByStatus,
      getOrderStatusClass,
      formatDate,
      currencySymbol,
      money,
      translateProductName,
      translateCustomerName
    }
  }
}
</script>

<style scoped>
/* Auto table layout (no fixed column widths); the wrapper scrolls horizontally on narrow screens.
   nowrap keeps order ids, dates and amounts on one line instead of wrapping at 768px. */
.orders-table {
  width: 100%;
}

.col-order-number,
.col-date,
.col-value,
.col-status {
  white-space: nowrap;
}

.submitted-card {
  margin-top: var(--space-5);
}

.card-hint {
  margin: var(--space-1) 0 0;
  font-size: 0.8125rem;
  color: var(--text-muted);
}

.empty-state {
  padding: var(--space-6);
  text-align: center;
  color: var(--text-muted);
}

/* Items details styling */
.items-details {
  position: relative;
}

.items-summary {
  cursor: pointer;
  color: var(--accent);
  font-weight: 500;
  list-style: none;
  user-select: none;
  display: inline-block;
  white-space: nowrap;
}

.items-summary::-webkit-details-marker {
  display: none;
}

.items-summary::before {
  content: 'B6';
  display: inline-block;
  margin-right: var(--space-1);
  font-size: 0.75rem;
  transition: transform 0.2s;
}

.items-details[open] .items-summary::before {
  transform: rotate(90deg);
}

.items-summary:hover {
  color: var(--accent-hover);
  text-decoration: underline;
}

/* Dropdown container: width is content-driven but capped so it never exceeds the viewport */
.items-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  margin-top: var(--space-2);
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  padding: var(--space-3);
  z-index: 10;
  width: max-content;
  max-width: min(280px, 70vw);
}

.item-entry {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  padding: var(--space-2);
  border-bottom: 1px solid var(--border);
}

.item-entry:last-child {
  border-bottom: none;
}

.item-name {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text);
}

.item-meta {
  font-size: 0.8125rem;
  color: var(--text-muted);
}
</style>

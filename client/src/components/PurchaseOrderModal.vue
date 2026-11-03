<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="isOpen && backlogItem" class="modal-overlay" @click="close">
        <div
          ref="dialogRef"
          class="modal-container"
          role="dialog"
          aria-modal="true"
          aria-labelledby="po-modal-title"
          tabindex="-1"
          @click.stop
        >
          <div class="modal-header">
            <h3 id="po-modal-title" class="modal-title">
              {{ mode === 'view' ? t('purchaseOrder.viewTitle') : t('purchaseOrder.createTitle') }}
            </h3>
            <button class="close-button" type="button" :aria-label="t('common.close')" @click="close">
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <path d="M15 5L5 15M5 5L15 15" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
              </svg>
            </button>
          </div>

          <form class="modal-form" novalidate @submit.prevent="submit">
            <div class="modal-body">
              <!-- Item context, shared by both modes -->
              <div class="item-context">
                <h4 class="item-name">{{ translateProductName(backlogItem.item_name) }}</h4>
                <div class="context-meta">
                  <span>{{ t('purchaseOrder.sku') }}: <span class="mono">{{ backlogItem.item_sku }}</span></span>
                  <span>{{ t('purchaseOrder.shortfall') }}: {{ t('purchaseOrder.unitsCount', { count: shortfall }) }}</span>
                </div>
              </div>

              <!-- View mode -->
              <template v-if="mode === 'view'">
                <div v-if="loading" class="state-message">{{ t('common.loading') }}</div>
                <div v-else-if="loadError" class="form-error" role="alert">{{ loadError }}</div>
                <div v-else-if="po" class="info-grid">
                  <div class="info-item">
                    <div class="info-label">{{ t('purchaseOrder.poId') }}</div>
                    <div class="info-value mono">{{ po.id }}</div>
                  </div>
                  <div class="info-item">
                    <div class="info-label">{{ t('purchaseOrder.status') }}</div>
                    <div class="info-value"><span class="badge">{{ po.status }}</span></div>
                  </div>
                  <div class="info-item">
                    <div class="info-label">{{ t('purchaseOrder.supplier') }}</div>
                    <div class="info-value">{{ po.supplier_name }}</div>
                  </div>
                  <div class="info-item">
                    <div class="info-label">{{ t('purchaseOrder.quantity') }}</div>
                    <div class="info-value">{{ po.quantity.toLocaleString(dateLocale) }}</div>
                  </div>
                  <div class="info-item">
                    <div class="info-label">{{ t('purchaseOrder.unitCost') }}</div>
                    <div class="info-value">{{ money(po.unit_cost) }}</div>
                  </div>
                  <div class="info-item">
                    <div class="info-label">{{ t('purchaseOrder.total') }}</div>
                    <div class="info-value strong">{{ money(po.quantity * po.unit_cost) }}</div>
                  </div>
                  <div class="info-item">
                    <div class="info-label">{{ t('purchaseOrder.expectedDelivery') }}</div>
                    <div class="info-value">{{ formatDate(po.expected_delivery_date) }}</div>
                  </div>
                  <div class="info-item">
                    <div class="info-label">{{ t('purchaseOrder.createdDate') }}</div>
                    <div class="info-value">{{ formatDate(po.created_date) }}</div>
                  </div>
                  <div v-if="po.notes" class="info-item full">
                    <div class="info-label">{{ t('purchaseOrder.notes') }}</div>
                    <div class="info-value notes-text">{{ po.notes }}</div>
                  </div>
                </div>
              </template>

              <!-- Create mode -->
              <template v-else>
                <div class="form-grid">
                  <div class="form-group full">
                    <label for="po-supplier">{{ t('purchaseOrder.supplier') }}</label>
                    <input
                      id="po-supplier"
                      ref="firstFieldRef"
                      v-model="form.supplier"
                      type="text"
                      maxlength="120"
                      class="form-input"
                      :class="{ invalid: errors.supplier }"
                      :aria-invalid="!!errors.supplier"
                    />
                    <span v-if="errors.supplier" class="field-error">{{ errors.supplier }}</span>
                  </div>

                  <div class="form-group">
                    <label for="po-quantity">{{ t('purchaseOrder.quantity') }}</label>
                    <input
                      id="po-quantity"
                      v-model="form.quantity"
                      type="number"
                      min="1"
                      max="100000"
                      step="1"
                      class="form-input"
                      :class="{ invalid: errors.quantity }"
                      :aria-invalid="!!errors.quantity"
                    />
                    <span v-if="errors.quantity" class="field-error">{{ errors.quantity }}</span>
                  </div>

                  <div class="form-group">
                    <!-- The API takes USD, so the input stays in USD; the total below follows the display currency. -->
                    <label for="po-unit-cost">{{ t('purchaseOrder.unitCost') }} (USD)</label>
                    <input
                      id="po-unit-cost"
                      v-model="form.unitCost"
                      type="number"
                      min="0.01"
                      step="0.01"
                      class="form-input"
                      :class="{ invalid: errors.unitCost }"
                      :aria-invalid="!!errors.unitCost"
                    />
                    <span v-if="errors.unitCost" class="field-error">{{ errors.unitCost }}</span>
                  </div>

                  <div class="form-group full">
                    <label for="po-date">{{ t('purchaseOrder.expectedDelivery') }}</label>
                    <input
                      id="po-date"
                      v-model="form.date"
                      type="date"
                      :min="today"
                      class="form-input"
                      :class="{ invalid: errors.date }"
                      :aria-invalid="!!errors.date"
                    />
                    <span v-if="errors.date" class="field-error">{{ errors.date }}</span>
                  </div>

                  <div class="form-group full">
                    <label for="po-notes">{{ t('purchaseOrder.notes') }}</label>
                    <textarea id="po-notes" v-model="form.notes" rows="3" class="form-input"></textarea>
                  </div>
                </div>

                <div class="total-row">
                  <span class="info-label">{{ t('purchaseOrder.total') }}</span>
                  <span class="total-value">{{ liveTotal === null ? '-' : money(liveTotal) }}</span>
                </div>

                <div v-if="serverError" class="form-error" role="alert">{{ serverError }}</div>
              </template>
            </div>

            <div class="modal-footer">
              <button type="button" class="btn-secondary" @click="close">
                {{ mode === 'view' ? t('common.close') : t('common.cancel') }}
              </button>
              <button v-if="mode !== 'view'" type="submit" class="btn-primary" :disabled="submitting">
                {{ submitting ? t('purchaseOrder.submitting') : t('purchaseOrder.submit') }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch, nextTick, onBeforeUnmount } from 'vue'
import { api } from '../api'
import { useI18n } from '../composables/useI18n'
import { formatCurrencyWithDecimals } from '../utils/currency'

const props = defineProps({
  isOpen: { type: Boolean, default: false },
  backlogItem: { type: Object, default: null },
  mode: { type: String, default: 'create' } // 'create' | 'view'
})
const emit = defineEmits(['close', 'po-created'])

const { t, currentLocale, currentCurrency, translateProductName } = useI18n()

const dialogRef = ref(null)
const firstFieldRef = ref(null)
const form = ref({ supplier: '', quantity: '', unitCost: '', date: '', notes: '' })
const errors = ref({})
const serverError = ref('')
const submitting = ref(false)
const po = ref(null)
const loading = ref(false)
const loadError = ref('')

const dateLocale = computed(() => (currentLocale.value === 'ja' ? 'ja-JP' : 'en-US'))
const money = (v) => formatCurrencyWithDecimals(Number(v), currentCurrency.value, 2)

const shortfall = computed(() =>
  props.backlogItem ? Math.max(0, props.backlogItem.quantity_needed - props.backlogItem.quantity_available) : 0
)

// Local YYYY-MM-DD (toISOString would be UTC and can be off by a day). Strings in this format compare correctly.
const today = computed(() => {
  const d = new Date()
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
})

const formatDate = (s) => {
  if (!s) return '-'
  // Parse as local midnight; new Date('YYYY-MM-DD') is UTC and could shift the day.
  const [y, m, d] = String(s).slice(0, 10).split('-').map(Number)
  const date = new Date(y, m - 1, d)
  if (isNaN(date.getTime())) return s
  return date.toLocaleDateString(dateLocale.value, { year: 'numeric', month: 'long', day: 'numeric' })
}

const liveTotal = computed(() => {
  const q = Number(form.value.quantity)
  const c = Number(form.value.unitCost)
  return q > 0 && c > 0 ? q * c : null
})

const close = () => emit('close')

// Client-side checks mirror the API limits; the server stays the source of truth.
const validate = () => {
  const e = {}
  const name = form.value.supplier.trim()
  if (name.length < 1 || name.length > 120) e.supplier = t('purchaseOrder.errors.supplier')
  const q = Number(form.value.quantity)
  if (form.value.quantity === '' || !Number.isInteger(q) || q < 1 || q > 100000) e.quantity = t('purchaseOrder.errors.quantity')
  const c = Number(form.value.unitCost)
  if (form.value.unitCost === '' || !(c > 0)) e.unitCost = t('purchaseOrder.errors.unitCost')
  if (!form.value.date) e.date = t('purchaseOrder.errors.date')
  else if (form.value.date < today.value) e.date = t('purchaseOrder.errors.pastDate')
  errors.value = e
  return Object.keys(e).length === 0
}

// Map a FastAPI error response to a translated message (and field highlight where possible).
const applyServerError = (err) => {
  const status = err.response?.status
  const detail = err.response?.data?.detail
  if (status === 409) serverError.value = t('purchaseOrder.errors.duplicate')
  else if (status === 404) serverError.value = t('purchaseOrder.errors.itemNotFound')
  else if (status === 400) serverError.value = t('purchaseOrder.errors.pastDate')
  else if (status === 422 && Array.isArray(detail)) {
    // detail[].loc is like ['body', 'quantity']; route each to its field, anything unknown to the banner.
    const fieldKey = { supplier_name: 'supplier', quantity: 'quantity', unit_cost: 'unitCost', expected_delivery_date: 'date' }
    const fieldErrors = {}
    detail.forEach((d) => {
      const key = fieldKey[d.loc?.[d.loc.length - 1]]
      if (key) fieldErrors[key] = t(`purchaseOrder.errors.${key}`)
    })
    errors.value = fieldErrors
    if (Object.keys(fieldErrors).length === 0) serverError.value = t('purchaseOrder.errors.generic')
  } else serverError.value = t('purchaseOrder.errors.generic')
}

const submit = async () => {
  if (submitting.value) return
  serverError.value = ''
  if (!validate()) return
  submitting.value = true
  try {
    const created = await api.createPurchaseOrder({
      backlog_item_id: props.backlogItem.id,
      supplier_name: form.value.supplier.trim(),
      quantity: Number(form.value.quantity),
      unit_cost: Number(form.value.unitCost),
      expected_delivery_date: form.value.date,
      notes: form.value.notes.trim() || null
    })
    emit('po-created', created)
  } catch (err) {
    console.error('Create PO error:', err)
    applyServerError(err)
  } finally {
    submitting.value = false
  }
}

const loadPO = async () => {
  loading.value = true
  loadError.value = ''
  po.value = null
  try {
    po.value = await api.getPurchaseOrderByBacklogItem(props.backlogItem.id)
  } catch (err) {
    console.error('Load PO error:', err)
    loadError.value = err.response?.status === 404 ? t('purchaseOrder.notFound') : t('purchaseOrder.loadError')
  } finally {
    loading.value = false
  }
}

// Prefill unit cost from the inventory item with the same SKU; best effort, the field stays editable.
const prefillUnitCost = async (itemId) => {
  try {
    const inventory = await api.getInventory()
    const match = inventory.find((i) => i.sku === props.backlogItem?.item_sku)
    // Skip if the user switched items meanwhile or already typed a value.
    if (match && props.backlogItem?.id === itemId && form.value.unitCost === '') {
      form.value.unitCost = String(match.unit_cost)
    }
  } catch (err) {
    console.error('Unit cost prefill failed:', err)
  }
}

const onKeydown = (e) => {
  if (e.key === 'Escape') close()
}

// Remember who had focus so it can be restored when the modal closes.
let previouslyFocused = null

watch(
  () => [props.isOpen, props.backlogItem?.id, props.mode],
  async ([open]) => {
    if (!open || !props.backlogItem) return
    previouslyFocused = document.activeElement
    window.addEventListener('keydown', onKeydown)
    errors.value = {}
    serverError.value = ''
    if (props.mode === 'view') {
      loadPO()
    } else {
      form.value = { supplier: '', quantity: String(shortfall.value || ''), unitCost: '', date: '', notes: '' }
      prefillUnitCost(props.backlogItem.id)
    }
    await nextTick()
    // First field in create mode; the dialog itself otherwise so Escape and Tab start inside it.
    ;(firstFieldRef.value || dialogRef.value)?.focus()
  },
  { immediate: true }
)

watch(
  () => props.isOpen,
  (open) => {
    if (open) return
    window.removeEventListener('keydown', onKeydown)
    previouslyFocused?.focus?.()
    previouslyFocused = null
  }
)

onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: var(--overlay);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  padding: var(--space-4);
}

.modal-container {
  background: var(--surface);
  border-radius: 12px;
  box-shadow: var(--shadow-lg);
  max-width: 640px;
  width: 100%;
  max-height: calc(100dvh - 32px);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-container:focus {
  outline: none;
}

.modal-form {
  display: flex;
  flex-direction: column;
  min-height: 0;
  flex: 1;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.5rem;
  border-bottom: 1px solid var(--border);
}

.modal-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--text);
  letter-spacing: -0.025em;
  margin: 0;
}

.close-button {
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  padding: 0.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  transition: all 0.15s ease;
}

.close-button:hover {
  background: var(--surface-2);
  color: var(--text);
}

.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 1.5rem;
}

.item-context {
  padding-bottom: var(--space-4);
  border-bottom: 1px solid var(--border);
  margin-bottom: var(--space-5);
}

.item-name {
  font-size: 1.125rem;
  font-weight: 700;
  color: var(--text);
  margin: 0 0 var(--space-2) 0;
}

.context-meta {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2) var(--space-5);
  font-size: 0.875rem;
  color: var(--text-muted);
}

.mono {
  font-family: 'Monaco', 'Courier New', monospace;
}

.state-message {
  text-align: center;
  padding: var(--space-5);
  color: var(--text-muted);
}

/* Form */
.form-grid,
.info-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-4);
}

.full {
  grid-column: 1 / -1;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

label,
.info-label {
  font-size: 0.813rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
}

.form-input {
  padding: 0.625rem 0.75rem;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface);
  color: var(--text);
  font-size: 0.938rem;
  font-family: inherit;
  transition: border-color 0.15s ease;
}

.form-input:focus {
  outline: none;
  border-color: var(--accent);
}

.form-input.invalid {
  border-color: var(--danger);
}

textarea.form-input {
  resize: vertical;
}

.field-error {
  font-size: 0.813rem;
  color: var(--danger);
}

.form-error {
  margin-top: var(--space-4);
  padding: var(--space-3) var(--space-4);
  border-radius: 8px;
  font-size: 0.875rem;
  color: var(--danger);
  background: color-mix(in srgb, var(--danger) 16%, transparent);
}

.total-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-top: var(--space-5);
  padding-top: var(--space-4);
  border-top: 1px solid var(--border);
}

.total-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text);
  font-variant-numeric: tabular-nums;
}

/* View mode */
.info-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  min-width: 0;
}

.info-value {
  font-size: 0.938rem;
  color: var(--text);
  font-weight: 500;
  overflow-wrap: anywhere;
}

.info-value.strong {
  font-weight: 700;
}

.notes-text {
  white-space: pre-wrap;
}

.badge {
  display: inline-block;
  padding: 0.25rem 0.625rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
  background: color-mix(in srgb, var(--warning) 16%, transparent);
  color: var(--warning);
}

/* Footer */
.modal-footer {
  padding: 1.25rem 1.5rem;
  border-top: 1px solid var(--border);
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
}

.btn-secondary,
.btn-primary {
  padding: 0.625rem 1.25rem;
  border-radius: 8px;
  font-weight: 500;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.15s ease;
  font-family: inherit;
}

.btn-secondary {
  background: var(--surface-2);
  border: 1px solid var(--border);
  color: var(--text);
}

.btn-secondary:hover {
  background: var(--border);
  border-color: var(--border-strong);
}

.btn-primary {
  background: var(--accent);
  border: 1px solid var(--accent);
  color: var(--accent-contrast);
}

.btn-primary:hover:not(:disabled) {
  opacity: 0.9;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

@media (max-width: 520px) {
  .form-grid,
  .info-grid {
    grid-template-columns: 1fr;
  }
}

/* Modal transition animations */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.2s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-active .modal-container,
.modal-leave-active .modal-container {
  transition: transform 0.2s ease;
}

.modal-enter-from .modal-container,
.modal-leave-to .modal-container {
  transform: scale(0.95);
}
</style>

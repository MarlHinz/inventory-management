import { ref, watch, nextTick, onBeforeUnmount } from 'vue'

// Shared dialog behaviour: Escape closes, focus moves into the dialog on open
// and returns to the opener on close. Bind the returned ref to the element with role="dialog" (needs tabindex="-1").
export function useModalA11y(isOpen, close) {
  const dialogRef = ref(null)
  let opener = null

  const onKeydown = (e) => {
    if (e.key === 'Escape') close()
  }

  watch(
    isOpen,
    async (open) => {
      if (open) {
        opener = document.activeElement
        window.addEventListener('keydown', onKeydown)
        await nextTick() // the dialog is v-if'd, so wait for it to render
        dialogRef.value?.focus()
      } else {
        window.removeEventListener('keydown', onKeydown)
        opener?.focus?.()
        opener = null
      }
    },
    { immediate: true }
  )

  onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))

  return { dialogRef }
}

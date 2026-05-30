// Hagrid only uses JS for progressive enhancement! Make sure everything you
// implement in JS is at most "nice to have" and never required functionality.

// Synchronize inputs tagged with [data-synclocalstorage] to sessionStorage:
// When changing the input value, store it. When loading the page, restore the
// value (if any) from sessionStorage to the input, as long as the input is
// empty and the storage isn't.
document.addEventListener('DOMContentLoaded', () => {
  for (const input of document.querySelectorAll('[data-synclocalstorage]')) {
    const key = input.dataset.synclocalstorage

    if (!input.value) {
      const value = sessionStorage.getItem(key, '')
      if (value) {
        console.log('restored value for', key)
        input.value = value
      }
    }

    input.addEventListener('change', (e) => {
      sessionStorage.setItem(key, e.target.value)
      console.log('stored value for', key)
    })
  }
})

// Reset all forms with the class "reset-on-navigation" when navigating back
// and forth. This is to prevent duplicate entry where an empty field means "no
// change", such as in "variation_count.html".
window.addEventListener('pageshow', (e) => {
  if (e.persisted || performance.getEntriesByType('navigation')[0].type === 'back_forward') {
    for (const form of document.querySelectorAll('form.reset-on-navigation')) {
      form.reset()
    }
  }
})

// Hagrid only uses JS for progressive enhancement! Make sure everything you
// implement in JS is at most "nice to have" and never required functionality.

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

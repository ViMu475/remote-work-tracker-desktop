// Build config for static/css/app.css (see BUILDING.md, "Rebuild the CSS").
// Colours are NOT taken from Tailwind: they come from the CSS variables in tailwind-input.css.
module.exports = {
  content: ['./templates/index.html', './static/js/app.js'],
  safelist: ['rating-good', 'rating-tight', 'rating-exceeded', 'toast-success', 'toast-error', 'toast-warning', 'toast-info', 'hidden', 'dark-mode', 'light-mode', 'kpi-ok', 'kpi-warn', 'kpi-err', 'bar-ok', 'bar-warn', 'bar-err'],
  theme: { extend: {} },
  plugins: [],
};

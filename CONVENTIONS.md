# Coding Conventions & Standards

## Priority Ladder

1. **Correctness** — Zero uncaught exceptions, faithful business rule enforcement.
2. **Security** — Server-side authorization, input validation, zero DOM XSS.
3. **Usability & UX** — Clear error messages, immediate UI feedback, persistent inputs.
4. **Accessibility** — Semantic HTML and keyboard navigation.
5. **Maintainability** — Modular separation, explicit dependency injection.

---

## Python Conventions

- **Formatting & Linting:** Enforced via `ruff`. Line length: 120.
- **Factory Pattern:** Always use `create_app(config_object)` for app construction.
- **Imports:** Group standard library, third-party, and first-party imports cleanly.
- **Error Handling:** Avoid silent suppression. Catch specific exceptions and log with context.
- **Timezone:** Always obtain system datetimes using `utils.timezone.get_now()`. Never call naive `datetime.now()` directly for attendance logic.

---

## Frontend Conventions

- **Safe DOM Injection:** Never interpolate unescaped variables into `.innerHTML`. Use `escapeHtml()` from `static/js/base.js` or `textContent`.
- **API Payloads:** Send JSON objects (`{ "user_id": id }`), not naked JSON strings.
- **Error Feedback:** Catch API rejections and present user-friendly error dialogs or field highlighting.

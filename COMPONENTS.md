# Component Architecture and Engineering

> Owns component layers, contracts, reuse decisions, and abstraction thresholds—not overall visual direction or end-user workflow design. Use `DESIGN.md` for visual tokens, `UI.md` for rendering and accessibility implementation, and `UX.md` for user goals and interaction behavior. Use for component-driven frontends or other component-based UI architectures.

## Component layers

Document the component layering hierarchy used in the repository:

```text
Layer 4: Views & Pages       → Route entry points, orchestrates features and layouts
Layer 3: Feature / Domain   → Business-aware components tied to specific domain models
Layer 2: Shared UI          → Generic reusable elements (buttons, inputs, modals, tables)
Layer 1: Primitives / Headless → Low-level unstyled primitives, accessibility wrappers, tokens
```

- **Primitive / headless layer:** [Underlying primitive library or native elements, if any]
- **Shared UI location:** [Path to design system / generic UI components]
- **Feature components location:** [Path to domain-specific feature components]
- **View / page location:** [Path to route views / pages]

## Reuse hierarchy (search before create)

Before writing any new component, follow this 4-step search hierarchy:

1. **Use existing primitive/shared component:** Inspect the shared component directory first.
2. **Compose existing components:** Combine existing primitives or shared components to form the needed pattern.
3. **Extend existing component:** If an existing component is close, add a backward-compatible optional prop or slot. Avoid breaking existing call sites.
4. **Create a new component:** Only build a new component if steps 1–3 cannot satisfy the requirement without harmful compromises.

## Component decision framework

Extract a new component when:

- **Rule of three:** The pattern or markup appears in at least three distinct places.
- **Independent state & behavior:** The element encapsulates nontrivial internal state, keyboard navigation, or accessibility logic.
- **Isolated testability:** The component has a distinct contract that can be tested in isolation.
- **Clear boundaries:** The props interface is clean, minimal, and does not leak callers' internal state.

Avoid extracting a component when:
- It is only used once and does not encapsulate complex behavior (premature abstraction).
- It merely wraps a native element or another component without adding behavior or styling.

## Component contracts and state

- **Props discipline:** Document required vs optional props. Prefer strong typing for props interfaces.
- **Controlled vs uncontrolled:** Follow the repository's convention for state ownership in form controls.
- **Separation of concerns:** Keep data fetching and domain business logic in feature/page containers; keep shared UI components purely presentational.
- **Component states:** Account for empty, loading, disabled, error, and responsive variants in the component definition.

## Anti-patterns

- **Component duplication:** Creating `CustomButton.tsx` or `NewModal.vue` when `Button` and `Modal` already exist.
- **Business logic in primitives:** Importing database queries, API clients, or auth tokens directly into shared UI components.
- **God components:** Creating monolithic multi-thousand-line components that handle multiple unrelated screens or modes.
- **Prop drilling soup:** Passing 10+ props down four levels instead of using component composition or context.
- **Styling overrides with `!important`:** Forcing CSS overrides instead of using theme variants or supported props.
- **Uncontrolled prop explosion:** Adding bespoke boolean flags (`isCompactHeaderCardVariant`) instead of composing smaller primitives.

## See also

- [DESIGN.md](DESIGN.md) — Visual tokens, design system foundations, and anti-slop rules
- [UI.md](UI.md) — Framework rendering model, form handling, and styling integration
- [UX.md](UX.md) — User interaction mechanics, states, and accessibility expectations
- [CONVENTIONS.md](CONVENTIONS.md) — Code formatting, naming, and file organization

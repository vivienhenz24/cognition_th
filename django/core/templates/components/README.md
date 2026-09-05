# Django component translations

These templates and the `[data-slot]` rules in `core/static/core/styles.css` translate the shadcn/ui component anatomy used by this app into server-rendered Django HTML and handwritten CSS. The source structures are shadcn/ui's Button, Card, Badge, Input, Select, Textarea, Table, and Alert components from the `new-york-v4` registry; React composition becomes Django includes for leaf components and explicit `data-slot` composition for containers with arbitrary content.

## Components

- `button.html`: `default`, `destructive`, `outline`, `secondary`, `ghost`, and `link` variants plus `default`, `small`, and `large` sizes.
- `button_link.html`: the shadcn `asChild` button pattern translated to an anchor.
- `badge.html`: shadcn badge variants plus the app's semantic low, medium, high, approved, and rejected variants.
- `alert.html`: default, success, and destructive alert states.
- `page_header.html`, `stat_card.html`, and `empty_state.html`: repeated application compositions built from the translated primitives.
- Card and Table containers use the same named `data-slot` anatomy as shadcn so their children remain composable in ordinary Django templates.

The application intentionally does not ship React, TypeScript, Radix, Tailwind, or class-variance-authority. Variant selection is expressed through stable BEM-style classes while native controls preserve Django and HTMX behavior.

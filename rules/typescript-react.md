---
trigger: glob
globs: "*.ts, *.tsx, tsconfig*.json"
description: "TypeScript, React, Next.js, and React Native coding standards."
---

# TypeScript & React / Next.js / RN Standards

- **Strict TypeScript**: Never introduce implicit `any`, explicit `: any`, `@ts-ignore`, or unverified `as any` casts. Prefer discriminated unions, `unknown` with narrowing, and explicit return types on exported functions.
- **Single Source of Truth for Types**: Define shared domain interfaces and API contracts in one canonical types location rather than duplicating component-local copies.
- **Component Composition**: Prefer compound components, slots/children, and clean props over boolean prop proliferation.
- **Render & Effect Hygiene**: Derive values directly during render instead of chaining `useEffect` + `setState`. Reserve `useEffect` strictly for external system synchronization with proper cleanup.
- **Next.js Boundaries**: Keep Server vs Client Component (`"use client"`) boundaries explicit; never import server-only secrets or DB clients into client bundles.
- **Verification**: Run `tsc --noEmit` (or the project's `typecheck` script) and relevant lint/build/test commands after edits.

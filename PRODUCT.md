# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack
Vite + React single page (frontend), FastAPI + LangGraph backend; the user asked for "FastAPI and Next.js or React"; React via Vite chosen because one chat page needs no SSR or routing.

## Users
Primary: MediBuddy reviewers evaluating a take-home assignment, on a laptop during a live review call, typing questions and asking "why did it say that?". Secondary: end users on a phone checking quickly whether an outdoor plan is safe. Both have short attention spans: the answer must be readable in a glance.

## Product Purpose
Answers outdoor-activity safety questions ("is it safe to cycle today?") from live Open-Meteo weather, where every piece of advice comes from a written SOP the business controls, never from the model. Success: a verdict a user can trust and trace to a named policy, and an honest "no guidance" or "data unavailable" instead of a guess.

## Positioning
Advice is policy-backed and traceable: each reply names the SOP it came from and shows the live numbers that triggered it. It refuses rather than improvises.

## Operating Context
Live review call: reviewers type paraphrased, adversarial and follow-up questions, add an SOP to `sops.yaml` live, and check the reply cites it. Sessions are in-memory per browser tab.

## Capabilities and Constraints
- Verdicts: go, caution, avoid, none (no guidance), ask (needs a location), unavailable (weather or model down).
- Every reply carries the cited SOPs (id, title, severity, triggering reasons) and the live facts used.
- Design and polish are explicitly not graded by the assignment; clarity and the fact that it runs are.

## Brand Commitments
MediBuddy-flavoured: may nod to MediBuddy's blue/red palette as a courtesy to the reviewing company; no MediBuddy logo or name presented as the product's own. Tone: calm and clinical, a trusted health/safety advisory, precise and quiet.

## Evidence on Hand
None beyond live API data. No testimonials, customers or metrics exist; never fabricate them.

## Product Principles
1. Verdict first, reasons one tap away.
2. Never show a number that did not come from the API for this request.
3. Honest refusal beats plausible advice.
4. The policy is the authority; the interface makes the citation visible.

## Accessibility & Inclusion
Verdict must not rely on colour alone (word + icon shape). Keyboard usable, WCAG AA contrast.

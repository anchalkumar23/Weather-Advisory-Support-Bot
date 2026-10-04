---
name: Weather Rx
description: Outdoor safety advice, dispensed only from written policy and live weather.
colors:
  counter: "#e4e7ea"
  counter-deep: "#d3d8de"
  label-stock: "#fbfaf6"
  rx-navy: "#14264a"
  ink-secondary: "#46546f"
  rx-red: "#e2363d"
  rx-red-ink: "#b8222a"
  avoid: "#b8222a"
  caution-ink: "#7a5000"
  caution-sticker: "#f6c445"
  go: "#1d6e43"
  go-sticker: "#d6efdf"
  quiet-fill: "#e8ebf0"
typography:
  verdict:
    fontFamily: "Atkinson Hyperlegible Next Variable, system-ui, sans-serif"
    fontSize: "clamp(2.5rem, 7vw, 4rem)"
    fontWeight: 800
    lineHeight: 1
    letterSpacing: "-0.03em"
  instruction:
    fontFamily: "Atkinson Hyperlegible Next Variable, system-ui, sans-serif"
    fontSize: "1.125rem"
    fontWeight: 400
    lineHeight: 1.55
  body:
    fontFamily: "Atkinson Hyperlegible Next Variable, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.5
  readout:
    fontFamily: "Atkinson Hyperlegible Mono Variable, ui-monospace, monospace"
    fontSize: "0.8125rem"
    fontWeight: 500
    fontFeature: "tnum"
rounded:
  sticker: "6px"
  control: "12px"
  label: "14px"
spacing:
  label-inset: "20px"
  label-inset-mobile: "16px"
  thread-gap: "14px"
components:
  label:
    backgroundColor: "{colors.label-stock}"
    textColor: "{colors.rx-navy}"
    rounded: "{rounded.label}"
  label-meta-strip:
    backgroundColor: "{colors.rx-navy}"
    textColor: "{colors.label-stock}"
    typography: "{typography.readout}"
    padding: "8px 20px"
  sticker-avoid:
    backgroundColor: "{colors.avoid}"
    textColor: "#ffffff"
    rounded: "{rounded.sticker}"
  sticker-caution:
    backgroundColor: "{colors.caution-sticker}"
    textColor: "#2b1d00"
    rounded: "{rounded.sticker}"
  sticker-go:
    backgroundColor: "{colors.go-sticker}"
    textColor: "{colors.go}"
    rounded: "{rounded.sticker}"
  composer-input:
    backgroundColor: "{colors.label-stock}"
    textColor: "{colors.rx-navy}"
    rounded: "{rounded.control}"
  composer-send:
    backgroundColor: "{colors.rx-navy}"
    textColor: "{colors.label-stock}"
    rounded: "{rounded.control}"
    width: "52px"
---

# Design System: Weather Rx

## Overview
**North star: the dispensing label.** Every answer is printed like a pharmacy label: a navy header strip with the label number, place and time window; the verdict as one word at poster scale; the instruction in plain sentences; coloured auxiliary-warning stickers, one per policy applied; and a perforated tear-off stub ("Why?") holding the rule, the policy text and the live readings. Calm, clinical, MediBuddy-flavoured (navy and red), built for short attention spans: verdict first, reasons one tap away.

## Colors
Restrained strategy on a cool grey pharmacy-counter ground (`counter`). Labels are warm-white `label-stock`; all ink is `rx-navy`. Red appears only as the Rx accent: label numbers and SOP catalogue ids (`rx-red-ink` on stock for contrast). Verdict colour is semantic and always paired with a word and an icon shape: `avoid` red, `caution` amber (amber fill with dark-brown text on stickers, `caution-ink` for the verdict word), `go` green. No-guidance, unavailable and ask states use `ink-secondary`, never a verdict colour.

## Typography
One family, Atkinson Hyperlegible Next (Braille Institute's legibility face), for everything people read; its Mono sibling only for measurements and identifiers: the label meta strip, SOP ids, the 24 h strip scale and the readings table, all with tabular numerals. Scale steps: verdict (2.5–4rem, 800), empty-state heading (1.75–2.5rem, 800), instruction (1.125rem), body (1rem), small (0.8125–0.9375rem). Tracking never tighter than -0.03em.

## Layout
Single centred column, max 46rem, 16px gutters. Thread is a vertical stack (14px gap); user questions are right-aligned grey slips, answers are full-width labels. Composer is sticky at the bottom with a fade from the counter colour. Under 520px the masthead tagline hides and label insets drop to 16px.

## Elevation & Depth
Labels lift off the counter with one soft, offset shadow and no border. Nothing else casts a shadow. Inside a label, structure comes from the navy strip and a 2px dashed perforation above the stub.

## Shapes
Labels 14px radius, controls 12px, stickers 6px (die-cut feel; every second sticker rotated -0.6°). Pills only for the small ghost "New session" control.

## Components
- **Label**: meta strip → verdict (icon + word) → instruction with inline SOP ids → stickers → stub. Entry motion: prints downward from the slot (clip-path + 6px drop, 520ms ease-out), the page's only authored motion; disabled under reduced motion.
- **Sticker**: severity word in caps, SOP id in mono, title. Colour by severity: critical/high red, moderate amber, low/info green.
- **Why stub**: button with `aria-expanded`; opens policy list (id, title, severity, triggering rule, policy text), a 24 h strip with the checked window drawn to scale, and a readings table where values that tripped a rule are bold with the rule beside them.
- **Empty label**: question heading, one-paragraph promise, four sample questions as outlined buttons.
- **Composer**: stock-white input with navy 2px focus outline, square navy send button, disabled at 35% opacity.

## Do's and Don'ts
- Do lead every answer with the verdict word; never colour alone.
- Do print every number in mono with its unit; numbers come only from the API response.
- Do show the SOP id wherever advice appears.
- Don't add gradients, glass, or decorative illustration; the label is the only material.
- Don't add eyebrows/kickers above headings.

Not canonized: none of the build's elements are craft-floor refusals; the composer's bottom fade is a functional scrim, not a decorative gradient.

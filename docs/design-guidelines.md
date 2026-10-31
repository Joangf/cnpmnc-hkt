# Design guidelines: "Bold blocks. Calm care."

The source of truth is the visual board `frontend/Hospital Booking Design Guidelines.html`. It holds four
boards: 01 Foundations, 02 Components, 03 Booking flow & rules and 04 Homepage example. This file
is the text version, for use when writing UI. The tokens are implemented in
`frontend/tailwind.config.js` and the component classes in `frontend/src/index.css`.

The style uses flat, saturated color fields held together by heavy black lines. Each screen has few elements, big
type and lots of air. It should be eye-catching without ever feeling clinical or cluttered.

## Principles

1. **One loud thing.** Give each screen one big color block or headline. Keep everything else white and quiet.
2. **Lines draw the grid.** 3px black rules frame panels, inputs and cards. Do not use shadows or gradients. Corners are square.
3. **One task per step.** The flow is specialty → doctor → time → details → confirm, and progress is always shown.
4. **Accessible by default.** Meet WCAG 2.2 AA. Use black text on every bright color, make targets at least 48px, and support the keyboard fully.

## Color

| Token | Hex | Use | Tailwind |
|---|---|---|---|
| Ink | `#111111` | All text and lines | `ink` |
| Muted | `#3D3D3D` | Captions, helper text | `muted` |
| Sky | `#12B5E5` | Hero blocks, avatars | `sky` |
| Mint | `#5EE07A` | Tiles, success fill | `mint` |
| Sun | `#FFC72C` | Selected, highlight, hover | `sun` |
| Blush | `#F6C9BD` | Illustration ground | `blush` |
| Cobalt | `#1652C8` | Primary action, link hover | `cobalt` |
| Alert red | `#C8231B` | Emergencies and errors only | `alert` |
| Disabled | `#8A8A8A` line, `#EDEDED` fill, `#5C5C5C` text, `#F2F2F2` unavailable slot | | `grey-400/200/600/100` |

- Bright colors are backgrounds only and never text color. Only Cobalt and Alert red carry white text.
- Do not stack three bright colors next to each other in one section.

## Typography (Figtree, self-hosted via `@fontsource-variable/figtree`)

| Style | Spec | Tailwind |
|---|---|---|
| Display | 800, 56/60, −0.02em | `text-display` |
| Heading 1 | 800, 36/44 | `text-h1` / `.page-title` |
| Heading 2 | 800, 24/32 | `text-h2` |
| Nav / label | 800, 16, caps, +0.06em | `.eyebrow`, `.label` (15px) |
| Body | 400, 18/28 | `text-body` (default) |
| Caption | 400, 15/22, Muted | `.caption` |

## Lines, space and shape

- **Line weights:** 3px for panels, inputs, cards and nav. 2px for chips, slots, tags and small controls. 1px for table and list rows only.
- **Spacing:** use the 8-point scale (8, 16, 24, 32, 48, 64, 96).
- **Shape:** radius is always 0. Circles appear only in illustrations and avatars. Tailwind's `rounded-*` scale is reduced to `none` and `full`, and shadows are disabled.
- **Layout:** use 12 columns with a 1280px max width (`max-w-page`). Panels butt edge to edge and share their borders; use `.tile-grid`.

## Components

| Component | Rules | Class |
|---|---|---|
| Button | 56px tall, 3px ink border, caps 800. Primary is Cobalt with white text and **turns Sun with black text on hover**. Use one Cobalt button per screen. Disabled is grey. | `.btn-primary`, `.btn-secondary`, `.btn-dark`, `.btn-danger`, `.btn-sm` (48px) |
| Text link | 600 weight, 2px underline offset 4px, Cobalt on hover. | `.link` |
| Focus | 3px dashed ink outline, offset 4px, on every interactive element. | global `:focus-visible` |
| Field | Caps label above, 56px input with a 3px border, and helper text below. On error the border and text turn red, and the error text says how to fix the problem, not just what's wrong. | `Field`, `.input`, `.label` |
| Filter chip | 48px tall, 2px border. When pressed it is Sun, weight 800, with a ✓. | `FilterChip`, `.chip` |
| Tag | 2px border, 14px, 600 weight. | `.tag` |
| Doctor card | An avatar block plus name, specialty and experience, then a row of tags, then a split button row: **Book** (Cobalt) and **View profile**. | `DoctorCard` |
| Day picker | 68px tall, 2px border. The selected day is Ink with white text. | `.day` |
| Time slot | 52px tall, 2px border, grouped under Morning and Afternoon. The selected slot is Sun with a ✓. An unavailable slot is dashed grey with a line-through. | `.slot` |
| Notice | A full color block with an icon and a bold lead. Emergency uses Alert with white text, success uses Mint, and warning uses Sun. | `Notice`, `ErrorAlert` |
| Status | Always show color, icon and word together. | `StatusBadge` |

## Booking flow (five steps, under two minutes)

1. **Find care.** Search by doctor, specialty or symptom. The emergency number is always visible.
2. **Choose doctor.** Cards show the fee and visit details. Filter rather than paginate.
3. **Pick a time.** Progress reads "Step 3 of 5 · Pick a time".
4. **Your details.** Ask only for what's needed.
5. **Confirm.** Show a summary with a reference code, plus reschedule or cancel links.

Show availability before asking anyone to sign in. Back never clears what the patient typed.

## Do / don't

**Do:**

- Let one color block carry the page and keep the rest white.
- Write like a kind nurse: "Your appointment is Tue, 4 Nov at 9:30 AM."
- Show the total cost before the patient confirms.
- Use flat, friendly geometric illustration.

**Don't:**

- Set text in yellow, mint or sky.
- Use stock photos, gradients or drop shadows.
- Use countdowns or fake scarcity.
- Hide the cancel link.

## Accessibility, responsive design and trust

- **Accessibility:**
  - Black text on bright fills passes 4.5:1.
  - Targets are at least 48×48px and 8px apart.
  - Every step works with a keyboard and a screen reader.
  - The layout works at 200% zoom and respects reduced motion.
- **Responsive:**
  - Design mobile-first at 390px.
  - The split hero stacks with the color block on top.
  - The nav collapses to a bordered Menu button.
  - The primary action sticks to the bottom.
  - Every phone number is tap-to-call (`telHref`).
- **Trust and privacy:**
  - Explain why each sensitive field is asked; use the field hints.
  - Never show symptoms in notifications.
  - Confirm with a reference code.

# CareBook design guidelines — "Warm, simple, and human."

Text version of the boards in this folder (`Hospital Booking Design Guidelines.html`, `.pdf` and the four PNGs). Tokens live in [frontend/tailwind.config.js](../../frontend/tailwind.config.js); component classes in [frontend/src/index.css](../../frontend/src/index.css).

## Principles
1. **Calm first** — soft tints, white space, one accent. Strong colour only for urgent help.
2. **Clean and simple** — thin lines, gentle corners, soft shadows; no decoration that doesn't help.
3. **One task per step** — specialty → doctor → time → details → confirm, with progress shown.
4. **Accessible for all** — WCAG 2.2 AA, 48px touch targets, large readable text for older patients.

About 80% of every screen stays white; berry is the only strong colour in normal use.

## Colour
| Token (Tailwind) | Hex | Use |
|---|---|---|
| `berry` | #8C1D4F | Actions, links (hover `berry-dark` #6E163E) |
| `blush` | #FBE9EF | Hero, selected states |
| `mist` | #EAF2F8 | Info panels |
| `peach` | #FFF1E6 | Imagery ground |
| `ink` | #2B1A22 | Text |
| `alert` | #B42318 | Emergency only |
| `muted` | #5E4B53 | Secondary text (7:1) |
| `line` | #EADFD8 | Borders and dividers |
| `field` | #D9CBC2 | Input borders |
| `surface` | #FAF6F2 | Page surface, tags, footer |
| `success` | #1E7A4F | Success (soft #E8F4EE) |
| `notice` | #A15C07 | Notices / waiting |
| `focus` | #E59AB8 | 3px focus ring |

Notice tints: danger #FEF3F2 / line #F4C7C3 / text #7A271A · success #E8F4EE / #BFDFCD / #134D33 · info #EAF2F8 / #C9DCEA / #1E3A57. Disabled: #EEF1F3 with #6B7882 text.

## Typography (Figtree, self-hosted)
| Style | Weight · size/line |
|---|---|
| Display | 700 · 48/56 (hero 56) |
| Heading 1 | 700 · 32/40 |
| Heading 2 | 600 · 22/30 |
| Body | 400 · 18/28 |
| Caption | 400 · 15/22 |

Sentence case everywhere. Capitals only for tiny section labels (`.eyebrow`: 14px, 600, 0.08em, berry).

## Space and shape
- 8-point spacing. 12-column grid, 1200px max content width, 24px gutters, 16px phone margins.
- Radius: 12 buttons and inputs · 16 cards · 20 panels · full for chips and avatars.
- 1px `line` borders plus a soft warm shadow (`shadow-card`: 0 8px 24px at 8%) on cards and panels. Berry buttons carry `shadow-button`.

## Components
| Component | Spec | Class / component |
|---|---|---|
| Primary button | 52px, berry, white 17px/600, radius 12. One per screen; label says what happens next | `.btn-primary` |
| Secondary button | 1.5px berry outline, berry text | `.btn-secondary` |
| Emergency button | Alert red fill | `.btn-danger` |
| Text link | Berry, underline offset 4 | `.link` |
| Field | Label above (15px/600), 52px input, 1.5px `field` border; hint 14px muted; error 14px alert, says how to fix | `Field`, `.input` |
| Specialty chip | Full radius, 1.5px `line`; selected = blush + berry border + "✓" | `FilterChip`, `.chip` |
| Doctor card | Round blush initials avatar, name 20/600, specialty · years, clinic; tags on `surface`; Book + View profile split | `DoctorCard` |
| Time slot picker | Day buttons 64px (selected = berry fill); slots 48px (selected = blush + ✓), grouped Morning / Afternoon | `.day`, `.slot`, `BookingPanel` |
| Notices | Soft tint + 1px tinted border + icon + bold lead | `Notice`, `ErrorAlert` |
| Status | Colour + icon + word on a soft pill | `StatusBadge` |

## Booking flow
Five steps, under two minutes. Progress reads "Step 3 of 5 · Pick a time". Back never clears what the patient typed. Show availability before asking anyone to sign in.

1. **Find care** — search by doctor, specialty or symptom. Emergency link always visible.
2. **Choose doctor** — cards show next date, fee and visit type. Filter, don't paginate.
3. **Pick a time** — open on the earliest free day. Hold the slot 10 minutes and say so.
4. **Your details** — only what's needed. "Myself" or "Someone else". Guest booking allowed.
5. **Confirm** — summary, add to calendar, directions, reschedule or cancel links.

## Do / don't
- **Do:** keep most of each screen white and use berry for the one main action · write like a kind nurse ("Your appointment is Tue, 4 Nov at 9:30 AM.") · show total cost and HMO coverage before the patient confirms · use real, warm photos of staff and spaces, with consent.
- **Don't:** add bright accents, gradients, heavy shadows or decorative patterns · use medical jargon ("OPD consult") without a plain explanation · force sign-up before showing available times · use countdowns or fake scarcity, or hide the cancel link.

## Accessibility · responsive · trust
- Text contrast ≥ 4.5:1. Targets ≥ 48×48px, 8px apart. Keyboard and screen reader for every step. 200% zoom; respects reduced motion. Status = colour + icon + word.
- Mobile-first at 390px. Hero stacks: text above image. Nav collapses to a menu button. Main action sticks to the bottom. Tap-to-call on every phone number.
- Show licence number and specialty board. Explain why each sensitive field is asked. Link the privacy notice at the details step. Never show symptoms in notifications. Confirm by SMS with a reference code.

## Motion
Motion is soft and short. It confirms what the patient did or shows what just appeared. It never decorates, never loops, and never delays a task. Tokens live in `frontend/tailwind.config.js` (`transitionDuration`, `transitionTimingFunction`, `keyframes`, `animation`); classes live in `frontend/src/index.css`.

| Token | Value | Use |
|---|---|---|
| `duration-fast` | 120ms | Colour and press feedback on buttons, chips, slots, inputs |
| `duration-base` (default) | 200ms | Card hover lift, icon and arrow nudges |
| `duration-slow` | 320ms | Entrances and the booking progress bar |
| `ease-out` (default) | cubic-bezier(0.2, 0, 0, 1) | Everything that enters or responds |
| `ease-in` | cubic-bezier(0.4, 0, 1, 1) | Reserved for exits |

| Pattern | Spec | Where |
|---|---|---|
| Press | Buttons scale to 0.98 while held; chips, days and slots to 0.97 | `.btn`, `.chip`, `.day`, `.slot` |
| Hover lift | Link cards rise 2px, border turns berry, shadow deepens (`shadow-card-hover`); they settle on press. Hover only on devices that can hover (`hoverOnlyWhenSupported`) | `.card-link` (specialty tiles, appointment rows) |
| Primary hover | Berry darkens and the shadow deepens (`shadow-button-hover`) | `.btn-primary` |
| Selection | The ✓ on a selected chip or slot pops in (scale 0.6 → 1.15 → 1, 240ms) | `.check-pop` |
| Page entrance | Each new route fades in and rises 8px (320ms). Filter and paging changes don't replay it | `Layout` (`.reveal`, keyed by pathname) |
| List entrance | Cards rise in with a 40ms stagger, capped at 8 items (≤ 320ms extra) | `stagger(i)` in `ui.tsx`: doctor cards, hospitals, specialties, appointments |
| Revealed step | The booking details step and new notices or errors rise in | `.reveal` on `BookingPanel` details, `Notice`, `ErrorAlert` |
| Refreshed content | Time slots fade in (200ms) when the day or visit type changes | `animate-fade` in `BookingPanel` |
| Menus | The mobile menu drops 6px and fades in (200ms) | `animate-drop` |
| Counters | The unread badge pops when its number changes | `Layout` |
| Progress | Booking progress segments fill over 320ms | `BookingPanel` |

Rules:
- Animate only `opacity`, `transform`, colours and shadows; never layout properties (height, width, top).
- Entrances use `backwards` fill, so nothing lingers after the animation and hover transforms on the same element still work.
- Nothing moves for longer than 320ms, plus at most 320ms of stagger. No looping motion except the loading spinner.
- `prefers-reduced-motion: reduce` turns every animation and transition into an instant change and removes stagger delays (`index.css` base layer). Content must never depend on an animation to become visible.

## Header pattern (homepage board)
Utility bar on `surface` (opening info left; account links and "Emergency 24/7: 115" tap-to-call right) → white header with berry logo tile, main nav and a "Book appointment" button, 1px `line` underneath.

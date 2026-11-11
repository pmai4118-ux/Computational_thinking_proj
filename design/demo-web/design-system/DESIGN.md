---
name: Luminous Violet Glass
colors:
  surface: '#faf9fe'
  surface-dim: '#dad9de'
  surface-bright: '#faf9fe'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f4f3f8'
  surface-container: '#eeedf2'
  surface-container-high: '#e8e7ec'
  surface-container-highest: '#e3e2e7'
  on-surface: '#1a1c1f'
  on-surface-variant: '#4a4455'
  inverse-surface: '#2f3034'
  inverse-on-surface: '#f1f0f5'
  outline: '#7b7487'
  outline-variant: '#ccc3d8'
  surface-tint: '#732ee4'
  primary: '#630ed4'
  on-primary: '#ffffff'
  primary-container: '#7c3aed'
  on-primary-container: '#ede0ff'
  inverse-primary: '#d2bbff'
  secondary: '#6b38d4'
  on-secondary: '#ffffff'
  secondary-container: '#8455ef'
  on-secondary-container: '#fffbff'
  tertiary: '#4f4b6c'
  on-tertiary: '#ffffff'
  tertiary-container: '#686385'
  on-tertiary-container: '#e9e2ff'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#eaddff'
  primary-fixed-dim: '#d2bbff'
  on-primary-fixed: '#25005a'
  on-primary-fixed-variant: '#5a00c6'
  secondary-fixed: '#e9ddff'
  secondary-fixed-dim: '#d0bcff'
  on-secondary-fixed: '#23005c'
  on-secondary-fixed-variant: '#5516be'
  tertiary-fixed: '#e5deff'
  tertiary-fixed-dim: '#c8c2e9'
  on-tertiary-fixed: '#1b1735'
  on-tertiary-fixed-variant: '#474363'
  background: '#faf9fe'
  on-background: '#1a1c1f'
  surface-variant: '#e3e2e7'
typography:
  display-hero:
    fontFamily: Plus Jakarta Sans
    fontSize: 56px
    fontWeight: '800'
    lineHeight: 64px
    letterSpacing: -0.03em
  display-hero-mobile:
    fontFamily: Plus Jakarta Sans
    fontSize: 38px
    fontWeight: '800'
    lineHeight: 46px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 36px
    fontWeight: '700'
    lineHeight: 44px
    letterSpacing: -0.025em
  headline-lg-mobile:
    fontFamily: Plus Jakarta Sans
    fontSize: 28px
    fontWeight: '700'
    lineHeight: 36px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 26px
    fontWeight: '600'
    lineHeight: 34px
    letterSpacing: -0.02em
  headline-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.015em
  title-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 17px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 17px
    fontWeight: '400'
    lineHeight: 26px
  body-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 15px
    fontWeight: '400'
    lineHeight: 22px
  body-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
  label-md:
    fontFamily: Space Grotesk
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.04em
  label-sm:
    fontFamily: Space Grotesk
    fontSize: 10px
    fontWeight: '700'
    lineHeight: 14px
    letterSpacing: 0.06em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1.5rem
  gutter-mobile: 1rem
  margin: 3rem
  margin-tablet: 2rem
  margin-mobile: 1.25rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2.5rem
---

## Brand & Style

This design system establishes a high-clarity, luminous educational interface engineered for high-stakes interview preparation. It merges ethereal modern glassmorphism with rigorous editorial precision. The aesthetic dispels academic monotony through translucent, multi-layered crystalline surfaces, soft chromatic refractions, and focused violet energy.

### Aesthetic Principles
- **Luminous Transparency:** Interfaces feel weightless and illuminated from within. Frosted layers stack logically to indicate hierarchy, depth, and spatial nesting without heavy solid container shapes.
- **Electric Focus:** Vibrancy is concentrated purely within the violet spectrum. High-intensity violet guides primary attention and progress markers, balanced by delicate lavender-tinted surfaces.
- **Specular Refraction:** Micro-details mimic optical glass—crisp light catching on top and left borders, gentle drop shadows tinted with faint ultraviolet, and diffused backdrop blur.
- **Academic Serenity:** Whitespace is treated as quiet airspace. The lavender off-white canvas reduces eye strain across lengthy mock interview sessions, code reviews, and structured video analysis.

## Colors

The palette is strictly calibrated around high-fidelity violets, frosted whites, and obsidian text tones. Competing hues are omitted to reinforce absolute institutional focus.

### Palette Architecture
- **Primary (`#7C3AED`):** Electric Violet. Applied to critical interactive targets, active states, progress indicators, and high-visibility badges.
- **Secondary (`#8B5CF6`):** Vivid Amethyst. Used for hover transitions, focal emphasis, and decorative gradient endpoints.
- **Tertiary (`#DDD6FE`):** Soft Lilac Frost. Serves as ambient highlight zones, delicate tags, subtle active chips, and glass edge flares.
- **Neutral Canvas (`#F8F7FC`):** Pale Lavender Mist. Provides an optically warm, non-glare atmospheric foundation with violet undertones.
- **Text & Contrast:**
  - Primary Typography: Deep Obsidian (`#1E1B2E`) for near-black readability.
  - Secondary Typography: Softened Slate Violet (`#5B5474`) for secondary metadata and hierarchy.
  - Borders & Specular Edges: Semi-transparent white (`rgba(255, 255, 255, 0.9)`) backed by subtle violet borders (`rgba(124, 58, 237, 0.12)`).

## Typography

The typographic hierarchy balances modern geometric friendliness with technical structure. 

- **Primary & Body (`Plus Jakarta Sans`):** Chosen for its tall x-height, pristine legibility, and refined curves. It ensures long-form reading during problem prompts and behavioral rubrics is fatigue-free.
- **Labels & System Meta (`Space Grotesk`):** Provides a crisp, technical cadence for metrics, countdown timers, category chips, and analytical status fields. Its geometric construction evokes performance and computational precision.
- **Pairing Rule:** Use uppercase treatment with loosened tracking for `label-sm` and `label-md` to denote tags, metadata categories, and status alerts.

## Layout & Spacing

The layout operates on a fluid 12-column grid structured around generous negative space to reinforce the open, ethereal quality of glass planes.

### Layout Grid Rules
- **Desktop (1200px+):** 12 columns with `1.5rem` gutters and a max content container width of `1280px` centered within a `3rem` canvas margin.
- **Tablet (768px - 1199px):** 8 columns with `1.25rem` gutters and `2rem` side margins. Floating utility sidebars tuck into bottom drawers or collapsible translucent side-sheets.
- **Mobile (Below 768px):** 4 columns with `1rem` gutters and `1.25rem` screen edge margins. Multi-column interview question and video review cards collapse into stacked vertical glass tiles.
- **Breathing Room:** Glass containers must not touch; maintain at least `space-md` (`1rem`) between card surfaces to allow the background ambient atmosphere and light refractions to separate planar boundaries clearly.

## Elevation & Depth

Visual hierarchy is constructed via optical glass simulation rather than opaque drop shadows. Elevation is conveyed by stacking blur intensities, white specular highlights, and chromatic violet shadowing.

### Surface Elevation Tiers
1. **Tier 0 (Base Canvas):** Solid pale lavender tint (`#F8F7FC`). May feature ambient, soft radial violet glows (`rgba(124, 58, 237, 0.06)`) positioned in corners to fuel the glass refractions above.
2. **Tier 1 (Resting Glass Cards & Panels):** 
   - Fill: `rgba(255, 255, 255, 0.72)`
   - Blur: `backdrop-filter: blur(16px)`
   - Border: `1px solid rgba(255, 255, 255, 0.9)` on top/left edges blending to `rgba(221, 214, 254, 0.5)` on bottom/right edges.
   - Shadow: `0 8px 32px -4px rgba(124, 58, 237, 0.05), 0 2px 8px -1px rgba(30, 27, 46, 0.03)`
3. **Tier 2 (Hovered Cards & Interactive Flyouts):**
   - Fill: `rgba(255, 255, 255, 0.84)`
   - Blur: `backdrop-filter: blur(20px)`
   - Border: `1px solid rgba(255, 255, 255, 1)`
   - Shadow: `0 16px 40px -6px rgba(124, 58, 237, 0.12), 0 4px 16px -2px rgba(30, 27, 46, 0.04)`
4. **Tier 3 (Modals, Overlays & Command Bars):**
   - Backdrop Scrim: `rgba(248, 247, 252, 0.45)` with `backdrop-filter: blur(8px)`
   - Modal Fill: `rgba(255, 255, 255, 0.92)`
   - Blur: `backdrop-filter: blur(28px)`
   - Border: `1px solid rgba(255, 255, 255, 1)` with an internal glow `inset 0 1px 1px 0 rgba(255, 255, 255, 1)`
   - Shadow: `0 24px 64px -8px rgba(124, 58, 237, 0.18), 0 8px 24px -4px rgba(30, 27, 46, 0.06)`

## Shapes

The geometric framework employs medium-rounded contours to mimic ground optical glass lenses.

- **Standard Elements (`rounded` / 0.5rem / 8px):** Inputs, interactive list entries, code blocks, and granular dropdown menus.
- **Containers & Surfaces (`rounded-lg` / 1.0rem / 16px):** Metric panels, mock interview question panes, video preview pods, and modals.
- **Hero & Primary Shells (`rounded-xl` / 1.5rem / 24px):** Large dashboard viewports, stage layout cards, and multi-step scenario containers.
- **Pill Architecture (`9999px`):** Reserved exclusively for status indicators, tag badges, and standalone circular floating actions.

## Components

### Buttons
- **Primary:** Gradient fill `linear-gradient(135deg, #7C3AED, #8B5CF6)`, crisp `1px solid rgba(255, 255, 255, 0.3)` inner rim, text `#FFFFFF`. Shadow: `0 4px 14px rgba(124, 58, 237, 0.35)`. Hover: scale `1.01`, box shadow increases in violet spread.
- **Glass / Secondary:** Background `rgba(255, 255, 255, 0.65)`, backdrop blur `12px`, border `1px solid rgba(255, 255, 255, 0.9)`, text `#1E1B2E`. Hover: Background shifts to `rgba(237, 233, 254, 0.7)`, border tint shifts to `#DDD6FE`.
- **Ghost:** Transparent background, text `#7C3AED`, rounded geometry. Hover: `rgba(124, 58, 237, 0.06)`.

### Chips & Badges
- **Status / Category Chips:** Background `rgba(237, 233, 254, 0.6)`, backdrop blur `8px`, border `1px solid rgba(221, 214, 254, 0.8)`, text `#7C3AED`, font token `label-md`.
- **Selected Filter Chip:** Background `#7C3AED`, text `#FFFFFF`, border `1px solid rgba(255, 255, 255, 0.4)`.

### Input Fields
- **Default State:** Background `rgba(255, 255, 255, 0.6)`, backdrop blur `12px`, border `1px solid rgba(221, 214, 254, 0.6)`, text `#1E1B2E`, placeholder `#5B5474` at 60% opacity.
- **Focus State:** Background `rgba(255, 255, 255, 0.95)`, border `1px solid #7C3AED`, shadow ring `0 0 0 3px rgba(124, 58, 237, 0.15)`.

### Checkboxes & Radio Buttons
- **Unchecked:** Border `1.5px solid rgba(124, 58, 237, 0.3)`, background `rgba(255, 255, 255, 0.5)`.
- **Checked:** Background `#7C3AED`, border `1.5px solid #7C3AED`, checkmark/dot `#FFFFFF`. Dynamic glow: `0 0 8px rgba(124, 58, 237, 0.3)`.

### Cards & Panels
- **Standard Card:** Translucent frosted white `rgba(255, 255, 255, 0.75)`, `backdrop-filter: blur(16px)`, border `1px solid rgba(255, 255, 255, 0.85)`, border-radius `1.0rem`.
- **Active / Focused Interview Card:** Background `rgba(255, 255, 255, 0.88)`, border `1.5px solid #7C3AED`, diffuse lavender shadow.

### Domain-Specific Components
- **Mock Interview Teleprompter Card:** Glass surface pinned above the interface, top border accentuated with an intense specular highlight `linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.9) 50%, transparent)`, providing a crisp optical shelf.
- **Audio / AI Feedback Meter:** Segmented waveform bars using `#7C3AED` for active levels and `rgba(124, 58, 237, 0.15)` for empty states over a frosted glass track.
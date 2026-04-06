# Design System Strategy: High-End Real Estate Editorial



## 1. Overview & Creative North Star

**Creative North Star: "The Architectural Curator"**



This design system is built to evoke the feeling of a high-end luxury architectural digest. We are moving away from the "app-like" density of traditional real estate portals toward a curated, editorial experience. The interface should feel like a quiet, expensive physical space—trustworthy, authoritative, and spacious.



To break the "template" look, we utilize **Intentional Asymmetry**. This means hero images may bleed off one edge of the screen while typography sits anchored to a generous internal margin. We favor high-contrast typography scales and overlapping elements (e.g., a property title in `notoSerif` partially overlapping a high-resolution image container) to create a sense of bespoke craftsmanship rather than a rigid, automated grid.



---



## 2. Colors: Depth and Sophistication

Our palette is anchored in deep oceanic blues and charcoals, punctuated by refined gold accents.



* **Primary (`#00152a`) & Primary Container (`#102a43`):** These represent our "Charcoal and Deep Blue" base. Use these for high-authority sections or full-bleed editorial backgrounds.

* **Tertiary Fixed (`#ffdf9a`) & Tertiary Fixed Dim (`#ebc15f`):** Our "Gold Accents." Use these sparingly for precision elements like price tags, premium badges, or active states.

* **The "No-Line" Rule:** Explicitly prohibit 1px solid borders for sectioning. Boundaries must be defined solely through background color shifts. For example, a property feature list in `surface-container-low` (`#eef4ff`) sitting on a `background` (`#f8f9ff`) provides enough contrast to define a zone without the visual clutter of a stroke.

* **The "Glass & Gradient" Rule:** To provide "soul," use subtle gradients. Transitioning from `primary` to `primary_container` on a call-to-action card creates a sense of volume. For floating navigation or search bars, use **Glassmorphism**: a background of `surface` at 70% opacity with a `backdrop-filter: blur(20px)`.



---



## 3. Typography: The Editorial Voice

We use a high-contrast pairing to balance tradition with modernity.



* **The Serif (Noto Serif):** Used for all `display` and `headline` roles. This is our "Editorial" voice. It communicates heritage, trust, and luxury. Large `display-lg` headings should use tighter letter-spacing to feel like a premium magazine masthead.

* **The Sans-Serif (Manrope):** Used for `title`, `body`, and `label` roles. Manrope’s geometric but warm nature ensures that property data and descriptions remain highly legible and "Modern."

* **Scale Usage:** Use `display-lg` (3.5rem) for hero property titles and `headline-sm` (1.5rem) for section introductions. The jump between scales should be dramatic to emphasize hierarchy.



---



## 4. Elevation & Depth: Tonal Layering

Traditional shadows are often too "heavy" for a sophisticated aesthetic. We achieve depth through the **Layering Principle**.



* **Tonal Stacking:** Instead of shadows, stack surface tiers. Place a `surface-container-lowest` (`#ffffff`) card on a `surface-container` (`#e4efff`) background to create a "lifted" effect.

* **Ambient Shadows:** If a floating effect is required (e.g., a "Book Viewing" modal), use a shadow color tinted with the primary hue: `rgba(1, 29, 53, 0.06)` with a 40px blur. This mimics natural light passing through a premium space.

* **The "Ghost Border":** If a container requires definition against a similar background, use `outline_variant` at 20% opacity. Never use 100% opaque borders.

* **Glassmorphism:** Use semi-transparent `surface` containers for interactive overlays. This allows the high-end property photography to "bleed" through the UI, making the site feel immersive and integrated.



---



## 5. Components



### Buttons

* **Primary:** Background of `primary` (`#00152a`), text `on_primary`. Shape: `md` (0.375rem).

* **Secondary:** Glass-style. Background `surface` at 10% opacity with a `ghost border`.

* **Tertiary (Gold):** Use `tertiary_fixed_dim` for "Exclusive" or "VIP" actions only.



### Property Cards

* **Structure:** No dividers. Use `surface_container_lowest` for the card body.

* **Imagery:** Aspect ratio 4:5 or 16:9. No border-radius on the top corners to maintain "Clean Lines."

* **Typography:** Property name in `title-lg` (Manrope), price in `headline-sm` (Noto Serif).



### Input Fields (Search & Filtering)

* **Style:** Minimalist. No bottom line or box. Use `surface_container_low` as a subtle background fill.

* **Focus:** Transition the background to `surface_container_high` and add a 1px `tertiary` (Gold) bottom-only accent.



### Chips (Property Tags)

* **Style:** `label-md` uppercase with generous letter spacing.

* **Color:** `secondary_container` with `on_secondary_container` text. Use for "New Listing" or "Penthouse."



---



## 6. Do's and Don'ts



### Do:

* **Use Whitespace as a Luxury:** Give elements 2x more breathing room than you think they need.

* **Lead with Imagery:** The property is the hero; the UI is the frame.

* **Align to a Baseline:** Ensure serif headings and sans-serif body text feel anchored to a common vertical rhythm.



### Don't:

* **No Dividers:** Never use a horizontal line to separate content. Use a background shift to `surface_container` instead.

* **No Pure Black:** Use `primary` (`#00152a`) or `on_surface` (`#011d35`) for text. Pure black (#000) feels "cheap" and digital; our deep blues feel "inked" and professional.

* **No Standard Rounds:** Avoid the `full` pill-shape for main containers. Stick to `md` (0.375rem) or `lg` (0.5rem) to keep the "Clean Lines" requested.
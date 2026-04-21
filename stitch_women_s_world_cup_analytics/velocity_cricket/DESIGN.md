# Design System Documentation: The Kinetic Analyst

## 1. Overview & Creative North Star
The North Star for this design system is **"The Kinetic Analyst."** 

In the world of Women’s World Cup cricket, the data is fast, high-stakes, and elite. We are moving away from the "SaaS-dashboard-in-a-box" look. Instead, we are leaning into a high-end editorial experience that feels more like a premium sports journal than a spreadsheet. 

We achieve this through **Intentional Asymmetry** and **Tonal Depth**. By breaking the rigid 12-column grid with overlapping elements—such as a player’s silhouette breaking the frame of a data card—we create a sense of movement. This system prioritizes breathing room and sophisticated layering to ensure that even the most complex data sets feel authoritative and accessible.

---

## 2. Colors & Surface Architecture
The palette is anchored in a deep, nocturnal Navy (`#0b1326`), punctuated by the electric precision of Vibrant Teal (`#43ecdb`) and the high-energy pulse of Pink (`#ffb2ba`).

### The "No-Line" Rule
**Strict Mandate:** Designers are prohibited from using 1px solid borders to define sections or containers. 
Structure must be achieved through:
- **Background Color Shifts:** Use `surface-container-low` for secondary information sitting on a `surface` background.
- **Tonal Transitions:** Use subtle shifts in the Material surface tiers to imply boundaries.

### Surface Hierarchy & Nesting
Think of the UI as physical layers of frosted glass. 
- **Base:** `surface` (#0b1326)
- **Primary Layout Blocks:** `surface-container-low` (#131b2e)
- **Active Data Cards:** `surface-container-high` (#222a3d)
- **Interacted/Floating Elements:** `surface-container-highest` (#2d3449)

### The "Glass & Gradient" Rule
To elevate the "Modern" feel, use **Glassmorphism** for floating overlays (e.g., player stat tooltips). Utilize `surface_variant` with a 60% opacity and a `backdrop-blur` of 12px to allow the deep navy background to bleed through. 
**Signature Texture:** Main CTAs or victory-state cards should use a subtle linear gradient from `secondary` (#43ecdb) to `secondary_container` (#00cfbf) at a 135-degree angle.

---

## 3. Typography
We utilize a high-contrast pairing of **Manrope** (for editorial impact) and **Inter** (for data precision).

*   **Display & Headlines (Manrope):** These are your "Announcers." Use `display-lg` to `headline-sm` for scorelines and major milestones. The geometric nature of Manrope conveys modern authority.
*   **Titles & Body (Inter):** These are your "Analysts." Use `title-md` for card headers and `body-md` for player bios. Inter’s high x-height ensures readability even at the smallest `label-sm` sizes in dense bowling economy charts.
*   **Hierarchy Tip:** Never center-align data. Align headlines to the left to create a strong "edge" that guides the eye through complex statistics.

---

## 4. Elevation & Depth
In this system, depth is a result of light and shadow, not lines.

*   **The Layering Principle:** Stacking is key. A `surface-container-lowest` card placed on a `surface-container-low` section creates a natural "recessed" look. Conversely, placing a `surface-container-highest` card on a `surface` background creates an immediate focal point.
*   **Ambient Shadows:** For floating elements (Modals/Popovers), use an extra-diffused shadow: `0px 24px 48px rgba(6, 14, 32, 0.4)`. The shadow must be a tinted version of the background, never pure black.
*   **The "Ghost Border" Fallback:** If a boundary is required for accessibility, use the `outline_variant` token at **15% opacity**. This creates a "whisper" of a line that defines space without cluttering the visual field.

---

## 5. Components

### Buttons
*   **Primary:** High-energy. Background: `secondary` (#43ecdb), Text: `on_secondary`. Use `xl` (0.75rem) roundedness.
*   **Secondary:** Ghost style. Background: Transparent, Border: Ghost Border (15% `outline_variant`), Text: `secondary`.
*   **Tertiary:** Energetic. Text: `tertiary` (#ffb2ba). No background, used for "View Full Match History."

### Data Visualization (Signature Component)
*   **Intensity Gauges:** Use `secondary` (Teal) for positive performance (Strike Rate) and `tertiary` (Pink) for aggressive metrics (Wickets/Boundaries).
*   **Forbid Dividers:** Do not use lines between list items. Use 16px of vertical spacing and a `surface-container-low` hover state to separate "Batsman" entries in a scorecard.

### Cards
*   **Layout:** Cards should never be perfectly symmetrical. Use a heavier padding on the left (24px) than the right (16px) to create an editorial "pull."
*   **Background:** Use `surface_container_high`.

### Input Fields
*   **State:** Default state should be `surface_container_highest` with no border. On focus, transition to a `secondary` (Teal) "Ghost Border."

---

## 6. Do's and Don'ts

### Do:
*   **Do** use `tertiary` (Pink) as a "high-energy" accent only—save it for key moments like a "Wicket" alert or a "Live" badge.
*   **Do** lean into `surface-bright` for highlights in bar charts to make the data pop against the navy.
*   **Do** leave generous white space (32px+) between major sections to maintain an "Authoritative" feel.

### Don't:
*   **Don't** use 100% opaque `outline` tokens. They are too "heavy" for this high-end aesthetic.
*   **Don't** use "Drop Shadows" on flat cards sitting in the layout. Reserve shadows only for elements that truly "float" (Modals).
*   **Don't** use standard "Success Green" or "Warning Yellow." Use `secondary` for success and `tertiary` for warnings to keep the brand identity intact.

---
**Director’s Final Note:** 
Remember, we are telling the story of the game. If the layout feels too "safe" or "boxed in," strip away a container and use a Manrope `display-md` headline to command the space instead. Confidence is our best design tool.
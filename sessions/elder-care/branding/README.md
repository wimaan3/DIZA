# DIZA animated branding

The animated and static SVGs in `../web/branding/` are copied byte-for-byte from the user-provided `diza-logo.zip`.
Use `logoDark` on dark backgrounds and `logoLight` on light backgrounds.
`logo.js` exports Vite-managed asset URLs and imports the shared sizing rules.
The original SVGs provide the blinking eyes, bobbing mascot, antenna movement and pulsing waves.
A picture source explicitly selects the supplied static SVG when `prefers-reduced-motion` is enabled.
This also handles browsers that do not update embedded SVG animation rules when the preference changes.
The SVGs use outlined wordmarks, so they do not depend on downloaded fonts.
The source archive remains untouched.

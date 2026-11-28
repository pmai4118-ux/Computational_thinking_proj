# Stitch homepage

Imported from `D:/stitch_ct_nh_m_5 (3).zip`. Source file bytes are preserved;
`rename-manifest.json` records the original paths, English paths and SHA-256 hashes.

- `homepage.html`: original HTML design.
- `homepage.png`: original screenshot.
- `design-system/DESIGN.md`: original design notes, treated as reference material.

The application ports the main HTML to `source/view/templates/welcome.html`, using
the supplied violet palette, glass cards and spacing. Per the follow-up request,
the homepage uses the same header, navigation and Be Vietnam Pro typography as the
other tabs. The floating Luminous Glass utility bar is removed. Light/dark controls
live in the shared header and persist across routes using `interviewus.theme`.

Per the user's request, the statistics strip and all illustrative numerical claims
are removed. The console is labeled as an illustration; it shows no fabricated
score. Copy describes text answers, rubric feedback and the Java Backend roadmap.
No microphone, fake account, notification, or standalone alternate-question flow
is introduced. Buttons open the existing clarification, interview and learning pages.

CSS is compiled locally, scoped to `.homepage-shell`; the app does not load the
Tailwind CDN. To rebuild after editing the template:

```powershell
npm.cmd exec --yes --cache .local/npm-cache --package tailwindcss@3.4.17 -- tailwindcss -c scripts/homepage/tailwind.config.cjs -i scripts/homepage/input.css -o source/view/static/css/homepage.utilities.css --minify
```

`scripts/port_homepage.py` documents the initial source conversion. Running it
regenerates the template and build configuration; subsequent hand edits should be
reviewed before rerunning it.

Computational thinking: decompose into hero, illustration, feature cards and CTA;
recognize shared navigation/route patterns; abstract design tokens from the source;
map each action deterministically to the existing route without adding AI calls.

# Daylight

A calm, responsive personal planner built with React, TypeScript, and Vite.

## Develop

Requires Node.js 22.12+ (Node.js 24 is recommended).

```sh
npm ci
npm run dev
```

The development server listens on port 5173. On machines where the home directory is read-only, use `npm ci --cache /tmp/daylight-npm-cache`.

## Check

```sh
npm run build
npm test
```

Browser tests use `/usr/bin/chromium` when available. Otherwise, install the matching browser with `npx playwright install chromium`, or set `CHROMIUM_PATH` to a Chromium executable. The test runner starts Vite automatically.

## Use

- Add timed tasks, choose a category, and attach a note. Press **N** to add a task.
- Tick tasks complete, or untick them to reopen them. Click a title to edit; the three-dot menu also offers deletion with undo.
- Switch between day and week views and navigate dates in the calendar.
- Keep notes for each day and run a 15-, 25-, 45-, or 60-minute focus session.
- Personalize your name and focus duration in settings, and export a JSON backup.

The first day includes editable example tasks. Tasks, notes, and preferences are saved in this browser's local storage. Data is specific to the device and browser; there is no account, cloud synchronization, or backend. Focus timers run while the page is open and calculate remaining time from a deadline to stay accurate in background tabs; a page reload resets the timer. Export is a downloadable backup; automatic import is not part of this version.

Fonts and icons are bundled locally. No API keys or external services are required.

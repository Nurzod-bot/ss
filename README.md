# Daylight

A dark, aviation-inspired daily habit tracker built with React, TypeScript, and Vite. Includes locally bundled fighter-jet artwork and fonts, a daily checklist, weekly tracking, notes, and a fixed 30-minute focus timer.

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
npm test -- --workers=2
```

Browser tests use `/usr/bin/chromium` when available. Otherwise, install the matching browser with `npx playwright install chromium`, or set `CHROMIUM_PATH` to a Chromium executable. The test runner starts Vite automatically.

## Daily routine

Every date has its own checklist, with no hours or time slots:

1. Fish oil intake
2. Creatine intake
3. Gym
4. Chinese language practice
5. Code practice
6. A few pages of a book

- Tick any habit on or off. Checkmarks are saved separately for each date.
- Today automatically rolls into a fresh checklist at midnight in your browser's local timezone. Earlier dates keep their checkmarks.
- Switch to Week to see and update each day's checkmarks side by side.
- Click a habit's title to edit it. Press **N** to add a habit that repeats from the selected day forward. Removing a habit affects the selected date and later dates, preserving earlier progress; the notification offers undo.
- Completing every active habit counts as a complete day. Consecutive complete days build a streak. Today does not break yesterday's streak until the day ends.
- Run a 30-minute focus session. Pause, resume, and reset are supported, and completed sessions are counted for the date they finish. Reloading resets a running timer.
- Keep separate daily notes and export a JSON backup in settings.

## Saved data

Data is saved in this browser on this device using local storage (`daylight-planner-v2`). There is no account, backend, or synchronization between devices. JSON export is a downloadable backup; automatic import is not part of this version.

The previous timed planner is migrated automatically: its name and daily notes are carried forward, the complete original plan is retained in `previousPlan` for exports, and its original `daylight-planner-v1` storage key is left untouched. The new routine starts with unchecked habits, and its timer is always 30 minutes, including after migration. Unreadable stored data is never overwritten until the user explicitly backs it up and starts fresh.

All artwork, fonts, and icons are bundled locally. No API keys or external services are required. The aviation artwork was generated for this app.

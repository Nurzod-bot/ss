import { test, expect } from "@playwright/test";

const titles = [
  "Fish oil intake",
  "Creatine intake",
  "Gym",
  "Chinese language practice",
  "Code practice",
  "A few pages of a book",
];
const key = "daylight-planner-v2";

test.beforeEach(async ({ page }) => {
  await page.clock.install({ time: new Date("2026-10-15T10:00:00+05:00") });
  await page.goto("/");
});

test("the six requested habits repeat every day without hours", async ({
  page,
}) => {
  await expect(page.locator(".habit-card")).toHaveCount(6);
  for (const title of titles)
    await expect(
      page.getByRole("checkbox", {
        name: `Mark complete: ${title}`,
        exact: true,
      }),
    ).toHaveAttribute("aria-checked", "false");
  await expect(page.getByRole("timer")).toHaveText("30:00");
  await expect(
    page.locator("input[type=time], .time-label, .task-duration"),
  ).toHaveCount(0);
  await page.getByRole("button", { name: "Next day", exact: true }).click();
  await expect(page.locator(".habit-card")).toHaveCount(6);
  await expect(page.getByLabel("Choose date")).toHaveValue("2026-10-16");
  await expect(page.locator(".habit-check.checked")).toHaveCount(0);
  await expect(page.locator(".stat-card").first()).toContainText("0 / 6");
});

test("completion ticks work both ways, persist, and stay separate per day", async ({
  page,
}) => {
  await page
    .getByRole("checkbox", { name: "Mark complete: Gym", exact: true })
    .click();
  await expect(page.locator(".stat-card").first()).toContainText("1 / 6");
  await page.reload();
  await expect(
    page.getByRole("checkbox", { name: "Mark incomplete: Gym", exact: true }),
  ).toHaveAttribute("aria-checked", "true");
  await page.getByRole("button", { name: "Next day", exact: true }).click();
  await expect(
    page.getByRole("checkbox", { name: "Mark complete: Gym", exact: true }),
  ).toHaveAttribute("aria-checked", "false");
  await page.getByRole("button", { name: "Previous day", exact: true }).click();
  await page
    .getByRole("checkbox", { name: "Mark incomplete: Gym", exact: true })
    .click();
  await expect(page.locator(".stat-card").first()).toContainText("0 / 6");
});

test("an open planner rolls into a fresh day at midnight and keeps yesterday", async ({
  page,
}) => {
  await page.clock.setSystemTime(new Date("2026-10-15T23:59:50+05:00"));
  await page
    .getByRole("checkbox", {
      name: "Mark complete: Fish oil intake",
      exact: true,
    })
    .click();
  await page.clock.fastForward(20_000);
  await expect(page.getByLabel("Choose date")).toHaveValue("2026-10-16");
  await expect(page.locator(".habit-card")).toHaveCount(6);
  await expect(page.locator(".habit-check.checked")).toHaveCount(0);
  await page.getByRole("button", { name: "Previous day", exact: true }).click();
  await expect(
    page.getByRole("checkbox", {
      name: "Mark incomplete: Fish oil intake",
      exact: true,
    }),
  ).toHaveAttribute("aria-checked", "true");
});

test("weekly checkboxes track any date and a full day builds the streak", async ({
  page,
}) => {
  for (const title of titles)
    await page
      .getByRole("checkbox", { name: `Mark complete: ${title}`, exact: true })
      .click();
  await expect(page.locator(".stat-card").nth(1)).toContainText("1 day");
  await expect(page.locator(".stat-card").nth(2)).toContainText("100%");
  await page.getByRole("button", { name: "Week", exact: true }).click();
  await expect(
    page.locator(".week-table tbody").getByRole("checkbox"),
  ).toHaveCount(42);
  await page
    .getByRole("checkbox", {
      name: "Mark complete: Gym on Oct 16",
      exact: true,
    })
    .click();
  await page
    .getByRole("button", { name: "Open Friday, October 16", exact: true })
    .click();
  await expect(
    page.getByRole("checkbox", { name: "Mark incomplete: Gym", exact: true }),
  ).toHaveAttribute("aria-checked", "true");
  await expect(page.locator(".stat-card").first()).toContainText("1 / 6");
});

test("new habits repeat, can be edited, and have no time inputs", async ({
  page,
}) => {
  await page.getByRole("button", { name: /^Add habit/ }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog.locator("input[type=time]")).toHaveCount(0);
  await dialog.getByLabel("Habit name").fill("Evening walk");
  await dialog.getByRole("button", { name: "Health", exact: true }).click();
  await dialog.getByLabel("A reminder").fill("Get some fresh air.");
  await dialog.getByRole("button", { name: "Add to routine" }).click();
  await page.getByRole("button", { name: "Evening walk", exact: true }).click();
  await dialog.getByLabel("Habit name").fill("A little fresh air");
  await dialog.getByRole("button", { name: "Save changes" }).click();
  await page.getByRole("button", { name: "Next day", exact: true }).click();
  await expect(
    page.getByRole("checkbox", {
      name: "Mark complete: A little fresh air",
      exact: true,
    }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Previous day", exact: true }).click();
  await page.getByRole("button", { name: "Previous day", exact: true }).click();
  await expect(page.locator(".habit-card")).toHaveCount(6);
  await page.reload();
  await expect(page.locator(".habit-card")).toHaveCount(7);
});

test("removal can be undone and preserves checkmarks on earlier dates", async ({
  page,
}) => {
  await page.getByRole("button", { name: "Previous day", exact: true }).click();
  await page
    .getByRole("checkbox", { name: "Mark complete: Gym", exact: true })
    .click();
  await page.getByRole("button", { name: "Today", exact: true }).click();
  await page
    .getByRole("button", { name: "Options for Gym", exact: true })
    .click();
  await page.getByRole("menuitem", { name: "Remove habit" }).click();
  await expect(page.locator(".habit-card")).toHaveCount(5);
  await page.getByRole("button", { name: "Undo", exact: true }).click();
  await expect(page.locator(".habit-card")).toHaveCount(6);
  await page
    .getByRole("button", { name: "Options for Gym", exact: true })
    .click();
  await page.getByRole("menuitem", { name: "Remove habit" }).click();
  await page.getByRole("button", { name: "Previous day", exact: true }).click();
  await expect(
    page.getByRole("checkbox", { name: "Mark incomplete: Gym", exact: true }),
  ).toHaveAttribute("aria-checked", "true");
  await page.getByRole("button", { name: "Today", exact: true }).click();
  await page.reload();
  await expect(page.locator(".habit-card")).toHaveCount(5);
});

test("daily notes and filters work without changing stored progress", async ({
  page,
}) => {
  await page
    .getByRole("textbox", { name: "Daily note", exact: true })
    .fill("Steady progress.");
  await page
    .getByRole("checkbox", {
      name: "Mark complete: Code practice",
      exact: true,
    })
    .click();
  await page.getByRole("button", { name: "Done", exact: true }).click();
  await expect(page.locator(".habit-card")).toHaveCount(1);
  await page.getByRole("button", { name: "To do", exact: true }).click();
  await expect(page.locator(".habit-card")).toHaveCount(5);
  await page.getByRole("button", { name: "Next day", exact: true }).click();
  await expect(
    page.getByRole("textbox", { name: "Daily note", exact: true }),
  ).toHaveValue("");
  await page.getByRole("button", { name: "Previous day", exact: true }).click();
  await page.reload();
  await expect(
    page.getByRole("textbox", { name: "Daily note", exact: true }),
  ).toHaveValue("Steady progress.");
});

test("the 30-minute timer pauses, resumes, finishes once, and resets to 30", async ({
  page,
}) => {
  await page.getByLabel("Choose focus habit").selectOption("code");
  await page.getByRole("button", { name: "Start focus", exact: true }).click();
  await page.clock.fastForward(60_000);
  await expect(page.getByRole("timer")).toHaveText("29:00");
  await page.getByRole("button", { name: "Pause focus" }).click();
  await page.clock.fastForward(30_000);
  await expect(page.getByRole("timer")).toHaveText("29:00");
  await page.getByRole("button", { name: "Resume focus" }).click();
  await page.clock.fastForward(29 * 60_000);
  await expect(page.getByRole("timer")).toHaveText("00:00");
  await expect(page.locator(".focus-footnote")).toContainText(
    "1 session completed today",
  );
  await page.clock.fastForward(2000);
  await expect(page.locator(".focus-footnote")).toContainText(
    "1 session completed today",
  );
  await page.getByRole("button", { name: "Reset focus timer" }).click();
  await expect(page.getByRole("timer")).toHaveText("30:00");
  await page.reload();
  await expect(page.locator(".focus-footnote")).toContainText(
    "1 session completed today",
  );
});

test("settings and JSON export preserve routine, checkmarks and a 30-minute focus", async ({
  page,
}) => {
  await page
    .getByRole("checkbox", {
      name: "Mark complete: Creatine intake",
      exact: true,
    })
    .click();
  await page
    .getByRole("button", { name: "Planner settings", exact: true })
    .click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("What should we call you?").fill("Nurzod");
  await expect(
    dialog.getByText("30-minute focus sessions", { exact: true }),
  ).toBeVisible();
  const download = page.waitForEvent("download");
  await dialog.getByRole("button", { name: "Export my plan" }).click();
  const file = await download;
  const stream = await file.createReadStream();
  const chunks: Buffer[] = [];
  for await (const chunk of stream!) chunks.push(chunk);
  const exported = JSON.parse(Buffer.concat(chunks).toString());
  expect(exported.name).toBe("Nurzod");
  expect(exported.habits).toHaveLength(6);
  expect(exported.completions["2026-10-15"]).toEqual(["creatine"]);
  expect(exported.focusMinutes).toBe(30);
  await dialog.getByRole("button", { name: "All set", exact: true }).click();
  await page.reload();
  await expect(page.locator(".hero-copy p")).toContainText("Nurzod");
});

test("the previous timed planner migrates without losing notes or original data", async ({
  page,
}) => {
  const old = {
    tasks: [
      {
        id: "old-task",
        date: "2026-10-15",
        title: "Old personal task",
        start: "09:00",
        end: "10:00",
        category: "Personal",
        notes: "Keep this",
        done: true,
      },
    ],
    notes: { "2026-10-15": "My old note" },
    name: "Nurzod",
    focusMinutes: 15,
  };
  await page.evaluate(
    ({ key, old }) => {
      localStorage.removeItem(key);
      localStorage.setItem("daylight-planner-v1", JSON.stringify(old));
    },
    { key, old },
  );
  await page.reload();
  await expect(page.locator(".habit-card")).toHaveCount(6);
  await expect(
    page.getByRole("textbox", { name: "Daily note", exact: true }),
  ).toHaveValue("My old note");
  await expect(page.getByRole("timer")).toHaveText("30:00");
  const preserved = await page.evaluate(() =>
    JSON.parse(localStorage.getItem("daylight-planner-v1")!),
  );
  expect(preserved).toEqual(old);
  const migrated = await page.evaluate(
    (key) => JSON.parse(localStorage.getItem(key)!),
    key,
  );
  expect(migrated.previousPlan).toEqual(old);
  expect(migrated.name).toBe("Nurzod");
});

test("corrupt storage is not overwritten before an explicit backup", async ({
  page,
}) => {
  await page.evaluate(
    (key) => localStorage.setItem(key, "unreadable previous plan"),
    key,
  );
  await page.reload();
  await expect(page.getByRole("alert")).toContainText(
    "Your saved plan could not be opened",
  );
  expect(await page.evaluate((key) => localStorage.getItem(key), key)).toBe(
    "unreadable previous plan",
  );
  await page.getByRole("button", { name: "Back up old data & save" }).click();
  await expect(page.getByRole("alert")).toHaveCount(0);
  expect(
    await page.evaluate(
      (key) =>
        Object.keys(localStorage)
          .filter((k) => k.startsWith(`${key}-recovery-`))
          .map((k) => localStorage.getItem(k)),
      key,
    ),
  ).toEqual(["unreadable previous plan"]);
  await expect(page.locator(".save-indicator")).toContainText(
    "All progress saved",
  );
});

test("dark desktop and mobile layouts load local jet artwork without overflow", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Your daily mission.", exact: true }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => getComputedStyle(document.documentElement).colorScheme,
    ),
  ).toBe("dark");
  await expect(page.locator(".hero-photo")).toBeVisible();
  await expect
    .poll(() =>
      page
        .locator(".hero-photo")
        .evaluate(
          (img: HTMLImageElement) => img.complete && img.naturalWidth > 0,
        ),
    )
    .toBe(true);
  await page.screenshot({
    path: "/tmp/daylight-dark-desktop.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole("button", { name: "Open navigation" }).click();
  await page.getByRole("button", { name: "Field notes", exact: true }).click();
  await page
    .getByRole("textbox", { name: "Notes for selected day" })
    .fill("A small-screen thought.");
  await page.getByRole("button", { name: "All done", exact: true }).click();
  await expect(
    page.getByRole("textbox", { name: "Daily note", exact: true }),
  ).toHaveValue("A small-screen thought.");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "/tmp/daylight-dark-mobile.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Week", exact: true }).click();
  await expect(page.locator(".week-table")).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  expect(errors).toEqual([]);
});

import { test, expect } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.clock.install({ time: new Date("2026-10-15T10:00:00+05:00") });
  await page.goto("/");
});

test("completion ticks switch both ways and survive a refresh", async ({
  page,
}) => {
  const tick = page.getByRole("checkbox", {
    name: "Mark complete: Team check-in",
  });
  await expect(tick).toHaveAttribute("aria-checked", "false");
  await tick.click();
  await expect(
    page.getByRole("checkbox", { name: "Mark incomplete: Team check-in" }),
  ).toHaveAttribute("aria-checked", "true");
  await page.reload();
  await page
    .getByRole("checkbox", { name: "Mark incomplete: Team check-in" })
    .click();
  await expect(
    page.getByRole("checkbox", { name: "Mark complete: Team check-in" }),
  ).toHaveAttribute("aria-checked", "false");
  await expect(page.locator(".stat-card").first()).toContainText("2 / 6");
});

test("create, validate, edit, filter and persist a task", async ({ page }) => {
  await page.getByRole("button", { name: /^Add task/ }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("What’s the plan?").fill("Sketch the next big idea");
  await dialog.getByLabel("Start time").fill("15:30");
  await dialog.getByLabel("End time").fill("15:00");
  await dialog.getByRole("button", { name: "Add to my day" }).click();
  await expect(dialog.getByRole("alert")).toContainText("after the start time");
  await dialog.getByLabel("End time").fill("16:15");
  await dialog.getByRole("button", { name: "Personal", exact: true }).click();
  await dialog
    .getByLabel("A note")
    .fill("Bring a notebook and a little curiosity.");
  await dialog.getByRole("button", { name: "Add to my day" }).click();
  await expect(
    page.getByRole("button", { name: "Sketch the next big idea", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Sketch the next big idea", exact: true })
    .click();
  await dialog
    .getByLabel("What’s the plan?")
    .fill("Sketch something wonderful");
  await dialog.getByRole("button", { name: "Save changes" }).click();
  await page.getByLabel("Filter tasks").selectOption("Personal");
  await expect(page.locator(".task-card")).toHaveCount(2);
  await page.reload();
  await expect(
    page.getByRole("button", {
      name: "Sketch something wonderful",
      exact: true,
    }),
  ).toBeVisible();
  await expect(page.locator(".stat-card").first()).toContainText("2 / 7");
});

test("delete and undo restore the original task", async ({ page }) => {
  await page.getByRole("button", { name: "Options for Team check-in" }).click();
  await page.getByRole("menuitem", { name: "Delete task" }).click();
  await expect(
    page.getByRole("button", { name: "Team check-in", exact: true }),
  ).toHaveCount(0);
  await page.getByRole("button", { name: "Undo", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Team check-in", exact: true }),
  ).toBeVisible();
  await expect(page.locator(".stat-card").first()).toContainText("2 / 6");
});

test("dates keep tasks and notes separate, and weekly navigation works", async ({
  page,
}) => {
  await page
    .getByRole("textbox", { name: "Daily note", exact: true })
    .fill("Leave some room for a walk.");
  await page.getByRole("button", { name: "Next day", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "A little room for possibility." }),
  ).toBeVisible();
  await expect(
    page.getByRole("textbox", { name: "Daily note", exact: true }),
  ).toHaveValue("");
  await page
    .getByRole("textbox", { name: "Daily note", exact: true })
    .fill("Tomorrow has its own possibilities.");
  await page.getByRole("button", { name: "Previous day", exact: true }).click();
  await expect(
    page.getByRole("textbox", { name: "Daily note", exact: true }),
  ).toHaveValue("Leave some room for a walk.");
  await page.getByRole("button", { name: "Week", exact: true }).click();
  await expect(page.locator(".week-day")).toHaveCount(7);
  await expect(page.locator(".week-task")).toHaveCount(6);
  await page.getByRole("button", { name: "Thu 15", exact: true }).click();
  await expect(page.locator(".task-card")).toHaveCount(6);
  await page.reload();
  await expect(
    page.getByRole("textbox", { name: "Daily note", exact: true }),
  ).toHaveValue("Leave some room for a walk.");
});

test("focus timer counts, pauses, resumes, resets and finishes", async ({
  page,
}) => {
  await page.getByRole("button", { name: "Start focus", exact: true }).click();
  await page.clock.fastForward(60_000);
  await expect(page.getByRole("timer")).toHaveText("24:00");
  await page.getByRole("button", { name: "Pause focus" }).click();
  await page.clock.fastForward(30_000);
  await expect(page.getByRole("timer")).toHaveText("24:00");
  await page.getByRole("button", { name: "Resume focus" }).click();
  await page.clock.fastForward(24 * 60_000);
  await expect(page.getByRole("timer")).toHaveText("00:00");
  await expect(page.getByRole("status")).toContainText(
    "Focus session complete",
  );
  await page.getByRole("button", { name: "Reset focus timer" }).click();
  await expect(page.getByRole("timer")).toHaveText("25:00");
});

test("settings persist and export includes the saved plan", async ({
  page,
}) => {
  await page
    .getByRole("button", { name: "Planner settings", exact: true })
    .click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("What should we call you?").fill("Nurzod");
  await dialog.getByLabel("Your focus session").selectOption("15");
  const download = page.waitForEvent("download");
  await dialog.getByRole("button", { name: "Export my plan" }).click();
  const file = await download;
  expect(file.suggestedFilename()).toBe("daylight-plan-2026-10-15.json");
  const stream = await file.createReadStream();
  const chunks: Buffer[] = [];
  for await (const chunk of stream!) chunks.push(chunk);
  const exported = JSON.parse(Buffer.concat(chunks).toString());
  expect(exported.name).toBe("Nurzod");
  expect(exported.tasks).toHaveLength(6);
  await dialog.getByRole("button", { name: "Feels like me" }).click();
  await expect(page.getByRole("timer")).toHaveText("15:00");
  await page.reload();
  await expect(page.locator(".heading-description")).toContainText("Nurzod");
  await expect(page.getByRole("timer")).toHaveText("15:00");
});

test("mobile navigation and task editing work without horizontal overflow", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(
    page.getByRole("button", { name: "Open navigation" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Open navigation" }).click();
  await page.getByRole("button", { name: "My notes", exact: true }).click();
  await page
    .getByRole("textbox", { name: "Notes for selected day" })
    .fill("A small-screen thought.");
  await page.getByRole("button", { name: "All done", exact: true }).click();
  await expect(
    page.getByRole("textbox", { name: "Daily note", exact: true }),
  ).toHaveValue("A small-screen thought.");
  await page
    .getByRole("button", { name: "Team check-in", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.getByRole("button", { name: "Close dialog" }).click();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({ path: "/tmp/daylight-mobile.png", fullPage: true });
});

test("initial layout has no runtime errors or overflow", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "A day with intention." }),
  ).toBeVisible();
  await expect(page.locator(".task-card")).toHaveCount(6);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  expect(errors).toEqual([]);
  await page.screenshot({ path: "/tmp/daylight-desktop.png", fullPage: true });
});

test("unreadable saved data is preserved until an explicit backup and recovery", async ({
  page,
}) => {
  await page.evaluate(() =>
    localStorage.setItem("daylight-planner-v1", "unreadable previous plan"),
  );
  await page.reload();
  await expect(page.getByRole("alert")).toContainText(
    "Your saved plan could not be opened",
  );
  expect(
    await page.evaluate(() => localStorage.getItem("daylight-planner-v1")),
  ).toBe("unreadable previous plan");
  await page.getByRole("button", { name: "Back up old data & save" }).click();
  await expect(page.getByRole("alert")).toHaveCount(0);
  expect(
    await page.evaluate(() =>
      Object.keys(localStorage)
        .filter((key) => key.startsWith("daylight-planner-v1-recovery-"))
        .map((key) => localStorage.getItem(key)),
    ),
  ).toEqual(["unreadable previous plan"]);
  await expect(page.locator(".save-indicator")).toContainText(
    "All changes saved",
  );
});

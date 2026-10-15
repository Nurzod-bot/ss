export const CATEGORIES = [
  "Health",
  "Training",
  "Learning",
  "Focus",
  "Personal",
] as const;
export type Category = (typeof CATEGORIES)[number];
export type HabitIcon =
  "capsule" | "flask" | "dumbbell" | "language" | "code" | "book" | "check";
export type Habit = {
  id: string;
  title: string;
  category: Category;
  notes: string;
  icon: HabitIcon;
  createdOn?: string;
  archivedOn?: string;
};
export type DayHabit = Habit & { done: boolean };
export type PlannerData = {
  version: 2;
  habits: Habit[];
  completions: Record<string, string[]>;
  focusSessions: Record<string, number>;
  notes: Record<string, string>;
  name: string;
  previousPlan?: unknown;
};
export const STORAGE_KEY = "daylight-planner-v2";
export const LEGACY_STORAGE_KEY = "daylight-planner-v1";
export const FOCUS_SECONDS = 30 * 60;

export const DEFAULT_HABITS: Habit[] = [
  {
    id: "fish-oil",
    title: "Fish oil intake",
    category: "Health",
    notes: "A small daily essential.",
    icon: "capsule",
  },
  {
    id: "creatine",
    title: "Creatine intake",
    category: "Health",
    notes: "Keep your routine consistent.",
    icon: "flask",
  },
  {
    id: "gym",
    title: "Gym",
    category: "Training",
    notes: "Show up. Put in the work.",
    icon: "dumbbell",
  },
  {
    id: "chinese",
    title: "Chinese language practice",
    category: "Learning",
    notes: "A few new words. A little more fluency.",
    icon: "language",
  },
  {
    id: "code",
    title: "Code practice",
    category: "Focus",
    notes: "Build something. Solve something. Get better.",
    icon: "code",
  },
  {
    id: "book",
    title: "A few pages of a book",
    category: "Personal",
    notes: "Less scrolling. More turning pages.",
    icon: "book",
  },
];

export function dateKey(date: Date): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}
export function fromKey(key: string): Date {
  return new Date(`${key}T12:00:00`);
}
export function shiftDate(key: string, days: number): string {
  const date = fromKey(key);
  date.setDate(date.getDate() + days);
  return dateKey(date);
}
export function weekDates(key: string): string[] {
  const offset = (fromKey(key).getDay() + 6) % 7;
  return Array.from({ length: 7 }, (_, i) => shiftDate(key, i - offset));
}
export function isActive(habit: Habit, date: string): boolean {
  return (
    (!habit.createdOn || habit.createdOn <= date) &&
    (!habit.archivedOn || date < habit.archivedOn)
  );
}
export function habitsForDate(data: PlannerData, date: string): DayHabit[] {
  const done = new Set(data.completions[date] ?? []);
  return data.habits
    .filter((h) => isActive(h, date))
    .map((h) => ({ ...h, done: done.has(h.id) }));
}
export function completedStreak(data: PlannerData, today: string): number {
  const complete = (day: string) => {
    const habits = habitsForDate(data, day);
    return habits.length > 0 && habits.every((h) => h.done);
  };
  let cursor = complete(today) ? today : shiftDate(today, -1),
    streak = 0;
  while (streak < 36600 && complete(cursor)) {
    streak++;
    cursor = shiftDate(cursor, -1);
  }
  return streak;
}
export function toggleCompletion(
  data: PlannerData,
  date: string,
  id: string,
): PlannerData {
  const done = new Set(data.completions[date] ?? []);
  if (done.has(id)) done.delete(id);
  else done.add(id);
  return { ...data, completions: { ...data.completions, [date]: [...done] } };
}
export function initialData(): PlannerData {
  return {
    version: 2,
    habits: DEFAULT_HABITS.map((h) => ({ ...h })),
    completions: {},
    focusSessions: {},
    notes: {},
    name: "",
  };
}
const isRecord = (v: unknown): v is Record<string, unknown> =>
  !!v && typeof v === "object" && !Array.isArray(v);
const isDate = (v: unknown): v is string =>
  typeof v === "string" &&
  /^\d{4}-\d{2}-\d{2}$/.test(v) &&
  !Number.isNaN(fromKey(v).getTime()) &&
  dateKey(fromKey(v)) === v;
function isHabit(v: unknown): v is Habit {
  if (!isRecord(v)) return false;
  return (
    typeof v.id === "string" &&
    !!v.id &&
    typeof v.title === "string" &&
    !!v.title.trim() &&
    typeof v.notes === "string" &&
    CATEGORIES.includes(v.category as Category) &&
    [
      "capsule",
      "flask",
      "dumbbell",
      "language",
      "code",
      "book",
      "check",
    ].includes(v.icon as string) &&
    (v.createdOn === undefined || isDate(v.createdOn)) &&
    (v.archivedOn === undefined || isDate(v.archivedOn))
  );
}
export function isPlannerData(v: unknown): v is PlannerData {
  if (
    !isRecord(v) ||
    v.version !== 2 ||
    !Array.isArray(v.habits) ||
    !v.habits.every(isHabit) ||
    new Set(v.habits.map((h) => h.id)).size !== v.habits.length ||
    !isRecord(v.completions) ||
    !isRecord(v.notes) ||
    !isRecord(v.focusSessions) ||
    typeof v.name !== "string"
  )
    return false;
  return (
    Object.entries(v.completions).every(
      ([date, ids]) =>
        isDate(date) &&
        Array.isArray(ids) &&
        ids.every((id) => typeof id === "string"),
    ) &&
    Object.entries(v.notes).every(
      ([date, note]) => isDate(date) && typeof note === "string",
    ) &&
    Object.entries(v.focusSessions).every(
      ([date, n]) =>
        isDate(date) &&
        typeof n === "number" &&
        Number.isSafeInteger(n) &&
        n >= 0,
    )
  );
}
export function loadData(): { data: PlannerData; warning: string | null } {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed: unknown = JSON.parse(raw);
      if (!isPlannerData(parsed)) throw new Error("Invalid saved planner");
      return { data: parsed, warning: null };
    }
    const legacy = localStorage.getItem(LEGACY_STORAGE_KEY);
    if (!legacy) return { data: initialData(), warning: null };
    const old: unknown = JSON.parse(legacy);
    if (
      !isRecord(old) ||
      !Array.isArray(old.tasks) ||
      !isRecord(old.notes) ||
      !Object.entries(old.notes).every(
        ([date, note]) => isDate(date) && typeof note === "string",
      )
    )
      throw new Error("Invalid previous planner");
    return {
      data: {
        ...initialData(),
        name: typeof old.name === "string" ? old.name : "",
        notes: old.notes as Record<string, string>,
        previousPlan: old,
      },
      warning: null,
    };
  } catch {
    return {
      data: initialData(),
      warning:
        "Your saved plan could not be opened. Back up the old data before saving a fresh checklist.",
    };
  }
}

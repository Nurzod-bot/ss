export const CATEGORIES = ["Focus", "Work", "Personal", "Wellness"] as const;
export type Category = (typeof CATEGORIES)[number];
export type Task = {
  id: string;
  date: string;
  title: string;
  start: string;
  end: string;
  category: Category;
  notes: string;
  done: boolean;
};
export type PlannerData = {
  tasks: Task[];
  notes: Record<string, string>;
  name: string;
  focusMinutes: number;
};
export const STORAGE_KEY = "daylight-planner-v1";

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
export function minutes(time: string): number {
  const [h, m] = time.split(":").map(Number);
  return h * 60 + m;
}
export function duration(task: Task): number {
  return minutes(task.end) - minutes(task.start);
}
export function readableDuration(value: number): string {
  const h = Math.floor(value / 60),
    m = value % 60;
  return h ? `${h}h${m ? ` ${m}m` : ""}` : `${m}m`;
}
export function clock(time: string): string {
  const [h, m] = time.split(":").map(Number);
  return `${h % 12 || 12}:${String(m).padStart(2, "0")}`;
}
export function meridiem(time: string): string {
  return Number(time.split(":")[0]) >= 12 ? "PM" : "AM";
}
export function weekDates(key: string): string[] {
  const d = fromKey(key);
  const offset = (d.getDay() + 6) % 7;
  return Array.from({ length: 7 }, (_, i) => shiftDate(key, i - offset));
}
export function plannedMinutes(tasks: Task[]): number {
  const intervals = tasks
    .map((t) => [minutes(t.start), minutes(t.end)])
    .sort((a, b) => a[0] - b[0]);
  let total = 0,
    end = 0;
  for (const [start, stop] of intervals) {
    total += Math.max(0, stop - Math.max(start, end));
    end = Math.max(end, stop);
  }
  return total;
}
export function initialData(): PlannerData {
  const date = dateKey(new Date());
  const examples: Omit<Task, "id" | "date">[] = [
    {
      title: "A slow start & morning rituals",
      start: "08:00",
      end: "08:30",
      category: "Wellness",
      notes: "A little movement, a good coffee, a clear mind.",
      done: true,
    },
    {
      title: "Deep work session",
      start: "09:00",
      end: "10:30",
      category: "Focus",
      notes: "One important thing. Notifications off.",
      done: true,
    },
    {
      title: "Team check-in",
      start: "11:00",
      end: "11:30",
      category: "Work",
      notes: "Connect, share progress, make a plan.",
      done: false,
    },
    {
      title: "Lunch & a little fresh air",
      start: "12:00",
      end: "13:00",
      category: "Wellness",
      notes: "Step away from your screen. You’ve earned it.",
      done: false,
    },
    {
      title: "Make something great",
      start: "13:30",
      end: "15:00",
      category: "Focus",
      notes: "A little room for your next big idea.",
      done: false,
    },
    {
      title: "Read a few chapters",
      start: "17:00",
      end: "17:30",
      category: "Personal",
      notes: "End the day with something just for you.",
      done: false,
    },
  ];
  return {
    tasks: examples.map((t, i) => ({ ...t, date, id: `welcome-${i}` })),
    notes: {},
    name: "",
    focusMinutes: 25,
  };
}
function isTask(value: unknown): value is Task {
  if (!value || typeof value !== "object") return false;
  const t = value as Task;
  return (
    typeof t.id === "string" &&
    typeof t.title === "string" &&
    typeof t.notes === "string" &&
    typeof t.done === "boolean" &&
    /^\d{4}-\d{2}-\d{2}$/.test(t.date) &&
    CATEGORIES.includes(t.category) &&
    /^([01]\d|2[0-3]):[0-5]\d$/.test(t.start) &&
    /^([01]\d|2[0-3]):[0-5]\d$/.test(t.end) &&
    duration(t) > 0
  );
}
export function loadData(): { data: PlannerData; warning: string | null } {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { data: initialData(), warning: null };
    const parsed = JSON.parse(raw);
    if (
      !Array.isArray(parsed.tasks) ||
      !parsed.tasks.every(isTask) ||
      !parsed.notes ||
      typeof parsed.notes !== "object" ||
      Array.isArray(parsed.notes) ||
      !Object.values(parsed.notes).every((v) => typeof v === "string")
    )
      throw new Error("Invalid planner data");
    return {
      data: {
        tasks: parsed.tasks,
        notes: parsed.notes,
        name: typeof parsed.name === "string" ? parsed.name : "",
        focusMinutes: [15, 25, 45, 60].includes(parsed.focusMinutes)
          ? parsed.focusMinutes
          : 25,
      },
      warning: null,
    };
  } catch {
    return {
      data: initialData(),
      warning:
        "Your saved plan could not be opened. Export or back up your browser data before making changes.",
    };
  }
}

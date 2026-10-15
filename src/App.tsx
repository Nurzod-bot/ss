import { useEffect, useRef, useState, type ReactNode } from "react";
import {
  ArrowDownToLine,
  ArrowRight,
  BookOpen,
  CalendarDays,
  Check,
  CheckCheck,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  CircleHelp,
  Code2,
  Crosshair,
  Dumbbell,
  Flame,
  FlaskConical,
  Languages,
  ListChecks,
  Menu,
  MoreHorizontal,
  Pause,
  Pencil,
  Pill,
  Plane,
  Play,
  Plus,
  Repeat2,
  RotateCcw,
  Settings2,
  ShieldCheck,
  Target,
  Trash2,
  X,
  Zap,
  type LucideIcon,
} from "lucide-react";
import {
  CATEGORIES,
  completedStreak,
  dateKey,
  FOCUS_SECONDS,
  fromKey,
  habitsForDate,
  isActive,
  LEGACY_STORAGE_KEY,
  loadData,
  shiftDate,
  STORAGE_KEY,
  toggleCompletion,
  weekDates,
  type Category,
  type DayHabit,
  type Habit,
  type HabitIcon,
  type PlannerData,
} from "./model";

const habitIcons: Record<HabitIcon, LucideIcon> = {
  capsule: Pill,
  flask: FlaskConical,
  dumbbell: Dumbbell,
  language: Languages,
  code: Code2,
  book: BookOpen,
  check: CheckCheck,
};
const categoryIcons: Record<Category, HabitIcon> = {
  Health: "capsule",
  Training: "dumbbell",
  Learning: "language",
  Focus: "code",
  Personal: "book",
};
const longDate = (key: string) =>
  fromKey(key).toLocaleDateString("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
  });
const shortDate = (key: string) =>
  fromKey(key).toLocaleDateString("en-US", { month: "short", day: "numeric" });

function Dialog({
  title,
  description,
  onClose,
  children,
  className = "",
}: {
  title: string;
  description?: string;
  onClose: () => void;
  children: ReactNode;
  className?: string;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    ref.current?.showModal();
  }, []);
  return (
    <dialog
      ref={ref}
      className={`dialog ${className}`}
      onCancel={onClose}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      aria-labelledby="dialog-title"
    >
      <div className="dialog-heading">
        <div>
          <p className="eyebrow">YOUR DAILY FLIGHT PLAN</p>
          <h2 id="dialog-title">{title}</h2>
          {description && <p className="muted">{description}</p>}
        </div>
        <button
          className="icon-button"
          onClick={onClose}
          aria-label="Close dialog"
        >
          <X size={19} />
        </button>
      </div>
      {children}
    </dialog>
  );
}

function MiniCalendar({
  selected,
  onSelect,
}: {
  selected: string;
  onSelect: (key: string) => void;
}) {
  const [month, setMonth] = useState(
    () =>
      new Date(
        fromKey(selected).getFullYear(),
        fromKey(selected).getMonth(),
        1,
      ),
  );
  useEffect(() => {
    const d = fromKey(selected);
    setMonth(new Date(d.getFullYear(), d.getMonth(), 1));
  }, [selected]);
  const offset = (month.getDay() + 6) % 7;
  const count = new Date(
    month.getFullYear(),
    month.getMonth() + 1,
    0,
  ).getDate();
  const today = dateKey(new Date());
  return (
    <div className="mini-calendar">
      <div className="calendar-title">
        <span>
          {month.toLocaleDateString("en-US", {
            month: "long",
            year: "numeric",
          })}
        </span>
        <div>
          <button
            aria-label="Previous month"
            className="icon-button small"
            onClick={() =>
              setMonth(new Date(month.getFullYear(), month.getMonth() - 1, 1))
            }
          >
            <ChevronLeft size={15} />
          </button>
          <button
            aria-label="Next month"
            className="icon-button small"
            onClick={() =>
              setMonth(new Date(month.getFullYear(), month.getMonth() + 1, 1))
            }
          >
            <ChevronRight size={15} />
          </button>
        </div>
      </div>
      <div className="calendar-grid">
        {["M", "T", "W", "T", "F", "S", "S"].map((day, i) => (
          <span className="weekday" key={i}>
            {day}
          </span>
        ))}
        {Array.from({ length: offset }, (_, i) => (
          <span key={`empty-${i}`} />
        ))}
        {Array.from({ length: count }, (_, i) => {
          const key = dateKey(
            new Date(month.getFullYear(), month.getMonth(), i + 1),
          );
          return (
            <button
              key={key}
              className={`${key === selected ? "selected" : ""} ${key === today ? "is-today" : ""}`}
              onClick={() => onSelect(key)}
              aria-label={longDate(key)}
              aria-current={key === today ? "date" : undefined}
              aria-pressed={key === selected}
            >
              {i + 1}
            </button>
          );
        })}
      </div>
    </div>
  );
}

function HabitCard({
  habit,
  index,
  onToggle,
  onEdit,
  onDelete,
}: {
  habit: DayHabit;
  index: number;
  onToggle: () => void;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const Icon = habitIcons[habit.icon];
  useEffect(() => {
    if (!menuOpen) return;
    const close = (e: MouseEvent) => {
      if (!menuRef.current?.contains(e.target as Node)) setMenuOpen(false);
    };
    const escape = (e: KeyboardEvent) => {
      if (e.key === "Escape") setMenuOpen(false);
    };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", escape);
    return () => {
      document.removeEventListener("mousedown", close);
      document.removeEventListener("keydown", escape);
    };
  }, [menuOpen]);
  return (
    <article
      className={`habit-card category-${habit.category.toLowerCase()} ${habit.done ? "completed" : ""}`}
    >
      <span className="habit-number">{String(index + 1).padStart(2, "0")}</span>
      <span className="habit-icon">
        <Icon size={21} strokeWidth={1.6} />
      </span>
      <div className="habit-content">
        <button className="habit-title" onClick={onEdit}>
          {habit.title}
        </button>
        <p>{habit.notes || "One step forward, every day."}</p>
      </div>
      <span className="habit-category">{habit.category}</span>
      <button
        className={`habit-check ${habit.done ? "checked" : ""}`}
        onClick={onToggle}
        role="checkbox"
        aria-checked={habit.done}
        aria-label={`${habit.done ? "Mark incomplete" : "Mark complete"}: ${habit.title}`}
      >
        <Check size={15} strokeWidth={2.5} />
      </button>
      <div className="habit-menu" ref={menuRef}>
        <button
          className="icon-button"
          onClick={() => setMenuOpen(!menuOpen)}
          aria-label={`Options for ${habit.title}`}
          aria-expanded={menuOpen}
        >
          <MoreHorizontal size={18} />
        </button>
        {menuOpen && (
          <div className="dropdown" role="menu">
            <button
              role="menuitem"
              onClick={() => {
                setMenuOpen(false);
                onEdit();
              }}
            >
              <Pencil size={14} />
              Edit habit
            </button>
            <button
              className="danger"
              role="menuitem"
              onClick={() => {
                setMenuOpen(false);
                onDelete();
              }}
            >
              <Trash2 size={14} />
              Remove habit
            </button>
          </div>
        )}
      </div>
    </article>
  );
}

function HabitEditor({
  habit,
  selected,
  onSave,
  onClose,
}: {
  habit: Habit | null;
  selected: string;
  onSave: (habit: Habit) => void;
  onClose: () => void;
}) {
  const [title, setTitle] = useState(habit?.title ?? "");
  const [category, setCategory] = useState<Category>(
    habit?.category ?? "Focus",
  );
  const [notes, setNotes] = useState(habit?.notes ?? "");
  const [error, setError] = useState("");
  return (
    <Dialog
      title={habit ? "Refine your routine." : "Add a daily habit."}
      description="No time slots. Just one more thing worth showing up for."
      onClose={onClose}
    >
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (!title.trim()) {
            setError("Give your habit a name.");
            return;
          }
          onSave({
            id: habit?.id ?? crypto.randomUUID(),
            title: title.trim(),
            category,
            notes: notes.trim(),
            icon: habit?.icon ?? categoryIcons[category],
            createdOn: habit ? habit.createdOn : selected,
            archivedOn: habit?.archivedOn,
          });
        }}
      >
        <label className="field">
          Habit name
          <input
            autoFocus
            required
            maxLength={120}
            placeholder="Something to get better at"
            value={title}
            onChange={(e) => {
              setTitle(e.target.value);
              setError("");
            }}
          />
        </label>
        <fieldset className="category-field">
          <legend>Category</legend>
          <div className="category-options">
            {CATEGORIES.map((c) => {
              const Icon = habitIcons[categoryIcons[c]];
              return (
                <button
                  type="button"
                  key={c}
                  className={`category-option category-${c.toLowerCase()} ${category === c ? "active" : ""}`}
                  onClick={() => setCategory(c)}
                  aria-pressed={category === c}
                >
                  <Icon size={14} />
                  {c}
                </button>
              );
            })}
          </div>
        </fieldset>
        <label className="field">
          A reminder <span className="optional">(optional)</span>
          <textarea
            rows={3}
            maxLength={500}
            placeholder="A little motivation for your future self…"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
          />
        </label>
        <p className="repeat-notice">
          <Repeat2 size={15} />
          {habit
            ? "This updates your daily routine. Existing checkmarks stay saved."
            : `Repeats every day from ${shortDate(selected)}. Checkmarks are separate for each day.`}
        </p>
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        <div className="dialog-footer">
          <button type="button" className="button secondary" onClick={onClose}>
            Cancel
          </button>
          <button className="button primary" type="submit">
            <Check size={15} />
            {habit ? "Save changes" : "Add to routine"}
          </button>
        </div>
      </form>
    </Dialog>
  );
}

export default function App() {
  const [loaded] = useState(loadData);
  const [data, setData] = useState<PlannerData>(loaded.data);
  const [storageWarning, setStorageWarning] = useState(loaded.warning);
  const [canPersist, setCanPersist] = useState(!loaded.warning);
  const [today, setToday] = useState(() => dateKey(new Date()));
  const [selected, setSelected] = useState(today);
  const [view, setView] = useState<"day" | "week">("day");
  const [filter, setFilter] = useState("All");
  const [editor, setEditor] = useState<{
    habit: Habit | null;
    date: string;
  } | null>(null);
  const [dialog, setDialog] = useState<"notes" | "settings" | "help" | null>(
    null,
  );
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [toast, setToast] = useState<{
    message: string;
    removed?: Habit;
  } | null>(null);
  const [focusTask, setFocusTask] = useState("");
  const [remaining, setRemaining] = useState(FOCUS_SECONDS);
  const [deadline, setDeadline] = useState<number | null>(null);
  const completedDeadline = useRef<number | null>(null);

  useEffect(() => {
    if (!canPersist) return;
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
      setStorageWarning(null);
    } catch {
      setStorageWarning(
        "Browser storage is unavailable. Export your plan before closing this tab.",
      );
    }
  }, [data, canPersist]);
  useEffect(() => {
    if (!toast) return;
    const id = window.setTimeout(() => setToast(null), 6000);
    return () => window.clearTimeout(id);
  }, [toast]);
  useEffect(() => {
    const update = () => {
      const next = dateKey(new Date());
      if (next !== today) {
        setToday(next);
        setSelected((current) => (current === today ? next : current));
      }
    };
    const id = window.setInterval(update, 15000);
    document.addEventListener("visibilitychange", update);
    return () => {
      window.clearInterval(id);
      document.removeEventListener("visibilitychange", update);
    };
  }, [today]);
  useEffect(() => {
    if (deadline === null) return;
    const tick = () => {
      const left = Math.max(0, Math.ceil((deadline - Date.now()) / 1000));
      setRemaining(left);
      if (left === 0) {
        setDeadline(null);
        if (completedDeadline.current !== deadline) {
          completedDeadline.current = deadline;
          const day = dateKey(new Date());
          setData((prev) => ({
            ...prev,
            focusSessions: {
              ...prev.focusSessions,
              [day]: (prev.focusSessions[day] ?? 0) + 1,
            },
          }));
          setToast({ message: "30 minutes, well spent. Take a breather." });
        }
      }
    };
    tick();
    const id = window.setInterval(tick, 250);
    return () => window.clearInterval(id);
  }, [deadline]);
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (
        e.target instanceof HTMLElement &&
        (e.target.closest("input, textarea, select, dialog") ||
          e.target.isContentEditable)
      )
        return;
      if (
        e.key.toLowerCase() === "n" &&
        !e.metaKey &&
        !e.ctrlKey &&
        !e.altKey
      ) {
        e.preventDefault();
        setEditor({ habit: null, date: selected });
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [selected]);

  const dayHabits = habitsForDate(data, selected);
  const completed = dayHabits.filter((h) => h.done).length;
  const progress = dayHabits.length
    ? Math.round((completed / dayHabits.length) * 100)
    : 0;
  const visibleHabits = dayHabits.filter(
    (h) => filter === "All" || (filter === "To do" ? !h.done : h.done),
  );
  const dates = weekDates(selected);
  const weekHabits = data.habits.filter((h) =>
    dates.some((d) => isActive(h, d)),
  );
  const note = data.notes[selected] ?? "";
  const streak = completedStreak(data, today);
  const setNote = (value: string) =>
    setData((prev) => ({
      ...prev,
      notes: { ...prev.notes, [selected]: value },
    }));
  const chooseDay = (key: string) => {
    setSelected(key);
    setView("day");
    setSidebarOpen(false);
  };
  const toggle = (id: string, date = selected) =>
    setData((prev) => toggleCompletion(prev, date, id));
  const saveHabit = (habit: Habit) => {
    setData((prev) => ({
      ...prev,
      habits: prev.habits.some((h) => h.id === habit.id)
        ? prev.habits.map((h) => (h.id === habit.id ? habit : h))
        : [...prev.habits, habit],
    }));
    setFilter("All");
    setEditor(null);
    setToast({
      message: editor?.habit
        ? "Routine updated. Keep showing up."
        : "A new habit on your flight plan.",
    });
  };
  const removeHabit = (habit: Habit) => {
    setData((prev) => ({
      ...prev,
      habits: prev.habits.map((h) =>
        h.id === habit.id ? { ...h, archivedOn: selected } : h,
      ),
    }));
    setToast({
      message: "Removed from this day forward. Past progress is kept.",
      removed: habit,
    });
  };
  const exportPlan = () => {
    const url = URL.createObjectURL(
      new Blob(
        [
          JSON.stringify(
            { ...data, focusMinutes: 30, exportedAt: new Date().toISOString() },
            null,
            2,
          ),
        ],
        { type: "application/json" },
      ),
    );
    const a = document.createElement("a");
    a.href = url;
    a.download = `daylight-plan-${today}.json`;
    a.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    setToast({ message: "Your plan is exported. Keep it somewhere safe." });
  };
  const recoverStorage = () => {
    try {
      for (const key of [STORAGE_KEY, LEGACY_STORAGE_KEY]) {
        const raw = localStorage.getItem(key);
        if (raw) localStorage.setItem(`${key}-recovery-${Date.now()}`, raw);
      }
      setCanPersist(true);
    } catch {
      setStorageWarning(
        "Could not back up your old data. Browser storage may be full.",
      );
    }
  };

  return (
    <div className="app-shell">
      {sidebarOpen && (
        <button
          className="sidebar-backdrop"
          aria-label="Close navigation"
          onClick={() => setSidebarOpen(false)}
        />
      )}
      <aside className={`sidebar ${sidebarOpen ? "open" : ""}`}>
        <a
          className="brand"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            chooseDay(today);
          }}
          aria-label="Daylight home"
        >
          <span className="brand-icon">
            <Plane size={23} strokeWidth={1.7} />
          </span>
          daylight<span className="brand-dot">.</span>
        </a>
        <p className="brand-tagline">YOUR EVERYDAY, ELEVATED.</p>
        <p className="nav-label">FLIGHT DECK</p>
        <nav className="main-nav" aria-label="Main navigation">
          <button
            className={view === "day" ? "active" : ""}
            onClick={() => {
              setView("day");
              setSidebarOpen(false);
            }}
          >
            <ListChecks size={18} />
            <span>Daily checklist</span>
            {view === "day" && <span className="nav-active-dot" />}
          </button>
          <button
            className={view === "week" ? "active" : ""}
            onClick={() => {
              setView("week");
              setSidebarOpen(false);
            }}
          >
            <CalendarDays size={18} />
            <span>Weekly view</span>
          </button>
          <button
            onClick={() => {
              setDialog("notes");
              setSidebarOpen(false);
            }}
          >
            <BookOpen size={18} />
            <span>Field notes</span>
          </button>
        </nav>
        <MiniCalendar selected={selected} onSelect={chooseDay} />
        <div className="sidebar-bottom">
          <div className="consistency-card">
            <ShieldCheck size={24} strokeWidth={1.3} />
            <p>
              Consistency
              <br />
              beats intensity<span>.</span>
            </p>
            <span>Small actions. Every day.</span>
            <div className="mini-bars" aria-hidden="true">
              {[24, 38, 31, 45, 39, 54, 65, 57, 76, 89, 78, 100].map(
                (height, i) => (
                  <i key={i} style={{ height: `${height}%` }} />
                ),
              )}
            </div>
          </div>
          <button className="help-button" onClick={() => setDialog("help")}>
            <CircleHelp size={15} />
            Quick briefing
            <ArrowRight size={13} />
          </button>
          <button
            className="workspace-button"
            onClick={() => setDialog("settings")}
            aria-label="Open planner settings"
          >
            <span className="avatar">
              {data.name ? data.name[0].toUpperCase() : "Y"}
            </span>
            <span>
              <strong>{data.name || "My cockpit"}</strong>
              <small>Personal workspace</small>
            </span>
            <Settings2 size={17} />
          </button>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <div className="breadcrumb">
            <button
              className="icon-button mobile-menu"
              aria-label="Open navigation"
              onClick={() => setSidebarOpen(true)}
            >
              <Menu size={21} />
            </button>
            <Crosshair size={16} />
            <span>My workspace</span>
            <ChevronRight size={13} />
            <strong>
              {view === "day" ? "Daily checklist" : "Weekly view"}
            </strong>
          </div>
          <div className="topbar-right">
            <span
              className={`save-indicator ${storageWarning ? "warning" : ""}`}
            >
              <span />
              {storageWarning ? "Not saved" : "All progress saved"}
            </span>
            <button
              className="top-avatar"
              aria-label="Planner settings"
              onClick={() => setDialog("settings")}
            >
              {data.name ? data.name[0].toUpperCase() : "Y"}
            </button>
          </div>
        </header>
        <main>
          {storageWarning && (
            <div className="storage-banner" role="alert">
              {storageWarning}
              <button onClick={exportPlan}>Export plan</button>
              {!canPersist && (
                <button onClick={recoverStorage}>
                  Back up old data & save
                </button>
              )}
            </div>
          )}
          <section className="page-heading">
            <div>
              <p className="eyebrow">
                <span className="status-dot" />
                {selected === today
                  ? "TODAY’S FLIGHT PLAN"
                  : "YOUR FLIGHT PLAN"}
              </p>
              <h1>
                {view === "day" ? "Your daily mission." : "The bigger picture."}
              </h1>
            </div>
            <button
              className="button primary add-habit"
              onClick={() => setEditor({ habit: null, date: selected })}
            >
              <Plus size={16} />
              Add habit<kbd>N</kbd>
            </button>
          </section>
          <section className="aviation-hero" aria-label="Daily motivation">
            <img
              className="hero-photo"
              src="/images/afterburner.png"
              alt="Fighter jet banking over mountain clouds at sunset"
              fetchPriority="high"
            />
            <div className="hero-shade" />
            <div className="hero-copy">
              <span className="hero-tag">
                <Plane size={12} />
                CLEARED FOR PROGRESS
              </span>
              <h2>
                Show up.
                <br />
                <span>Rise above.</span>
              </h2>
              <p>
                {data.name ? `${data.name}, your` : "Your"} routine. Your pace.
                A better you, every day.
              </p>
            </div>
            <span className="hero-coordinate">
              <Crosshair size={14} />
              STAY THE COURSE<span>01 / DAILY OPERATIONS</span>
            </span>
          </section>
          <div className="day-toolbar">
            <div className="date-controls">
              <button className="today-button" onClick={() => chooseDay(today)}>
                Today
              </button>
              <div className="date-arrows">
                <button
                  className="icon-button"
                  aria-label={view === "day" ? "Previous day" : "Previous week"}
                  onClick={() =>
                    setSelected(shiftDate(selected, view === "day" ? -1 : -7))
                  }
                >
                  <ChevronLeft size={17} />
                </button>
                <button
                  className="icon-button"
                  aria-label={view === "day" ? "Next day" : "Next week"}
                  onClick={() =>
                    setSelected(shiftDate(selected, view === "day" ? 1 : 7))
                  }
                >
                  <ChevronRight size={17} />
                </button>
              </div>
              <label className="date-picker">
                <CalendarDays size={14} />
                <span>
                  {view === "day"
                    ? longDate(selected)
                    : `${shortDate(dates[0])} – ${shortDate(dates[6])}`}
                </span>
                <ChevronDown size={13} />
                <input
                  type="date"
                  aria-label="Choose date"
                  value={selected}
                  onChange={(e) => {
                    if (e.target.value) setSelected(e.target.value);
                  }}
                />
              </label>
            </div>
            <div className="view-switch" aria-label="Checklist view">
              <button
                className={view === "day" ? "active" : ""}
                onClick={() => setView("day")}
                aria-pressed={view === "day"}
              >
                <ListChecks size={14} />
                Day
              </button>
              <button
                className={view === "week" ? "active" : ""}
                onClick={() => setView("week")}
                aria-pressed={view === "week"}
              >
                <CalendarDays size={14} />
                Week
              </button>
            </div>
          </div>
          <div className="content-grid">
            <div className="main-column">
              <section className="stats-grid" aria-label="Daily summary">
                <div className="stat-card">
                  <span className="stat-icon">
                    <CheckCheck size={18} />
                  </span>
                  <div>
                    <p>Completed</p>
                    <strong>
                      {completed}
                      <span> / {dayHabits.length}</span>
                    </strong>
                    <small>
                      {completed === dayHabits.length && completed > 0
                        ? "Mission accomplished"
                        : "One win at a time"}
                    </small>
                  </div>
                </div>
                <div className="stat-card">
                  <span className="stat-icon amber">
                    <Flame size={18} />
                  </span>
                  <div>
                    <p>Current streak</p>
                    <strong>
                      {streak}
                      <span> {streak === 1 ? "day" : "days"}</span>
                    </strong>
                    <small>Complete days in a row</small>
                  </div>
                </div>
                <div className="stat-card">
                  <span className="stat-icon blue">
                    <Target size={18} />
                  </span>
                  <div>
                    <p>Daily progress</p>
                    <strong>
                      {progress}
                      <span>%</span>
                    </strong>
                    <div className="stat-progress">
                      <span style={{ width: `${progress}%` }} />
                    </div>
                  </div>
                </div>
              </section>
              {view === "day" ? (
                <section className="checklist-section">
                  <div className="section-heading">
                    <div>
                      <h2>
                        Daily checklist
                        <span className="count-badge">{dayHabits.length}</span>
                      </h2>
                      <p>
                        <Repeat2 size={12} />
                        Every day. In your own order.
                      </p>
                    </div>
                    <div className="filter-tabs" aria-label="Filter habits">
                      {["All", "To do", "Done"].map((f) => (
                        <button
                          key={f}
                          className={filter === f ? "active" : ""}
                          onClick={() => setFilter(f)}
                          aria-pressed={filter === f}
                        >
                          {f}
                          {f === "All" && <span>{dayHabits.length}</span>}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div className="habit-list">
                    {visibleHabits.map((habit) => (
                      <HabitCard
                        key={habit.id}
                        habit={habit}
                        index={dayHabits.findIndex((h) => h.id === habit.id)}
                        onToggle={() => toggle(habit.id)}
                        onEdit={() => setEditor({ habit, date: selected })}
                        onDelete={() => removeHabit(habit)}
                      />
                    ))}
                    {visibleHabits.length === 0 && (
                      <div className="empty-state">
                        <CheckCheck size={32} />
                        <h3>
                          {filter === "To do" && completed > 0
                            ? "Mission accomplished."
                            : "A little open space."}
                        </h3>
                        <p>
                          {dayHabits.length
                            ? "Nothing in this view. Try another filter."
                            : "Add a habit to build your daily routine."}
                        </p>
                        <button
                          className="button secondary"
                          onClick={() =>
                            dayHabits.length
                              ? setFilter("All")
                              : setEditor({ habit: null, date: selected })
                          }
                        >
                          {dayHabits.length ? "Show all habits" : "Add a habit"}
                          <ArrowRight size={14} />
                        </button>
                      </div>
                    )}
                  </div>
                  <button
                    className="add-to-routine"
                    onClick={() => setEditor({ habit: null, date: selected })}
                  >
                    <Plus size={15} />
                    <span>Add something worth repeating</span>
                    <kbd>N</kbd>
                  </button>
                  <div
                    className={`daily-progress-card ${progress === 100 ? "all-complete" : ""}`}
                  >
                    <span className="progress-symbol">
                      {progress === 100 ? (
                        <ShieldCheck size={21} />
                      ) : (
                        <Zap size={21} />
                      )}
                    </span>
                    <div>
                      <strong>
                        {progress === 100
                          ? "All done. All you."
                          : "You don’t need a perfect day."}
                      </strong>
                      <p>
                        {progress === 100
                          ? "Every habit checked. Let’s do it again tomorrow."
                          : "Just a few good things, done consistently."}
                      </p>
                    </div>
                    <span className="progress-fraction">
                      {completed}/{dayHabits.length}
                    </span>
                  </div>
                </section>
              ) : (
                <section className="week-section">
                  <div className="section-heading">
                    <div>
                      <h2>Your week at a glance</h2>
                      <p>Same routine. A fresh start each day.</p>
                    </div>
                    <span className="week-legend">
                      <span />
                      Complete
                    </span>
                  </div>
                  <div
                    className="week-scroll"
                    tabIndex={0}
                    aria-label="Weekly habit tracker"
                  >
                    <table className="week-table">
                      <thead>
                        <tr>
                          <th scope="col">DAILY HABIT</th>
                          {dates.map((d) => (
                            <th
                              key={d}
                              scope="col"
                              className={d === today ? "week-today" : ""}
                            >
                              <button
                                className="week-date"
                                aria-label={`Open ${longDate(d)}`}
                                onClick={() => chooseDay(d)}
                              >
                                <span>
                                  {fromKey(d).toLocaleDateString("en-US", {
                                    weekday: "short",
                                  })}
                                </span>
                                <strong>{fromKey(d).getDate()}</strong>
                              </button>
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {weekHabits.map((habit) => {
                          const Icon = habitIcons[habit.icon];
                          return (
                            <tr key={habit.id}>
                              <th scope="row">
                                <span
                                  className={`week-habit-name category-${habit.category.toLowerCase()}`}
                                >
                                  <Icon size={15} />
                                  {habit.title}
                                </span>
                              </th>
                              {dates.map((d) => {
                                const done = (
                                  data.completions[d] ?? []
                                ).includes(habit.id);
                                return (
                                  <td
                                    key={d}
                                    className={d === today ? "week-today" : ""}
                                  >
                                    {isActive(habit, d) ? (
                                      <button
                                        className={`habit-check ${done ? "checked" : ""}`}
                                        role="checkbox"
                                        aria-checked={done}
                                        aria-label={`${done ? "Mark incomplete" : "Mark complete"}: ${habit.title} on ${shortDate(d)}`}
                                        onClick={() => toggle(habit.id, d)}
                                      >
                                        <Check size={13} />
                                      </button>
                                    ) : (
                                      <span
                                        className="inactive-day"
                                        aria-label="Not in routine on this day"
                                      >
                                        —
                                      </span>
                                    )}
                                  </td>
                                );
                              })}
                            </tr>
                          );
                        })}
                      </tbody>
                      <tfoot>
                        <tr>
                          <th scope="row">DAILY TOTAL</th>
                          {dates.map((d) => {
                            const habits = habitsForDate(data, d);
                            return (
                              <td key={d}>
                                {habits.filter((h) => h.done).length}
                                <span>/{habits.length}</span>
                              </td>
                            );
                          })}
                        </tr>
                      </tfoot>
                    </table>
                  </div>
                  <p className="week-footnote">
                    <Repeat2 size={13} />
                    Click any square to track that day. Your progress is always
                    saved.
                  </p>
                </section>
              )}
            </div>
            <aside className="right-column">
              <section className="focus-card">
                <div className="card-topline">
                  <span>
                    <Crosshair size={14} />
                    FOCUS MODE
                  </span>
                  <span className={`live-dot ${deadline ? "running" : ""}`} />
                </div>
                <h2>Lock in.</h2>
                <p>One thing. Your full attention.</p>
                <div
                  className="timer-orbit"
                  style={
                    {
                      "--timer-progress": `${((FOCUS_SECONDS - remaining) / FOCUS_SECONDS) * 100}%`,
                    } as React.CSSProperties
                  }
                >
                  <span className="orbit-mark top" />
                  <span className="orbit-mark right" />
                  <span className="orbit-mark bottom" />
                  <span className="orbit-mark left" />
                  <div className="timer-inner">
                    <span className="timer-label">
                      {deadline
                        ? "IN THE ZONE"
                        : remaining === 0
                          ? "SESSION COMPLETE"
                          : "READY WHEN YOU ARE"}
                    </span>
                    <div
                      className="timer"
                      role="timer"
                      aria-label={`${Math.floor(remaining / 60)} minutes ${remaining % 60} seconds remaining`}
                    >
                      {String(Math.floor(remaining / 60)).padStart(2, "0")}
                      <span>:</span>
                      {String(remaining % 60).padStart(2, "0")}
                    </div>
                    <span className="timer-duration">30 MIN / SESSION</span>
                  </div>
                </div>
                <label className="focus-task-select">
                  <Crosshair size={13} />
                  <span className="sr-only">Choose focus habit</span>
                  <select
                    value={
                      dayHabits.some((h) => h.id === focusTask && !h.done)
                        ? focusTask
                        : ""
                    }
                    onChange={(e) => setFocusTask(e.target.value)}
                  >
                    <option value="">Choose your focus</option>
                    {dayHabits
                      .filter((h) => !h.done)
                      .map((h) => (
                        <option key={h.id} value={h.id}>
                          {h.title}
                        </option>
                      ))}
                  </select>
                  <ChevronDown size={12} />
                </label>
                <div className="timer-actions">
                  <button
                    className="button focus-start"
                    onClick={() => {
                      if (deadline) {
                        setRemaining(
                          Math.max(
                            0,
                            Math.ceil((deadline - Date.now()) / 1000),
                          ),
                        );
                        setDeadline(null);
                      } else {
                        const seconds =
                          remaining > 0 ? remaining : FOCUS_SECONDS;
                        setRemaining(seconds);
                        completedDeadline.current = null;
                        setDeadline(Date.now() + seconds * 1000);
                      }
                    }}
                  >
                    {deadline ? (
                      <Pause size={13} fill="currentColor" />
                    ) : (
                      <Play size={13} fill="currentColor" />
                    )}
                    {deadline
                      ? "Pause focus"
                      : remaining === 0
                        ? "Start again"
                        : remaining < FOCUS_SECONDS
                          ? "Resume focus"
                          : "Start focus"}
                  </button>
                  <button
                    className="timer-reset"
                    aria-label="Reset focus timer"
                    onClick={() => {
                      setDeadline(null);
                      setRemaining(FOCUS_SECONDS);
                    }}
                  >
                    <RotateCcw size={15} />
                  </button>
                </div>
                <p className="focus-footnote">
                  <span />
                  {data.focusSessions[today] ?? 0}{" "}
                  {data.focusSessions[today] === 1 ? "session" : "sessions"}{" "}
                  completed today
                </p>
              </section>
              <section className="notes-card">
                <div className="notes-heading">
                  <span>
                    <Pencil size={15} />
                    Field notes
                  </span>
                  <button
                    className="icon-button small"
                    onClick={() => setDialog("notes")}
                    aria-label="Expand daily note"
                  >
                    <ArrowRight size={15} />
                  </button>
                </div>
                <textarea
                  aria-label="Daily note"
                  placeholder={
                    "Clear your head. Put it on paper.\nA thought, a reminder, a small win…"
                  }
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  maxLength={10000}
                />
                <div className="notes-footer">
                  <span>{shortDate(selected)}</span>
                  <span>
                    <span />
                    AUTO-SAVED
                  </span>
                </div>
              </section>
              <div className="aviation-card">
                <img
                  src="/images/afterburner.png"
                  alt="Fighter jet above the clouds in warm evening light"
                  loading="lazy"
                />
                <div>
                  <Plane size={16} />
                  <p>
                    Keep your eyes
                    <br />
                    on the horizon.
                  </p>
                  <span>PROGRESS IS A DAILY PRACTICE.</span>
                </div>
              </div>
            </aside>
          </div>
          <footer className="page-footer">
            <span>
              <Plane size={13} />A little discipline. A different altitude.
            </span>
            <span>
              YOUR EVERYDAY, ELEVATED.
              <span className="footer-dot" />
            </span>
          </footer>
        </main>
      </div>
      {editor && (
        <HabitEditor
          habit={editor.habit}
          selected={editor.date}
          onSave={saveHabit}
          onClose={() => setEditor(null)}
        />
      )}
      {dialog === "notes" && (
        <Dialog
          title="Clear skies. Clear mind."
          description={longDate(selected)}
          onClose={() => setDialog(null)}
          className="notebook-dialog"
        >
          <label className="field">
            <span className="sr-only">Notes for selected day</span>
            <textarea
              autoFocus
              rows={12}
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="An idea, a small win, something to remember…"
              maxLength={10000}
            />
          </label>
          <div className="dialog-footer">
            <span className="muted">Saved automatically with this day.</span>
            <button className="button primary" onClick={() => setDialog(null)}>
              All done
              <Check size={15} />
            </button>
          </div>
        </Dialog>
      )}
      {dialog === "settings" && (
        <Dialog
          title="Your personal cockpit."
          description="Make this space yours."
          onClose={() => setDialog(null)}
        >
          <label className="field">
            What should we call you?
            <input
              value={data.name}
              onChange={(e) =>
                setData((prev) => ({ ...prev, name: e.target.value }))
              }
              maxLength={30}
              placeholder="Your first name"
            />
          </label>
          <div className="settings-focus">
            <Crosshair size={20} />
            <div>
              <strong>30-minute focus sessions</strong>
              <span>A fixed block to practice, learn, or create.</span>
            </div>
            <span>30:00</span>
          </div>
          <p className="settings-copy">
            <ShieldCheck size={18} />
            Your routine, checkmarks, and notes stay in this browser. Export a
            copy to keep a backup. Earlier planner data is preserved in your
            export.
          </p>
          <div className="dialog-footer">
            <button className="button secondary" onClick={exportPlan}>
              <ArrowDownToLine size={15} />
              Export my plan
            </button>
            <button className="button primary" onClick={() => setDialog(null)}>
              All set
              <Check size={15} />
            </button>
          </div>
        </Dialog>
      )}
      {dialog === "help" && (
        <Dialog
          title="Your daily briefing."
          description="A simple routine. Room to get better."
          onClose={() => setDialog(null)}
        >
          <div className="help-list">
            <p>
              <Repeat2 size={22} />
              <span>
                <strong>A fresh checklist, every day</strong>Your six habits
                repeat daily without time slots. Each day keeps its own
                checkmarks. If you leave today open overnight, it rolls into a
                fresh day automatically.
              </span>
            </p>
            <p>
              <CheckCheck size={22} />
              <span>
                <strong>Tick on. Tick off.</strong>Click any square to mark a
                habit complete. Click again to undo it. Open the weekly view to
                check any day.
              </span>
            </p>
            <p>
              <Pencil size={22} />
              <span>
                <strong>Your routine can evolve</strong>Click a habit’s title to
                edit it, or press <kbd>N</kbd> to add one. Removing a habit
                affects the selected day and later days; earlier progress stays
                saved.
              </span>
            </p>
            <p>
              <Crosshair size={22} />
              <span>
                <strong>30 minutes of focus</strong>Pick a habit and start.
                Pause, resume, or reset when you need to. Completed sessions are
                counted for today. Reloading resets a running timer.
              </span>
            </p>
            <p>
              <Flame size={22} />
              <span>
                <strong>Build your streak</strong>Check every habit to complete
                a day. Consecutive completed days make a streak; today gives you
                until midnight to keep it going.
              </span>
            </p>
          </div>
          <div className="dialog-footer">
            <button className="button primary" onClick={() => setDialog(null)}>
              Ready for takeoff
              <ArrowRight size={15} />
            </button>
          </div>
        </Dialog>
      )}
      {toast && (
        <div className="toast" role="status">
          <Check size={16} />
          <span>{toast.message}</span>
          {toast.removed && (
            <button
              onClick={() => {
                const habit = toast.removed!;
                setData((prev) => ({
                  ...prev,
                  habits: prev.habits.map((h) =>
                    h.id === habit.id ? habit : h,
                  ),
                }));
                setToast({ message: "Habit restored. Back on course." });
              }}
            >
              Undo
            </button>
          )}
          <button
            className="toast-close"
            aria-label="Dismiss notification"
            onClick={() => setToast(null)}
          >
            <X size={14} />
          </button>
        </div>
      )}
    </div>
  );
}

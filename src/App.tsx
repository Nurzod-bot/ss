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
  Clock3,
  Coffee,
  Ellipsis,
  Flower2,
  Focus,
  Leaf,
  ListTodo,
  Menu,
  MoreHorizontal,
  Pause,
  Pencil,
  Play,
  Plus,
  RotateCcw,
  Settings2,
  Sparkles,
  Sun,
  Trash2,
  X,
  type LucideIcon,
} from "lucide-react";
import {
  CATEGORIES,
  clock,
  dateKey,
  duration,
  fromKey,
  loadData,
  meridiem,
  minutes,
  plannedMinutes,
  readableDuration,
  shiftDate,
  STORAGE_KEY,
  weekDates,
  type Category,
  type PlannerData,
  type Task,
} from "./model";

const categoryIcons: Record<Category, LucideIcon> = {
  Focus,
  Work: Coffee,
  Personal: BookOpen,
  Wellness: Leaf,
};
const longDate = (key: string) =>
  fromKey(key).toLocaleDateString("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
  });

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
          <p className="eyebrow">A LITTLE MORE INTENTIONAL</p>
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

function PlantIllustration() {
  return (
    <svg
      className="plant-illustration"
      viewBox="0 0 260 142"
      fill="none"
      aria-hidden="true"
    >
      <circle cx="130" cy="76" r="58" fill="#e2e8d8" />
      <circle cx="182" cy="30" r="14" fill="#e9d7a4" opacity=".8" />
      <path
        d="M42 120c24-8 41-6 59-1m60 0c22-6 39-6 61 1"
        stroke="#c7d1b9"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
      <path
        d="M126 105c-3-33 0-51 12-77m-8 58c-11-6-22-17-27-33m28 21c10-5 21-14 25-29"
        stroke="#718466"
        strokeWidth="2"
        strokeLinecap="round"
      />
      <path d="M133 55c-2-17 2-27 15-31 4 15-2 26-15 31Z" fill="#718466" />
      <path d="M122 76c-18-1-29-12-29-27 16 2 26 11 29 27Z" fill="#93a284" />
      <path d="M130 84c2-19 13-30 30-30-2 17-12 28-30 30Z" fill="#b2be9d" />
      <path d="M126 95c-16-1-26-9-30-22 16 0 27 8 30 22Z" fill="#718466" />
      <path d="M109 103h36l-5 28h-26l-5-28Z" fill="#d2b89a" />
      <path d="M109 103h36v5h-36z" fill="#c6a98a" />
      <path
        d="M118 112l2 15m8-15v15m9-15-2 15"
        stroke="#b89574"
        strokeWidth="1"
        opacity=".5"
      />
      <path
        d="M65 67v8m-4-4h8m116 27v8m-4-4h8"
        stroke="#9aaa88"
        strokeLinecap="round"
      />
      <circle cx="180" cy="65" r="2" fill="#9aaa88" />
      <circle cx="79" cy="101" r="2" fill="#9aaa88" />
    </svg>
  );
}

function TaskCard({
  task,
  onToggle,
  onEdit,
  onDelete,
}: {
  task: Task;
  onToggle: () => void;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const Icon = categoryIcons[task.category];
  useEffect(() => {
    if (!menuOpen) return;
    const close = (e: MouseEvent) => {
      if (!ref.current?.contains(e.target as Node)) setMenuOpen(false);
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
    <div className={`timeline-row ${task.done ? "completed" : ""}`}>
      <div className="time-label">
        <strong>{clock(task.start)}</strong>
        <span>{meridiem(task.start)}</span>
      </div>
      <div className="timeline-track">
        <span />
      </div>
      <article className={`task-card category-${task.category.toLowerCase()}`}>
        <button
          className={`task-check ${task.done ? "checked" : ""}`}
          onClick={onToggle}
          aria-label={`${task.done ? "Mark incomplete" : "Mark complete"}: ${task.title}`}
          role="checkbox"
          aria-checked={task.done}
        >
          {task.done && <Check size={14} strokeWidth={2.7} />}
        </button>
        <div className="task-content">
          <button className="task-title" onClick={onEdit}>
            {task.title}
          </button>
          <p className="task-description">
            {task.notes || "A little time for what matters."}
          </p>
          <div className="task-meta">
            <span className="category-pill">
              <Icon size={11} />
              {task.category}
            </span>
            <span className="task-duration">
              <Clock3 size={11} />
              {clock(task.start)} – {clock(task.end)} {meridiem(task.end)}
              <span className="meta-dot">·</span>
              {readableDuration(duration(task))}
            </span>
          </div>
        </div>
        <div className="task-menu" ref={ref}>
          <button
            className="icon-button"
            onClick={() => setMenuOpen(!menuOpen)}
            aria-label={`Options for ${task.title}`}
            aria-expanded={menuOpen}
          >
            <MoreHorizontal size={19} />
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
                Edit task
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
                Delete task
              </button>
            </div>
          )}
        </div>
      </article>
    </div>
  );
}

function TaskEditor({
  task,
  selected,
  tasks,
  onSave,
  onClose,
}: {
  task: Task | null;
  selected: string;
  tasks: Task[];
  onSave: (task: Task) => void;
  onClose: () => void;
}) {
  const [title, setTitle] = useState(task?.title ?? "");
  const [date, setDate] = useState(task?.date ?? selected);
  const [start, setStart] = useState(task?.start ?? "09:00");
  const [end, setEnd] = useState(task?.end ?? "10:00");
  const [category, setCategory] = useState<Category>(task?.category ?? "Focus");
  const [notes, setNotes] = useState(task?.notes ?? "");
  const [error, setError] = useState("");
  const overlaps = tasks.filter(
    (t) =>
      t.id !== task?.id &&
      t.date === date &&
      minutes(t.start) < minutes(end) &&
      minutes(t.end) > minutes(start),
  );
  return (
    <Dialog
      title={task ? "Make a little adjustment." : "Make time for something."}
      description={
        task
          ? "Your plan can change with you."
          : "Big plans or small moments. They all belong here."
      }
      onClose={onClose}
    >
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (!title.trim()) {
            setError("Give your task a name.");
            return;
          }
          if (minutes(end) <= minutes(start)) {
            setError("Choose an end time after the start time.");
            return;
          }
          onSave({
            id: task?.id ?? crypto.randomUUID(),
            date,
            title: title.trim(),
            start,
            end,
            category,
            notes: notes.trim(),
            done: task?.done ?? false,
          });
        }}
      >
        <label className="field">
          What’s the plan?
          <input
            autoFocus
            required
            maxLength={120}
            placeholder="e.g. A little time to create"
            value={title}
            onChange={(e) => {
              setTitle(e.target.value);
              setError("");
            }}
          />
        </label>
        <label className="field">
          Day
          <input
            type="date"
            required
            value={date}
            onChange={(e) => setDate(e.target.value)}
          />
        </label>
        <div className="form-row">
          <label className="field">
            Start time
            <input
              type="time"
              required
              value={start}
              onChange={(e) => {
                setStart(e.target.value);
                setError("");
              }}
            />
          </label>
          <label className="field">
            End time
            <input
              type="time"
              required
              value={end}
              onChange={(e) => {
                setEnd(e.target.value);
                setError("");
              }}
            />
          </label>
        </div>
        <fieldset className="category-field">
          <legend>A little category</legend>
          <div className="category-options">
            {CATEGORIES.map((c) => {
              const Icon = categoryIcons[c];
              return (
                <button
                  key={c}
                  type="button"
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
          A note <span className="optional">(optional)</span>
          <textarea
            rows={2}
            maxLength={500}
            placeholder="Anything you’d like to remember…"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
          />
        </label>
        {error && (
          <p role="alert" className="form-error">
            {error}
          </p>
        )}
        {!error && overlaps.length > 0 && minutes(end) > minutes(start) && (
          <p className="form-notice">
            This shares time with “{overlaps[0].title}”. You can still save it.
          </p>
        )}
        <div className="dialog-footer">
          <button type="button" className="button secondary" onClick={onClose}>
            Cancel
          </button>
          <button className="button primary" type="submit">
            <Check size={16} />
            {task ? "Save changes" : "Add to my day"}
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
  const [selected, setSelected] = useState(() => dateKey(new Date()));
  const [view, setView] = useState<"day" | "week">("day");
  const [filter, setFilter] = useState("All tasks");
  const [editor, setEditor] = useState<{
    task: Task | null;
    date: string;
  } | null>(null);
  const [dialog, setDialog] = useState<"notes" | "settings" | "help" | null>(
    null,
  );
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [toast, setToast] = useState<{
    message: string;
    deleted?: Task;
  } | null>(null);
  const [focusTask, setFocusTask] = useState("");
  const [remaining, setRemaining] = useState(data.focusMinutes * 60);
  const [deadline, setDeadline] = useState<number | null>(null);
  const notesRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (!canPersist) return;
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
      setStorageWarning(null);
    } catch {
      setStorageWarning(
        "Browser storage is unavailable. Export your plan to keep a copy before closing this tab.",
      );
    }
  }, [data, canPersist]);
  useEffect(() => {
    if (!toast) return;
    const id = window.setTimeout(() => setToast(null), 6000);
    return () => window.clearTimeout(id);
  }, [toast]);
  useEffect(() => {
    setRemaining(data.focusMinutes * 60);
    setDeadline(null);
  }, [data.focusMinutes]);
  useEffect(() => {
    if (deadline === null) return;
    const tick = () => {
      const left = Math.max(0, Math.ceil((deadline - Date.now()) / 1000));
      setRemaining(left);
      if (left === 0) {
        setDeadline(null);
        setToast({
          message: "Focus session complete. Take a well-earned breath.",
        });
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
        setEditor({ task: null, date: selected });
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [selected]);

  const today = dateKey(new Date());
  const dayTasks = data.tasks
    .filter((t) => t.date === selected)
    .sort((a, b) => a.start.localeCompare(b.start));
  const completed = dayTasks.filter((t) => t.done).length;
  const progress = dayTasks.length
    ? Math.round((completed / dayTasks.length) * 100)
    : 0;
  const planned = plannedMinutes(dayTasks);
  const filteredTasks = dayTasks.filter(
    (t) =>
      filter === "All tasks" ||
      (filter === "Completed"
        ? t.done
        : filter === "To do"
          ? !t.done
          : t.category === filter),
  );
  const dates = weekDates(selected);
  const note = data.notes[selected] ?? "";
  const setNote = (value: string) =>
    setData((prev) => ({
      ...prev,
      notes: { ...prev.notes, [selected]: value },
    }));
  const toggle = (id: string) =>
    setData((prev) => ({
      ...prev,
      tasks: prev.tasks.map((t) => (t.id === id ? { ...t, done: !t.done } : t)),
    }));
  const deleteTask = (task: Task) => {
    setData((prev) => ({
      ...prev,
      tasks: prev.tasks.filter((t) => t.id !== task.id),
    }));
    setToast({
      message: "Task removed. A little more breathing room.",
      deleted: task,
    });
  };
  const chooseDay = (key: string) => {
    setSelected(key);
    setView("day");
    setSidebarOpen(false);
  };
  const saveTask = (task: Task) => {
    setData((prev) => ({
      ...prev,
      tasks: prev.tasks.some((t) => t.id === task.id)
        ? prev.tasks.map((t) => (t.id === task.id ? task : t))
        : [...prev.tasks, task],
    }));
    setSelected(task.date);
    setFilter("All tasks");
    setEditor(null);
    setToast({
      message: editor?.task
        ? "Your plan has been updated."
        : "A little intention, added to your day.",
    });
  };
  const exportPlan = () => {
    const blob = new Blob(
      [
        JSON.stringify(
          { ...data, exportedAt: new Date().toISOString() },
          null,
          2,
        ),
      ],
      { type: "application/json" },
    );
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `daylight-plan-${today}.json`;
    a.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    setToast({ message: "Your plan has been exported." });
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
            <Sun size={30} strokeWidth={1.6} />
          </span>
          <span>
            daylight<span className="brand-dot">.</span>
          </span>
        </a>
        <p className="brand-tagline">A little more intentional.</p>
        <p className="nav-label">YOUR SPACE</p>
        <nav className="main-nav" aria-label="Main navigation">
          <button
            className={view === "day" ? "active" : ""}
            onClick={() => {
              setView("day");
              setSidebarOpen(false);
            }}
          >
            <ListTodo size={18} />
            <span>My day</span>
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
            <span>My week</span>
            <span className="nav-shortcut">7</span>
          </button>
          <button
            onClick={() => {
              setDialog("notes");
              setSidebarOpen(false);
            }}
          >
            <BookOpen size={18} />
            <span>My notes</span>
          </button>
        </nav>
        <MiniCalendar selected={selected} onSelect={chooseDay} />
        <div className="sidebar-bottom">
          <div className="gentle-reminder">
            <span className="reminder-icon">
              <Flower2 size={23} strokeWidth={1.4} />
            </span>
            <p>
              Your pace is
              <br />
              <em>the right pace.</em>
            </p>
            <span>
              Make space for what matters.
              <br />
              Leave a little room for you.
            </span>
          </div>
          <button className="help-button" onClick={() => setDialog("help")}>
            <CircleHelp size={16} />A little help
            <ArrowRight size={14} />
          </button>
          <button
            className="workspace-button"
            onClick={() => setDialog("settings")}
            aria-label="Open planner settings"
          >
            <span className="avatar">
              {data.name ? data.name[0].toUpperCase() : <Sun size={19} />}
            </span>
            <span>
              <strong>{data.name || "My workspace"}</strong>
              <small>Your personal planner</small>
            </span>
            <Settings2 size={16} />
          </button>
        </div>
      </aside>

      <div className="workspace">
        <header className="topbar">
          <div className="breadcrumb">
            <button
              className="icon-button mobile-menu"
              onClick={() => setSidebarOpen(true)}
              aria-label="Open navigation"
            >
              <Menu size={21} />
            </button>
            <Sun size={16} />
            <span>My space</span>
            <ChevronRight size={13} />
            <strong>{view === "day" ? "My day" : "My week"}</strong>
          </div>
          <div className="topbar-right">
            <span
              className={`save-indicator ${storageWarning ? "warning" : ""}`}
            >
              <span />
              {storageWarning ? "Not saved" : "All changes saved"}
            </span>
            <button
              className="top-avatar"
              onClick={() => setDialog("settings")}
              aria-label="Planner settings"
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
                <button
                  onClick={() => {
                    try {
                      const raw = localStorage.getItem(STORAGE_KEY);
                      if (raw)
                        localStorage.setItem(
                          `${STORAGE_KEY}-recovery-${Date.now()}`,
                          raw,
                        );
                      setCanPersist(true);
                    } catch {
                      setStorageWarning(
                        "Could not back up your old plan. Browser storage may be full.",
                      );
                    }
                  }}
                >
                  Back up old data & save
                </button>
              )}
            </div>
          )}
          <section className="page-heading">
            <div>
              <p className="eyebrow">
                <span className="tiny-sun">✳</span>
                {longDate(selected).toUpperCase()}
              </p>
              <h1>
                {view === "day" ? (
                  <>
                    A day with <em>intention.</em>
                  </>
                ) : (
                  <>
                    See the <em>bigger picture.</em>
                  </>
                )}
              </h1>
              <p className="heading-description">
                {data.name ? `${data.name}, a` : "A"} little structure. A little
                breathing room. A day that feels like you.
              </p>
            </div>
            <button
              className="button primary add-task"
              onClick={() => setEditor({ task: null, date: selected })}
            >
              <Plus size={17} />
              Add task<span className="keyboard-hint">N</span>
            </button>
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
                <CalendarDays size={15} />
                <span>
                  {view === "day"
                    ? fromKey(selected).toLocaleDateString("en-US", {
                        month: "short",
                        day: "numeric",
                        year: "numeric",
                      })
                    : `${fromKey(dates[0]).toLocaleDateString("en-US", { month: "short", day: "numeric" })} – ${fromKey(dates[6]).toLocaleDateString("en-US", { month: "short", day: "numeric" })}`}
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
            <div className="view-switch" aria-label="Schedule view">
              <button
                className={view === "day" ? "active" : ""}
                onClick={() => setView("day")}
                aria-pressed={view === "day"}
              >
                <ListTodo size={14} />
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
                  <span className="stat-icon sage">
                    <CheckCheck size={19} strokeWidth={1.6} />
                  </span>
                  <div>
                    <p>Tasks completed</p>
                    <strong>
                      {completed}
                      <span> / {dayTasks.length}</span>
                    </strong>
                    <span className="stat-caption">
                      {completed === dayTasks.length && completed > 0
                        ? "Look at you go!"
                        : "One little win at a time"}
                    </span>
                  </div>
                  <span
                    className="mini-ring"
                    style={
                      { "--progress": `${progress}%` } as React.CSSProperties
                    }
                  >
                    <span>{progress}%</span>
                  </span>
                </div>
                <div className="stat-card">
                  <span className="stat-icon peach">
                    <Clock3 size={19} strokeWidth={1.6} />
                  </span>
                  <div>
                    <p>Time planned</p>
                    <strong>{readableDuration(planned)}</strong>
                    <span className="stat-caption">
                      For the things that matter
                    </span>
                  </div>
                </div>
                <div className="stat-card">
                  <span className="stat-icon lavender">
                    <Coffee size={19} strokeWidth={1.6} />
                  </span>
                  <div>
                    <p>Room to breathe</p>
                    <strong>
                      {readableDuration(Math.max(0, 12 * 60 - planned))}
                    </strong>
                    <span className="stat-caption">
                      In a 12-hour waking day
                    </span>
                  </div>
                </div>
              </section>

              {view === "day" ? (
                <section className="schedule-section">
                  <div className="section-heading">
                    <div>
                      <h2>
                        Your schedule{" "}
                        <span className="count-badge">{dayTasks.length}</span>
                      </h2>
                      <p>A little plan for a lovely day.</p>
                    </div>
                    <label className="filter-select">
                      <span className="sr-only">Filter tasks</span>
                      <select
                        value={filter}
                        onChange={(e) => setFilter(e.target.value)}
                      >
                        <option>All tasks</option>
                        <option>To do</option>
                        <option>Completed</option>
                        {CATEGORIES.map((c) => (
                          <option key={c}>{c}</option>
                        ))}
                      </select>
                      <ChevronDown size={13} />
                    </label>
                  </div>
                  <div className="timeline">
                    {filteredTasks.map((task) => (
                      <TaskCard
                        key={task.id}
                        task={task}
                        onToggle={() => toggle(task.id)}
                        onEdit={() => setEditor({ task, date: selected })}
                        onDelete={() => deleteTask(task)}
                      />
                    ))}
                    {filteredTasks.length === 0 && (
                      <div className="empty-state">
                        <Sun size={34} strokeWidth={1.3} />
                        <h3>
                          {dayTasks.length
                            ? "Nothing here, just yet."
                            : "A little room for possibility."}
                        </h3>
                        <p>
                          {dayTasks.length
                            ? "Try another filter to find your tasks."
                            : "Start with one thing you’d like to make time for."}
                        </p>
                        <button
                          className="button secondary"
                          onClick={() =>
                            dayTasks.length
                              ? setFilter("All tasks")
                              : setEditor({ task: null, date: selected })
                          }
                        >
                          {dayTasks.length
                            ? "Show all tasks"
                            : "Plan my first task"}
                          <ArrowRight size={14} />
                        </button>
                      </div>
                    )}
                    {filteredTasks.length > 0 && (
                      <button
                        className="add-timeline"
                        onClick={() =>
                          setEditor({ task: null, date: selected })
                        }
                      >
                        <span className="add-timeline-icon">
                          <Plus size={15} />
                        </span>
                        <span>A little more to your day</span>
                        <span className="add-timeline-key">N</span>
                      </button>
                    )}
                  </div>
                  <div className="schedule-footnote">
                    <Leaf size={13} />
                    <span>
                      Your plan is a guide. It’s okay to change the pace.
                    </span>
                  </div>
                </section>
              ) : (
                <section className="week-section">
                  <div className="section-heading">
                    <div>
                      <h2>Your week at a glance</h2>
                      <p>A little perspective. Plenty of possibility.</p>
                    </div>
                  </div>
                  <div className="week-grid">
                    {dates.map((key) => {
                      const tasks = data.tasks
                        .filter((t) => t.date === key)
                        .sort((a, b) => a.start.localeCompare(b.start));
                      return (
                        <div
                          className={`week-day ${key === today ? "week-today" : ""}`}
                          key={key}
                        >
                          <button
                            className="week-date"
                            onClick={() => chooseDay(key)}
                          >
                            <span>
                              {fromKey(key).toLocaleDateString("en-US", {
                                weekday: "short",
                              })}
                            </span>
                            <strong>{fromKey(key).getDate()}</strong>
                            {key === today && <span className="today-dot" />}
                          </button>
                          <div className="week-tasks">
                            {tasks.map((t) => (
                              <button
                                key={t.id}
                                className={`week-task category-${t.category.toLowerCase()} ${t.done ? "done" : ""}`}
                                onClick={() =>
                                  setEditor({ task: t, date: key })
                                }
                              >
                                <span>
                                  {t.done ? (
                                    <Check size={11} />
                                  ) : (
                                    <span className="week-task-dot" />
                                  )}
                                  {clock(t.start)} {meridiem(t.start)}
                                </span>
                                <strong>{t.title}</strong>
                              </button>
                            ))}
                            {tasks.length === 0 && (
                              <p className="week-empty">A little open space</p>
                            )}
                          </div>
                          <button
                            className="week-add"
                            aria-label={`Add task for ${longDate(key)}`}
                            onClick={() => setEditor({ task: null, date: key })}
                          >
                            <Plus size={15} />
                          </button>
                        </div>
                      );
                    })}
                  </div>
                  <div className="week-summary">
                    <Leaf size={15} />
                    {
                      data.tasks.filter((t) => dates.includes(t.date)).length
                    }{" "}
                    intentions this week. Make room for yourself, too.
                  </div>
                </section>
              )}
            </div>

            <aside className="right-column">
              <section className="focus-card">
                <div className="card-topline">
                  <span>
                    <Focus size={15} />A MOMENT OF FOCUS
                  </span>
                  <span className={`live-dot ${deadline ? "running" : ""}`} />
                </div>
                <PlantIllustration />
                <h2>One thing at a time.</h2>
                <p>Settle in. Let the rest wait a little.</p>
                <div
                  className={`timer ${deadline ? "running" : ""}`}
                  role="timer"
                  aria-label={`${Math.floor(remaining / 60)} minutes ${remaining % 60} seconds remaining`}
                >
                  {String(Math.floor(remaining / 60)).padStart(2, "0")}
                  <span>:</span>
                  {String(remaining % 60).padStart(2, "0")}
                </div>
                <label className="focus-task-select">
                  <span className="sr-only">Choose focus task</span>
                  <select
                    value={
                      dayTasks.some((t) => t.id === focusTask && !t.done)
                        ? focusTask
                        : ""
                    }
                    onChange={(e) => setFocusTask(e.target.value)}
                  >
                    <option value="">
                      {remaining === 0
                        ? "Well done. Time for a little break."
                        : "What would you like to focus on?"}
                    </option>
                    {dayTasks
                      .filter((t) => !t.done)
                      .map((t) => (
                        <option key={t.id} value={t.id}>
                          {t.title}
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
                          remaining > 0 ? remaining : data.focusMinutes * 60;
                        setRemaining(seconds);
                        setDeadline(Date.now() + seconds * 1000);
                      }
                    }}
                  >
                    {deadline ? (
                      <Pause size={14} fill="currentColor" />
                    ) : (
                      <Play size={14} fill="currentColor" />
                    )}
                    {deadline
                      ? "Pause focus"
                      : remaining === 0
                        ? "Start again"
                        : remaining < data.focusMinutes * 60
                          ? "Resume focus"
                          : "Start focus"}
                  </button>
                  <button
                    className="timer-reset"
                    aria-label="Reset focus timer"
                    onClick={() => {
                      setDeadline(null);
                      setRemaining(data.focusMinutes * 60);
                    }}
                  >
                    <RotateCcw size={16} />
                  </button>
                </div>
                <span className="focus-footnote">
                  A little focus goes a long way.
                </span>
              </section>
              <section className="notes-card">
                <div className="notes-heading">
                  <span className="note-icon">
                    <Pencil size={15} />
                  </span>
                  <h2>A little note</h2>
                  <button
                    className="icon-button small"
                    onClick={() => {
                      notesRef.current?.focus();
                    }}
                    aria-label="Edit daily note"
                  >
                    <Ellipsis size={18} />
                  </button>
                </div>
                <textarea
                  ref={notesRef}
                  aria-label="Daily note"
                  placeholder={
                    "A thought, a reminder,\na little something for later…"
                  }
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                  maxLength={10000}
                />
                <div className="notes-footer">
                  <span>
                    {note
                      ? "Saved with your day"
                      : "Just for you. Always saved."}
                  </span>
                  <span className="note-scribble" aria-hidden="true">
                    <svg viewBox="0 0 44 32" fill="none">
                      <path
                        d="M5 22c12-3 25-15 23-19-3-4-11 5-10 12 1 6 10 6 19 1m-3-4 4 4-5 3"
                        stroke="currentColor"
                        strokeWidth="1.4"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  </span>
                </div>
              </section>
              <div className="daily-thought">
                <Sparkles size={15} strokeWidth={1.4} />
                <p>
                  “Almost everything will work again
                  <br />
                  if you unplug it for a few minutes,
                  <br />
                  <em>including you.</em>”
                </p>
                <span>— ANNE LAMOTT</span>
              </div>
            </aside>
          </div>
          <footer className="page-footer">
            <span>
              <Sun size={14} />A little progress, every day.
            </span>
            <span>
              Made for a more mindful day
              <span className="footer-flower">✳</span>
            </span>
          </footer>
        </main>
      </div>

      {editor && (
        <TaskEditor
          task={editor.task}
          selected={editor.date}
          tasks={data.tasks}
          onClose={() => setEditor(null)}
          onSave={saveTask}
        />
      )}
      {dialog === "notes" && (
        <Dialog
          title="A little space for your thoughts."
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
              placeholder="An idea, a gratitude, something to remember…"
              maxLength={10000}
            />
          </label>
          <div className="dialog-footer">
            <span className="muted">Saved automatically with your day.</span>
            <button className="button primary" onClick={() => setDialog(null)}>
              All done
              <Check size={15} />
            </button>
          </div>
        </Dialog>
      )}
      {dialog === "settings" && (
        <Dialog
          title="Make yourself at home."
          description="The little things that make this space yours."
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
          <label className="field">
            Your focus session
            <select
              value={data.focusMinutes}
              onChange={(e) =>
                setData((prev) => ({
                  ...prev,
                  focusMinutes: Number(e.target.value),
                }))
              }
            >
              {[15, 25, 45, 60].map((n) => (
                <option value={n} key={n}>
                  {n} minutes
                </option>
              ))}
            </select>
          </label>
          <p className="settings-copy">
            <Leaf size={18} />
            Your plans stay in this browser on this device. Export a copy
            whenever you’d like to keep a backup.
          </p>
          <div className="dialog-footer">
            <button className="button secondary" onClick={exportPlan}>
              <ArrowDownToLine size={15} />
              Export my plan
            </button>
            <button className="button primary" onClick={() => setDialog(null)}>
              Feels like me
              <Check size={15} />
            </button>
          </div>
        </Dialog>
      )}
      {dialog === "help" && (
        <Dialog
          title="A little help along the way."
          description="A simple space for a day that feels like you."
          onClose={() => setDialog(null)}
        >
          <div className="help-list">
            <p>
              <CheckCheck size={22} />
              <span>
                <strong>Little ticks, little wins</strong>Click the circle
                beside a task to complete it. Click again to bring it back.
              </span>
            </p>
            <p>
              <CalendarDays size={22} />
              <span>
                <strong>A plan that moves with you</strong>Pick a date in the
                calendar, or switch to Week to see the bigger picture.
              </span>
            </p>
            <p>
              <Pencil size={22} />
              <span>
                <strong>Always room for a change</strong>Click a task’s title to
                edit it. Its three-dot menu also lets you delete it.
              </span>
            </p>
            <p>
              <Focus size={22} />
              <span>
                <strong>A little room to focus</strong>Choose a task and start
                the timer. Set your preferred duration in settings.
              </span>
            </p>
            <p>
              <ListTodo size={22} />
              <span>
                <strong>Yours to keep</strong>The first day includes example
                tasks you can edit or remove. Plans and notes save in this
                browser. Export a backup in settings. Press <kbd>N</kbd> to add
                a task.
              </span>
            </p>
          </div>
          <div className="dialog-footer">
            <button className="button primary" onClick={() => setDialog(null)}>
              Let’s make a little progress
              <ArrowRight size={15} />
            </button>
          </div>
        </Dialog>
      )}
      {toast && (
        <div className="toast" role="status">
          <Check size={17} />
          <span>{toast.message}</span>
          {toast.deleted && (
            <button
              onClick={() => {
                const task = toast.deleted!;
                setData((prev) => ({
                  ...prev,
                  tasks: prev.tasks.some((t) => t.id === task.id)
                    ? prev.tasks
                    : [...prev.tasks, task],
                }));
                setToast({ message: "Task restored. Welcome back." });
              }}
            >
              Undo
            </button>
          )}
          <button
            className="toast-close"
            onClick={() => setToast(null)}
            aria-label="Dismiss notification"
          >
            <X size={14} />
          </button>
        </div>
      )}
    </div>
  );
}

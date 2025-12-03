import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
from datetime import datetime, timedelta, date

DATA_FILE = "dailyflow_data.json"


PRIORITY_SCORES = {
    "Low": 1,
    "Medium": 2,
    "High": 3,
    "Critical": 4,
}


class Task:
    def __init__(
        self,
        task_id,
        title,
        category="General",
        due_date=None,
        duration_minutes=60,
        priority="Medium",
        completed=False,
        start_time=None,
        end_time=None,
    ):
        self.id = task_id
        self.title = title
        self.category = category
        self.due_date = due_date  # string "YYYY-MM-DD" or None
        self.duration_minutes = duration_minutes
        self.priority = priority
        self.completed = completed
        self.start_time = start_time  # iso string or None
        self.end_time = end_time

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "category": self.category,
            "due_date": self.due_date,
            "duration_minutes": self.duration_minutes,
            "priority": self.priority,
            "completed": self.completed,
            "start_time": self.start_time,
            "end_time": self.end_time,
        }

    @staticmethod
    def from_dict(d):
        return Task(
            d["id"],
            d["title"],
            d.get("category", "General"),
            d.get("due_date"),
            d.get("duration_minutes", 60),
            d.get("priority", "Medium"),
            d.get("completed", False),
            d.get("start_time"),
            d.get("end_time"),
        )

    def score_for_today(self, today: date):
        """Higher score = more important to schedule earlier."""
        base = PRIORITY_SCORES.get(self.priority, 2)
        urgency = 0
        if self.due_date:
            try:
                d = datetime.strptime(self.due_date, "%Y-%m-%d").date()
                days_left = (d - today).days
                if days_left <= 0:
                    urgency = 3  # overdue / due today
                elif days_left == 1:
                    urgency = 2
                elif days_left <= 3:
                    urgency = 1
            except ValueError:
                pass
        # Longer tasks get a slight penalty so shorter chunks fit earlier
        length_penalty = min(1, self.duration_minutes / 240.0)
        return base + urgency - length_penalty


class DailyFlowApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        self.title("DailyFlow – Intelligent Day Planner")
        self.geometry("1150x700")
        self.minsize(950, 600)

        self.tasks = []
        self.next_task_id = 1

        self.load_data()

        self.build_ui()
        self.refresh_all_views()

    # ---------------- UI BUILD ----------------

    def build_ui(self):
        # Top bar
        top = ctk.CTkFrame(self, height=50, corner_radius=0)
        top.pack(side="top", fill="x")

        title_label = ctk.CTkLabel(
            top,
            text="DailyFlow",
            font=ctk.CTkFont("SF Pro Display", 22, weight="bold"),
        )
        title_label.pack(side="left", padx=18, pady=8)

        subtitle = ctk.CTkLabel(
            top,
            text="Smart day planner • Prioritize what matters",
            font=ctk.CTkFont(size=13),
            text_color="#6b7280",
        )
        subtitle.pack(side="left", pady=8)

        today_label = ctk.CTkLabel(
            top,
            text=date.today().strftime("Today: %a, %d %b %Y"),
            font=ctk.CTkFont(size=13),
            text_color="#4b5563",
        )
        today_label.pack(side="right", padx=16)

        # Main container
        main = ctk.CTkFrame(self, corner_radius=0)
        main.pack(fill="both", expand=True)

        # Left panel: Task creator + list
        left = ctk.CTkFrame(main, width=320, corner_radius=0)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        # Right panel: Planner & tabs
        right = ctk.CTkFrame(main, corner_radius=0)
        right.pack(side="right", fill="both", expand=True)

        self.build_left_panel(left)
        self.build_right_panel(right)

    def build_left_panel(self, parent):
        header = ctk.CTkLabel(
            parent,
            text="Add Task",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        header.pack(anchor="w", padx=16, pady=(16, 4))

        info = ctk.CTkLabel(
            parent,
            text="Create tasks with priority, due date and duration.\nDailyFlow will help plan your day.",
            font=ctk.CTkFont(size=11),
            text_color="#6b7280",
            justify="left",
        )
        info.pack(anchor="w", padx=16, pady=(0, 12))

        form = ctk.CTkFrame(parent)
        form.pack(fill="x", padx=14, pady=4)

        # Title
        ctk.CTkLabel(form, text="Title", anchor="w").grid(row=0, column=0, sticky="w")
        self.title_entry = ctk.CTkEntry(form, placeholder_text="e.g., Study OS Unit 3")
        self.title_entry.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 8))

        # Category
        ctk.CTkLabel(form, text="Category", anchor="w").grid(row=2, column=0, sticky="w")
        self.category_entry = ctk.CTkEntry(form, placeholder_text="e.g., Study, Work, Personal")
        self.category_entry.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 8))

        # Due date
        ctk.CTkLabel(form, text="Due date (YYYY-MM-DD)", anchor="w").grid(
            row=4, column=0, sticky="w"
        )
        self.due_entry = ctk.CTkEntry(form, placeholder_text="optional")
        self.due_entry.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(0, 8))

        # Duration
        ctk.CTkLabel(form, text="Duration (minutes)", anchor="w").grid(
            row=6, column=0, sticky="w"
        )
        self.duration_entry = ctk.CTkEntry(form, placeholder_text="60")
        self.duration_entry.grid(row=7, column=0, sticky="ew", pady=(0, 8))

        # Priority
        ctk.CTkLabel(form, text="Priority", anchor="w").grid(row=6, column=1, sticky="w")
        self.priority_option = ctk.CTkOptionMenu(
            form,
            values=["Low", "Medium", "High", "Critical"],
        )
        self.priority_option.set("Medium")
        self.priority_option.grid(row=7, column=1, sticky="ew", padx=(6, 0), pady=(0, 8))

        form.columnconfigure(0, weight=1)
        form.columnconfigure(1, weight=1)

        # Add button
        add_btn = ctk.CTkButton(
            parent,
            text="➕ Add Task",
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            command=self.add_task_from_form,
        )
        add_btn.pack(fill="x", padx=16, pady=(8, 4))

        # Subheader: All tasks
        ctk.CTkLabel(
            parent,
            text="All Tasks",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=16, pady=(14, 4))

        # Treeview for all tasks
        tree_frame = ctk.CTkFrame(parent)
        tree_frame.pack(fill="both", expand=True, padx=14, pady=(0, 10))

        columns = ("title", "category", "priority", "due", "duration", "status")
        self.tasks_tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            height=8,
        )
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tasks_tree.yview)
        self.tasks_tree.configure(yscrollcommand=vsb.set)

        for col, w in zip(columns, (140, 80, 70, 80, 80, 80)):
            self.tasks_tree.heading(col, text=col.title())
            self.tasks_tree.column(col, width=w, anchor="w")

        self.tasks_tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        # Buttons under list
        btn_row = ctk.CTkFrame(parent, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(0, 8))

        complete_btn = ctk.CTkButton(
            btn_row,
            text="✔ Mark Done",
            fg_color="#16a34a",
            hover_color="#15803d",
            command=self.mark_selected_completed,
        )
        complete_btn.pack(side="left", padx=(0, 6))

        delete_btn = ctk.CTkButton(
            btn_row,
            text="🗑 Delete",
            fg_color="#dc2626",
            hover_color="#b91c1c",
            command=self.delete_selected_task,
        )
        delete_btn.pack(side="left")

        save_btn = ctk.CTkButton(
            parent,
            text="💾 Save Now",
            fg_color="#6b7280",
            hover_color="#4b5563",
            command=self.save_data,
        )
        save_btn.pack(fill="x", padx=16, pady=(0, 10))

    def build_right_panel(self, parent):
        header_row = ctk.CTkFrame(parent, fg_color="transparent")
        header_row.pack(fill="x", padx=12, pady=(12, 4))

        ctk.CTkLabel(
            header_row,
            text="Today’s Plan",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(side="left")

        # Planning controls
        self.start_time_entry = ctk.CTkEntry(
            header_row,
            width=80,
            placeholder_text="Start (HH:MM)",
        )
        self.start_time_entry.insert(0, "08:00")
        self.start_time_entry.pack(side="right", padx=(4, 0))

        self.end_time_entry = ctk.CTkEntry(
            header_row,
            width=80,
            placeholder_text="End (HH:MM)",
        )
        self.end_time_entry.insert(0, "22:00")
        self.end_time_entry.pack(side="right", padx=(4, 6))

        ctk.CTkLabel(
            header_row,
            text="Plan from",
            font=ctk.CTkFont(size=11),
            text_color="#6b7280",
        ).pack(side="right", padx=(0, 4))

        plan_btn = ctk.CTkButton(
            header_row,
            text="⚡ Auto Plan Day",
            fg_color="#0ea5e9",
            hover_color="#0284c7",
            command=self.plan_today,
        )
        plan_btn.pack(side="left", padx=(8, 0))

        # Tab view
        tabs = ctk.CTkTabview(parent)
        tabs.pack(fill="both", expand=True, padx=12, pady=(4, 12))

        self.today_tab = tabs.add("Today")
        self.focus_tab = tabs.add("Focus Mode")

        # Today tab content
        self.today_frame = ctk.CTkScrollableFrame(self.today_tab)
        self.today_frame.pack(fill="both", expand=True, padx=6, pady=6)

        # Focus mode
        self.focus_label = ctk.CTkLabel(
            self.focus_tab,
            text="Focus Mode\n\nClick a task in Today’s Plan to focus on it.",
            font=ctk.CTkFont(size=16, weight="bold"),
            justify="center",
        )
        self.focus_label.pack(expand=True)

    # ---------------- DATA PERSISTENCE ----------------

    def load_data(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                tasks_raw = raw.get("tasks", [])
                self.tasks = [Task.from_dict(d) for d in tasks_raw]
                if self.tasks:
                    self.next_task_id = max(t.id for t in self.tasks) + 1
            except Exception as e:
                print("Failed to load data:", e)
                self.tasks = []
        else:
            self.tasks = []

    def save_data(self):
        data = {
            "tasks": [t.to_dict() for t in self.tasks],
        }
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            messagebox.showinfo("Saved", "Tasks and plan saved to dailyflow_data.json")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save data:\n{e}")

    # ---------------- TASK CRUD ----------------

    def add_task_from_form(self):
        title = self.title_entry.get().strip()
        if not title:
            messagebox.showwarning("Missing", "Please enter a title.")
            return

        category = self.category_entry.get().strip() or "General"
        due_str = self.due_entry.get().strip()
        if due_str == "":
            due_str = None
        else:
            # validate format
            try:
                datetime.strptime(due_str, "%Y-%m-%d")
            except ValueError:
                messagebox.showerror("Invalid date", "Due date must be YYYY-MM-DD or left blank.")
                return

        dur_str = self.duration_entry.get().strip() or "60"
        try:
            duration = int(dur_str)
            if duration <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid duration", "Duration must be a positive integer (minutes).")
            return

        priority = self.priority_option.get()

        task = Task(
            self.next_task_id,
            title,
            category,
            due_str,
            duration,
            priority,
        )
        self.tasks.append(task)
        self.next_task_id += 1

        # Clear fields
        self.title_entry.delete(0, "end")
        # keep category/due as user might enter similar tasks
        self.duration_entry.delete(0, "end")

        self.refresh_all_views()

    def get_selected_task(self):
        sel = self.tasks_tree.selection()
        if not sel:
            return None
        item_id = sel[0]
        try:
            task_id = int(self.tasks_tree.item(item_id, "values")[0].split(":", 1)[0])
        except Exception:
            # fallback: store real id via tags or separate mapping in future
            # For now, we set first column as "id: title"
            val = self.tasks_tree.item(item_id, "values")[0]
            if ":" in val:
                task_id = int(val.split(":", 1)[0])
            else:
                return None
        for t in self.tasks:
            if t.id == task_id:
                return t
        return None

    def mark_selected_completed(self):
        task = self.get_selected_task()
        if not task:
            messagebox.showinfo("No selection", "Please select a task first.")
            return
        task.completed = True
        # Remove schedule info
        task.start_time = None
        task.end_time = None
        self.refresh_all_views()

    def delete_selected_task(self):
        task = self.get_selected_task()
        if not task:
            messagebox.showinfo("No selection", "Please select a task first.")
            return
        if not messagebox.askyesno("Delete", f"Delete task:\n\n{task.title}?"):
            return
        self.tasks = [t for t in self.tasks if t.id != task.id]
        self.refresh_all_views()

    # ---------------- PLANNING ----------------

    def parse_time(self, s: str):
        try:
            t = datetime.strptime(s, "%H:%M").time()
            return t
        except ValueError:
            return None

    def plan_today(self):
        if not self.tasks:
            messagebox.showinfo("No tasks", "You have no tasks to plan yet.")
            return

        start_str = self.start_time_entry.get().strip() or "08:00"
        end_str = self.end_time_entry.get().strip() or "22:00"
        start_t = self.parse_time(start_str)
        end_t = self.parse_time(end_str)
        if not start_t or not end_t:
            messagebox.showerror("Invalid time", "Start/End time must be in HH:MM format.")
            return

        today = date.today()
        start_dt = datetime.combine(today, start_t)
        end_dt = datetime.combine(today, end_t)
        if start_dt >= end_dt:
            messagebox.showerror("Invalid range", "Start time must be before end time.")
            return

        # Filter tasks to schedule: incomplete
        to_schedule = [t for t in self.tasks if not t.completed]

        if not to_schedule:
            messagebox.showinfo("Nothing to plan", "All tasks are completed!")
            return

        # Sort by importance (score desc)
        to_schedule.sort(key=lambda t: t.score_for_today(today), reverse=True)

        current = start_dt
        for t in to_schedule:
            if current >= end_dt:
                # no more time
                t.start_time = None
                t.end_time = None
                continue
            duration = timedelta(minutes=t.duration_minutes)
            slot_end = current + duration
            if slot_end > end_dt:
                # not enough space; leave unscheduled
                t.start_time = None
                t.end_time = None
            else:
                t.start_time = current.isoformat()
                t.end_time = slot_end.isoformat()
                current = slot_end + timedelta(minutes=5)  # small break

        self.refresh_all_views()

    # ---------------- VIEW REFRESH ----------------

    def refresh_all_views(self):
        self.refresh_task_list()
        self.refresh_today_plan()

    def refresh_task_list(self):
        for row in self.tasks_tree.get_children():
            self.tasks_tree.delete(row)

        for t in self.tasks:
            status = "Done" if t.completed else "Pending"
            due = t.due_date or "-"
            row_title = f"{t.id}: {t.title}"
            self.tasks_tree.insert(
                "",
                "end",
                values=(
                    row_title,
                    t.category,
                    t.priority,
                    due,
                    f"{t.duration_minutes}m",
                    status,
                ),
            )

    def refresh_today_plan(self):
        # Clear frame
        for widget in self.today_frame.winfo_children():
            widget.destroy()

        today = date.today()
        # Only tasks with schedule and not completed
        active = []
        unscheduled = []
        for t in self.tasks:
            if t.completed:
                continue
            if t.start_time and t.end_time:
                try:
                    st = datetime.fromisoformat(t.start_time)
                    if st.date() == today:
                        active.append(t)
                    else:
                        unscheduled.append(t)
                except Exception:
                    unscheduled.append(t)
            else:
                unscheduled.append(t)

        # Sort by start time
        active.sort(key=lambda x: x.start_time or "")

        if not active and not unscheduled:
            ctk.CTkLabel(
                self.today_frame,
                text="No tasks for today.\nAdd tasks on the left and click 'Auto Plan Day'.",
                font=ctk.CTkFont(size=14),
            ).pack(pady=40)
            return

        # Active schedule
        if active:
            ctk.CTkLabel(
                self.today_frame,
                text="Planned Slots",
                font=ctk.CTkFont(size=14, weight="bold"),
            ).pack(anchor="w", padx=6, pady=(4, 2))

            for t in active:
                st = datetime.fromisoformat(t.start_time)
                et = datetime.fromisoformat(t.end_time)
                time_str = f"{st.strftime('%H:%M')}–{et.strftime('%H:%M')}"
                row = ctk.CTkFrame(self.today_frame)
                row.pack(fill="x", padx=6, pady=3)

                time_lbl = ctk.CTkLabel(
                    row,
                    text=time_str,
                    width=90,
                    font=ctk.CTkFont(size=12, weight="bold"),
                )
                time_lbl.pack(side="left", padx=(4, 8))

                txt = f"{t.title}  [{t.category}]  ({t.priority})"
                task_btn = ctk.CTkButton(
                    row,
                    text=txt,
                    anchor="w",
                    fg_color="#e5e7eb",
                    hover_color="#d1d5db",
                    text_color="#111827",
                    command=lambda task=t: self.set_focus_task(task),
                )
                task_btn.pack(side="left", fill="x", expand=True, padx=(0, 4))

        # Unscheduled
        if unscheduled:
            ctk.CTkLabel(
                self.today_frame,
                text="Unscheduled Tasks",
                font=ctk.CTkFont(size=14, weight="bold"),
            ).pack(anchor="w", padx=6, pady=(10, 2))

            for t in unscheduled:
                row = ctk.CTkFrame(self.today_frame, fg_color="#f5f5f5")
                row.pack(fill="x", padx=6, pady=3)

                txt = f"{t.title}  [{t.category}]  ({t.priority})"
                if t.due_date:
                    txt += f"  • Due: {t.due_date}"
                ctk.CTkLabel(
                    row,
                    text=txt,
                    anchor="w",
                    font=ctk.CTkFont(size=12),
                    text_color="#111827",
                ).pack(side="left", padx=6, pady=4)

    def set_focus_task(self, task: Task):
        """Update focus mode tab with the selected task."""
        lines = []
        lines.append("FOCUS MODE")
        lines.append("")
        lines.append(f"Task: {task.title}")
        lines.append(f"Category: {task.category}")
        lines.append(f"Priority: {task.priority}")
        if task.due_date:
            lines.append(f"Due date: {task.due_date}")
        if task.start_time and task.end_time:
            st = datetime.fromisoformat(task.start_time)
            et = datetime.fromisoformat(task.end_time)
            lines.append(f"Slot: {st.strftime('%H:%M')}–{et.strftime('%H:%M')}")
        lines.append("")
        lines.append("Tip: Close other apps and focus only on this task.")
        self.focus_label.configure(text="\n".join(lines))


if __name__ == "__main__":
    app = DailyFlowApp()
    app.mainloop()

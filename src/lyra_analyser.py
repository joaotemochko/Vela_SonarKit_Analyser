"""
LYRA Data Analyser - Scientific Analysis Tool
=============================================
A comprehensive GUI tool for analyzing spatial navigation data
from the Lyra Framework for Non-Visual Spatial Navigation research.

Metrics aligned with:
- Spatial Cognition research (Klatzky et al., Loomis et al.)
- Wayfinding performance (Golledge, 1999)
- Blind navigation studies (Giudice et al.)

Author: Instituto Federal de Educação, Ciência e Tecnologia de São Paulo & Universidade do Vale do Itajaí
Version: 1.0.0
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import numpy as np
from datetime import datetime
import os
from typing import Dict, List, Optional

import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

try:
    from scipy.signal import savgol_filter
    HAS_SCIPY = True
except:
    HAS_SCIPY = False


class LyraAnalyser:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Lyra Scientific Data Analyser v1.0 - IFSP & UNIVALI")
        self.root.geometry("1400x900")
        self.root.state("zoomed")

        self.df: Optional[pd.DataFrame] = None
        self.current_file: str = ""
        self.sessions: List[str] = []
        self.current_session: str = ""
        self.current_figures: Dict[str, Figure] = {}
        
        self._setup_ui()
        self._setup_menu()
        
    def _setup_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open CSV...", command=self.load_csv)
        file_menu.add_separator()
        file_menu.add_command(label="Export All Figures...", command=self.export_all_figures)
        file_menu.add_command(label="Export Report...", command=self.export_report)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        analysis_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Analysis", menu=analysis_menu)
        analysis_menu.add_command(label="Generate All Figures", command=self.generate_all_figures)
        analysis_menu.add_command(label="Full Report", command=self.run_full_analysis)
        

        about_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="About", menu=about_menu)
        about_menu.add_command(label="Credits", command=self.show_about)
        
    def _setup_ui(self):
        self.main_frame = ttk.Frame(self.root, padding="5")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        self.left_panel = ttk.Frame(self.main_frame, width=320)
        self.left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        self.left_panel.pack_propagate(False)
        
        self.right_panel = ttk.Frame(self.main_frame)
        self.right_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self._setup_left_panel()
        self._setup_right_panel()
        
    def _setup_left_panel(self):
        # File
        file_frame = ttk.LabelFrame(self.left_panel, text="📁 Data File", padding="5")
        file_frame.pack(fill=tk.X, pady=(0, 10))
        self.file_label = ttk.Label(file_frame, text="No file loaded", wraplength=300)
        self.file_label.pack(fill=tk.X)
        ttk.Button(file_frame, text="Load CSV", command=self.load_csv).pack(fill=tk.X, pady=(5, 0))
        
        # Session
        session_frame = ttk.LabelFrame(self.left_panel, text="📊 Session", padding="5")
        session_frame.pack(fill=tk.X, pady=(0, 10))
        self.session_var = tk.StringVar()
        self.session_combo = ttk.Combobox(session_frame, textvariable=self.session_var, state="readonly")
        self.session_combo.pack(fill=tk.X)
        self.session_combo.bind('<<ComboboxSelected>>', self.on_session_change)
        
        # Stats
        stats_frame = ttk.LabelFrame(self.left_panel, text="📈 Statistics", padding="5")
        stats_frame.pack(fill=tk.X, pady=(0, 10))
        self.stats_text = tk.Text(stats_frame, height=8, font=('Consolas', 9))
        self.stats_text.pack(fill=tk.X)
        self.stats_text.config(state=tk.DISABLED)
        
        # Analysis buttons
        btn_frame = ttk.LabelFrame(self.left_panel, text="🔬 Analysis", padding="5")
        btn_frame.pack(fill=tk.X, pady=(0, 10))
        
        for text, cmd in [
            ("🗺️ Path", self.visualize_path),
            ("📊 Distance", self.plot_distance_time),
            ("🎯 Goals", self.analyze_goals),
            ("⚠️ Safety", self.analyze_safety),
            ("📉 Velocity", self.plot_velocity),
            ("🧭 Heading", self.plot_heading),
            ("📄 Full Report", self.run_full_analysis)
        ]:
            ttk.Button(btn_frame, text=text, command=cmd).pack(fill=tk.X, pady=1)
        
        # Export
        exp_frame = ttk.LabelFrame(self.left_panel, text="💾 Export", padding="5")
        exp_frame.pack(fill=tk.X)
        ttk.Button(exp_frame, text="Generate All Figures", command=self.generate_all_figures).pack(fill=tk.X, pady=1)
        ttk.Button(exp_frame, text="Export All PNG", command=self.export_all_figures).pack(fill=tk.X, pady=1)
        ttk.Button(exp_frame, text="Export Report TXT", command=self.export_report).pack(fill=tk.X, pady=1)
        
    def _setup_right_panel(self):
        self.notebook = ttk.Notebook(self.right_panel)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        self.tabs = {}
        for name in ['Path', 'Distance', 'Goals', 'Safety', 'Velocity', 'Heading', 'Report']:
            tab = ttk.Frame(self.notebook)
            self.notebook.add(tab, text=name)
            self.tabs[name] = tab
        
        self.report_text = tk.Text(self.tabs['Report'], font=('Consolas', 10))
        scroll = ttk.Scrollbar(self.tabs['Report'], command=self.report_text.yview)
        self.report_text.configure(yscrollcommand=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.report_text.pack(fill=tk.BOTH, expand=True)

    def load_csv(self):
        filepath = filedialog.askopenfilename(
            title="Select Lyra CSV",
            filetypes=[("CSV", "*.csv"), ("All", "*.*")]
        )
        if not filepath:
            return
        
        try:
            df = None
            for delim in [';', ',', '\t']:
                try:
                    test = pd.read_csv(filepath, delimiter=delim)
                    if len(test.columns) > 3:
                        df = test
                        break
                except:
                    continue
            
            if df is None:
                messagebox.showerror("Error", "Cannot parse CSV")
                return
            
            self.df = df
            self.current_file = filepath
            self.file_label.config(text=os.path.basename(filepath))
            
            if 'session_id' in df.columns:
                self.sessions = df['session_id'].unique().tolist()
            else:
                self.sessions = ['default']
                self.df['session_id'] = 'default'
            
            self.session_combo['values'] = self.sessions
            if self.sessions:
                self.session_combo.set(self.sessions[0])
                self.current_session = self.sessions[0]
            
            self.current_figures.clear()
            self._update_stats()
            messagebox.showinfo("OK", f"Loaded {len(df)} records")
        except Exception as e:
            messagebox.showerror("Error", str(e))
            
    def on_session_change(self, event=None):
        self.current_session = self.session_var.get()
        self.current_figures.clear()
        self._update_stats()
        
    def _get_data(self) -> pd.DataFrame:
        if self.df is None:
            return pd.DataFrame()
        if self.current_session != 'default':
            return self.df[self.df['session_id'] == self.current_session].copy()
        return self.df.copy()
    
    def _get_track(self) -> pd.DataFrame:
        data = self._get_data()
        if 'event' in data.columns:
            return data[data['event'].isin(['TRACK', 'STEP'])].copy()
        return data
    
    def _get_time(self, df: pd.DataFrame) -> np.ndarray:
        if 'elapsed_time' in df.columns:
            return df['elapsed_time'].values
        elif 'timestamp' in df.columns:
            return (df['timestamp'] - df['timestamp'].iloc[0]).values
        return np.arange(len(df)) * 0.5
        
    def _update_stats(self):
        if self.df is None:
            return
        data = self._get_data()
        track = self._get_track()
        
        lines = [f"Records: {len(data)}", f"Track: {len(track)}"]
        
        time = self._get_time(data)
        if len(time) > 0:
            lines.append(f"Duration: {time[-1]:.1f}s")
        
        if 'event' in data.columns:
            collect = len(data[data['event'] == 'COLLECT'])
            lines.append(f"Goals: {collect}")
        
        if 'velocity' in track.columns:
            lines.append(f"Avg Speed: {track['velocity'].mean():.2f}m/s")
        
        self.stats_text.config(state=tk.NORMAL)
        self.stats_text.delete(1.0, tk.END)
        self.stats_text.insert(tk.END, "\n".join(lines))
        self.stats_text.config(state=tk.DISABLED)

    def _make_fig(self, name: str, size=(10, 8)) -> Figure:
        fig = Figure(figsize=size, dpi=100)
        self.current_figures[name] = fig
        return fig
    
    def _show_fig(self, fig: Figure, tab_name: str):
        tab = self.tabs[tab_name]
        for w in tab.winfo_children():
            w.destroy()
        canvas = FigureCanvasTkAgg(fig, master=tab)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        NavigationToolbar2Tk(canvas, tab)
        self.notebook.select(tab)

    def visualize_path(self):
        if self.df is None:
            return
        track = self._get_track()
        data = self._get_data()
        
        if 'x' not in track.columns or 'z' not in track.columns:
            messagebox.showwarning("Warning", "No position data")
            return
        
        fig = self._make_fig('01_path')
        ax = fig.add_subplot(111)
        
        x, z = track['x'].values, track['z'].values
        c = np.linspace(0, 1, len(x))
        sc = ax.scatter(x, z, c=c, cmap='viridis', s=5, alpha=0.7)
        fig.colorbar(sc, ax=ax, label='Time')
        ax.plot(x, z, 'b-', alpha=0.2, lw=0.5)
        
        ax.scatter(x[0], z[0], c='lime', s=200, marker='^', edgecolors='k', lw=2, label='Start', zorder=10)
        ax.scatter(x[-1], z[-1], c='red', s=200, marker='s', edgecolors='k', lw=2, label='End', zorder=10)
        
        if 'event' in data.columns:
            coll = data[data['event'] == 'COLLECT']
            if len(coll) > 0 and 'x' in coll.columns:
                ax.scatter(coll['x'], coll['z'], c='gold', s=300, marker='*', edgecolors='k', lw=1.5, label='Goal', zorder=11)
        
        ax.set_xlabel('X (m)')
        ax.set_ylabel('Z (m)')
        ax.set_title(f'Path - {self.current_session}')
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.set_aspect('equal')
        fig.tight_layout()
        self._show_fig(fig, 'Path')

    def plot_distance_time(self):
        if self.df is None:
            return
        track = self._get_track()
        data = self._get_data()
        time = self._get_time(track)
        
        fig = self._make_fig('02_distance')
        
        ax1 = fig.add_subplot(211)
        dist_col = 'dist_goal' if 'dist_goal' in track.columns else ('dist_local' if 'dist_local' in track.columns else None)
        
        if dist_col:
            dist = track[dist_col].values
            ax1.plot(time, dist, 'b-', alpha=0.7, lw=1, label='Distance')
            if HAS_SCIPY and len(dist) > 15:
                w = min(51, len(dist)//2*2+1)
                if w >= 5:
                    try:
                        ax1.plot(time, savgol_filter(dist, w, 3), 'r-', lw=2, label='Smooth')
                    except:
                        pass
            
            if 'event' in data.columns:
                for _, r in data[data['event'] == 'COLLECT'].iterrows():
                    t = r.get('elapsed_time', r.get('timestamp', 0) - data['timestamp'].min())
                    ax1.axvline(x=t, color='gold', ls='--', lw=2)
            
            ax1.set_ylabel('Dist to Goal (m)')
            ax1.set_title('Distance to Goal')
            ax1.legend()
            ax1.grid(True, alpha=0.3)
        
        ax2 = fig.add_subplot(212)
        for col, lbl, clr in [('dist_boundary', 'Boundary', 'g'), ('dist_obstacle', 'Obstacle', 'orange'), ('dist_hazard', 'Hazard', 'r')]:
            if col in track.columns:
                v = track[col].values
                m = v > 0
                if m.any():
                    ax2.plot(time[m], v[m], color=clr, alpha=0.7, label=lbl)
        ax2.axhline(y=2.0, color='r', ls=':', lw=2, label='Safety 2m')
        ax2.set_xlabel('Time (s)')
        ax2.set_ylabel('Distance (m)')
        ax2.set_title('Distance to Environment')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        fig.tight_layout()
        self._show_fig(fig, 'Distance')

    def analyze_goals(self):
        if self.df is None:
            return
        data = self._get_data()
        track = self._get_track()
        
        fig = self._make_fig('03_goals')
        
        if 'event' not in data.columns:
            ax = fig.add_subplot(111)
            ax.text(0.5, 0.5, 'No event data', ha='center', va='center')
            fig.tight_layout()
            self._show_fig(fig, 'Goals')
            return
        
        coll = data[data['event'] == 'COLLECT']
        if len(coll) == 0:
            ax = fig.add_subplot(111)
            ax.text(0.5, 0.5, 'No goals collected', ha='center', va='center', fontsize=14)
            fig.tight_layout()
            self._show_fig(fig, 'Goals')
            return
        
        times = self._get_time(coll)
        
        ax1 = fig.add_subplot(221)
        ax1.bar(range(1, len(times)+1), times, color='gold', edgecolor='k')
        ax1.set_xlabel('Goal #')
        ax1.set_ylabel('Time (s)')
        ax1.set_title('Time to Each Goal')
        ax1.grid(True, alpha=0.3, axis='y')
        
        ax2 = fig.add_subplot(222)
        if len(times) > 1:
            inter = np.diff(times)
            ax2.bar(range(1, len(inter)+1), inter, color='#3498db', edgecolor='k')
            ax2.axhline(np.mean(inter), color='r', ls='--', label=f'Mean {np.mean(inter):.1f}s')
            ax2.set_xlabel('Interval')
            ax2.set_ylabel('Time (s)')
            ax2.set_title('Inter-Goal Time')
            ax2.legend()
            ax2.grid(True, alpha=0.3, axis='y')
        
        ax3 = fig.add_subplot(223)
        if 'x' in coll.columns and 'z' in coll.columns:
            if 'x' in track.columns:
                ax3.plot(track['x'], track['z'], 'b-', alpha=0.3, lw=0.5)
            for i, (_, r) in enumerate(coll.iterrows()):
                ax3.scatter(r['x'], r['z'], c='gold', s=200, marker='*', edgecolors='k', zorder=10)
                ax3.annotate(f'{i+1}', (r['x'], r['z']), xytext=(5,5), textcoords='offset points')
            ax3.set_xlabel('X (m)')
            ax3.set_ylabel('Z (m)')
            ax3.set_title('Goal Positions')
            ax3.set_aspect('equal')
            ax3.grid(True, alpha=0.3)
        
        ax4 = fig.add_subplot(224)
        ax4.axis('off')
        txt = f"Goals: {len(coll)}\nFirst: {times[0]:.1f}s\nLast: {times[-1]:.1f}s"
        if len(times) > 1:
            txt += f"\n\nMean interval: {np.mean(np.diff(times)):.1f}s"
        ax4.text(0.1, 0.9, txt, transform=ax4.transAxes, va='top', fontsize=12, family='monospace',
                 bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
        
        fig.tight_layout()
        self._show_fig(fig, 'Goals')

    def analyze_safety(self):
        if self.df is None:
            return
        track = self._get_track()
        data = self._get_data()
        time = self._get_time(track)
        
        fig = self._make_fig('04_safety')
        
        ax1 = fig.add_subplot(221)
        dist_col = 'dist_boundary' if 'dist_boundary' in track.columns else ('dist_local' if 'dist_local' in track.columns else None)
        
        if dist_col:
            dist = track[dist_col].values
            dist = np.where(dist < 0, 999, dist)
            
            ax1.fill_between(time, 0, 5, where=dist<1, color='red', alpha=0.5, label='Danger <1m')
            ax1.fill_between(time, 0, 5, where=(dist>=1)&(dist<2), color='yellow', alpha=0.5, label='Warning 1-2m')
            ax1.fill_between(time, 0, 5, where=dist>=2, color='green', alpha=0.3, label='Safe >2m')
            ax1.plot(time, np.minimum(dist, 5), 'k-', lw=0.5, alpha=0.5)
            ax1.set_xlabel('Time (s)')
            ax1.set_ylabel('Distance (m)')
            ax1.set_title('Safety Zones')
            ax1.legend(loc='upper right')
            ax1.set_ylim(0, 5)
            ax1.grid(True, alpha=0.3)
        
        ax2 = fig.add_subplot(222)
        if 'event' in data.columns and 'category' in data.columns:
            enter = data[data['event'] == 'ENTER']
            if len(enter) > 0:
                cats = {0:'Boundary', 1:'Obstacle', 2:'Goal', 3:'Interact', 4:'Hazard'}
                counts = enter['category'].value_counts()
                labels = [cats.get(int(c), f'C{c}') for c in counts.index]
                colors = ['#1abc9c', '#e67e22', '#9b59b6', '#3498db', '#c0392b']
                ax2.bar(labels, counts.values, color=colors[:len(labels)], edgecolor='k')
                ax2.set_xlabel('Category')
                ax2.set_ylabel('ENTER Events')
                ax2.set_title('Events by Category')
                ax2.tick_params(axis='x', rotation=45)
                ax2.grid(True, alpha=0.3, axis='y')
        
        ax3 = fig.add_subplot(223)
        if dist_col:
            dv = dist[dist < 100]
            if len(dv) > 0:
                ax3.hist(dv, bins=30, color='#3498db', edgecolor='k', alpha=0.7)
                ax3.axvline(2.0, color='r', ls='--', lw=2, label='Safety')
                ax3.axvline(np.mean(dv), color='g', ls='-', lw=2, label=f'Mean {np.mean(dv):.1f}m')
                ax3.set_xlabel('Distance (m)')
                ax3.set_ylabel('Frequency')
                ax3.set_title('Distance Distribution')
                ax3.legend()
                ax3.grid(True, alpha=0.3)
        
        ax4 = fig.add_subplot(224)
        if 'collisions' in track.columns:
            ax4.plot(time, track['collisions'].values, 'r-', lw=2)
            ax4.fill_between(time, 0, track['collisions'].values, color='red', alpha=0.3)
            ax4.set_xlabel('Time (s)')
            ax4.set_ylabel('Collisions')
            ax4.set_title('Cumulative Collisions')
            ax4.grid(True, alpha=0.3)
        
        fig.tight_layout()
        self._show_fig(fig, 'Safety')

    def plot_velocity(self):
        if self.df is None:
            return
        track = self._get_track()
        time = self._get_time(track)
        
        if 'velocity' not in track.columns:
            if 'x' in track.columns and 'z' in track.columns:
                track = track.copy()
                dx = np.diff(track['x'].values, prepend=track['x'].iloc[0])
                dz = np.diff(track['z'].values, prepend=track['z'].iloc[0])
                dt = np.diff(time, prepend=0)
                dt[0] = dt[1] if len(dt) > 1 else 0.1
                dt = np.where(dt == 0, 0.001, dt)
                track['velocity'] = np.sqrt(dx**2 + dz**2) / dt
            else:
                messagebox.showwarning("Warning", "No velocity data")
                return
        
        vel = track['velocity'].values
        
        fig = self._make_fig('05_velocity')
        
        ax1 = fig.add_subplot(211)
        ax1.plot(time, vel, 'b-', alpha=0.5, lw=1, label='Raw')
        
        if HAS_SCIPY and len(vel) > 15:
            w = min(51, len(vel)//2*2+1)
            if w >= 5:
                try:
                    ax1.plot(time, savgol_filter(vel, w, 3), 'r-', lw=2, label='Smooth')
                except:
                    pass
        
        m = np.mean(vel)
        s = np.std(vel)
        ax1.axhline(m, color='g', ls='--', lw=2, label=f'Mean {m:.2f}')
        ax1.fill_between(time, m-s, m+s, color='g', alpha=0.1)
        ax1.set_xlabel('Time (s)')
        ax1.set_ylabel('Velocity (m/s)')
        ax1.set_title('Velocity Profile')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        ax2 = fig.add_subplot(212)
        ax2.hist(vel, bins=40, color='#3498db', edgecolor='k', alpha=0.7, density=True)
        ax2.axvline(m, color='g', ls='-', lw=2, label=f'Mean {m:.2f}')
        ax2.axvline(np.median(vel), color='orange', ls='--', lw=2, label=f'Median {np.median(vel):.2f}')
        ax2.set_xlabel('Velocity (m/s)')
        ax2.set_ylabel('Density')
        ax2.set_title('Velocity Distribution')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        fig.tight_layout()
        self._show_fig(fig, 'Velocity')

    def plot_heading(self):
        if self.df is None:
            return
        track = self._get_track()
        
        if 'x' not in track.columns or 'z' not in track.columns:
            messagebox.showwarning("Warning", "No position data")
            return
        
        x, z = track['x'].values, track['z'].values
        dx, dz = np.diff(x), np.diff(z)
        mag = np.sqrt(dx**2 + dz**2)
        valid = mag > 0.01
        angles = np.arctan2(dz, dx)
        
        time = self._get_time(track)[1:]
        
        fig = self._make_fig('06_heading')
        
        ax1 = fig.add_subplot(221)
        ax1.plot(time[valid], np.degrees(angles[valid]), 'b-', alpha=0.5, lw=1)
        ax1.set_xlabel('Time (s)')
        ax1.set_ylabel('Heading (deg)')
        ax1.set_title('Heading Over Time')
        ax1.set_ylim(-180, 180)
        ax1.grid(True, alpha=0.3)
        
        ax2 = fig.add_subplot(222, projection='polar')
        hist, bins = np.histogram(angles[valid], bins=16, range=(-np.pi, np.pi))
        ax2.bar(bins[:-1], hist, width=2*np.pi/16, alpha=0.7, color='#3498db', edgecolor='k')
        ax2.set_title('Heading Distribution', pad=20)
        
        ax3 = fig.add_subplot(223)
        if 'heading_changes' in track.columns:
            t = self._get_time(track)
            ax3.plot(t, track['heading_changes'].values, 'purple', lw=2)
            ax3.fill_between(t, 0, track['heading_changes'].values, color='purple', alpha=0.3)
        else:
            changes = np.abs(np.diff(angles[valid]))
            changes = np.where(changes > np.pi, 2*np.pi - changes, changes)
            cum = np.cumsum(changes > 0.5)
            ax3.plot(time[valid][1:], cum, 'purple', lw=2)
            ax3.fill_between(time[valid][1:], 0, cum, color='purple', alpha=0.3)
        ax3.set_xlabel('Time (s)')
        ax3.set_ylabel('Cumulative')
        ax3.set_title('Direction Changes (>30°)')
        ax3.grid(True, alpha=0.3)
        
        ax4 = fig.add_subplot(224)
        step = max(1, len(x)//100)
        ax4.quiver(x[:-1:step], z[:-1:step], dx[::step], dz[::step], mag[::step], cmap='viridis', alpha=0.7)
        ax4.set_xlabel('X (m)')
        ax4.set_ylabel('Z (m)')
        ax4.set_title('Movement Vectors')
        ax4.set_aspect('equal')
        ax4.grid(True, alpha=0.3)
        
        fig.tight_layout()
        self._show_fig(fig, 'Heading')

    def generate_all_figures(self):
        if self.df is None:
            messagebox.showwarning("Warning", "Load data first")
            return
        
        self.current_figures.clear()
        self.visualize_path()
        self.plot_distance_time()
        self.analyze_goals()
        self.analyze_safety()
        self.plot_velocity()
        self.plot_heading()
        
        messagebox.showinfo("Done", f"Generated {len(self.current_figures)} figures")

    def export_all_figures(self):
        if self.df is None:
            messagebox.showwarning("Warning", "Load data first")
            return
        
        folder = filedialog.askdirectory(title="Select Output Folder")
        if not folder:
            return
        
        try:
            saved = []
            sess = self.current_session.replace(':', '-').replace('/', '-')[:25]
            track = self._get_track()
            data = self._get_data()
            time_arr = self._get_time(track)
            
            # 1. PATH
            if 'x' in track.columns and 'z' in track.columns:
                x, z = track['x'].values, track['z'].values
                
                fig, ax = plt.subplots(figsize=(10, 8))
                c = np.linspace(0, 1, len(x))
                sc = ax.scatter(x, z, c=c, cmap='viridis', s=5, alpha=0.7)
                fig.colorbar(sc, ax=ax, label='Time')
                ax.plot(x, z, 'b-', alpha=0.2, lw=0.5)
                ax.scatter(x[0], z[0], c='lime', s=200, marker='^', edgecolors='k', lw=2, label='Start', zorder=10)
                ax.scatter(x[-1], z[-1], c='red', s=200, marker='s', edgecolors='k', lw=2, label='End', zorder=10)
                if 'event' in data.columns:
                    coll = data[data['event'] == 'COLLECT']
                    if len(coll) > 0 and 'x' in coll.columns:
                        ax.scatter(coll['x'], coll['z'], c='gold', s=300, marker='*', edgecolors='k', lw=1.5, label='Goal', zorder=11)
                ax.set_xlabel('X (m)')
                ax.set_ylabel('Z (m)')
                ax.set_title(f'Navigation Path - {sess}')
                ax.legend()
                ax.grid(True, alpha=0.3)
                ax.set_aspect('equal')
                fig.tight_layout()
                fig.savefig(os.path.join(folder, f'01_path_{sess}.png'), dpi=150, bbox_inches='tight', facecolor='white')
                saved.append('01_path')
                plt.close(fig)
            
            # 2. DISTANCE TO GOAL
            dist_col = 'dist_goal' if 'dist_goal' in track.columns else ('dist_local' if 'dist_local' in track.columns else None)
            if dist_col:
                dist = track[dist_col].values
                
                fig, ax = plt.subplots(figsize=(10, 6))
                ax.plot(time_arr, dist, 'b-', alpha=0.7, lw=1, label='Distance')
                if HAS_SCIPY and len(dist) > 15:
                    w = min(51, len(dist)//2*2+1)
                    if w >= 5:
                        try:
                            ax.plot(time_arr, savgol_filter(dist, w, 3), 'r-', lw=2, label='Smooth')
                        except:
                            pass
                if 'event' in data.columns:
                    for _, r in data[data['event'] == 'COLLECT'].iterrows():
                        t = r.get('elapsed_time', r.get('timestamp', 0) - data['timestamp'].min())
                        ax.axvline(x=t, color='gold', ls='--', lw=2)
                ax.set_xlabel('Time (s)')
                ax.set_ylabel('Distance to Goal (m)')
                ax.set_title('Distance to Goal Over Time')
                ax.legend()
                ax.grid(True, alpha=0.3)
                fig.tight_layout()
                fig.savefig(os.path.join(folder, f'02_distance_goal_{sess}.png'), dpi=150, bbox_inches='tight', facecolor='white')
                saved.append('02_distance_goal')
                plt.close(fig)
            
            # 3. DISTANCE TO ENVIRONMENT (Boundary, Obstacle, Hazard)
            fig, ax = plt.subplots(figsize=(10, 6))
            has_env = False
            for col, lbl, clr in [('dist_boundary', 'Boundary', 'g'), ('dist_obstacle', 'Obstacle', 'orange'), ('dist_hazard', 'Hazard', 'r')]:
                if col in track.columns:
                    v = track[col].values
                    m = v > 0
                    if m.any():
                        ax.plot(time_arr[m], v[m], color=clr, alpha=0.7, label=lbl)
                        has_env = True
            if has_env:
                ax.axhline(y=2.0, color='r', ls=':', lw=2, label='Safety 2m')
                ax.set_xlabel('Time (s)')
                ax.set_ylabel('Distance (m)')
                ax.set_title('Distance to Environment')
                ax.legend()
                ax.grid(True, alpha=0.3)
                fig.tight_layout()
                fig.savefig(os.path.join(folder, f'03_distance_environment_{sess}.png'), dpi=150, bbox_inches='tight', facecolor='white')
                saved.append('03_distance_environment')
            plt.close(fig)
            
            # GOALS
            if 'event' in data.columns:
                coll = data[data['event'] == 'COLLECT']
                if len(coll) > 0:
                    times_goal = self._get_time(coll)
                    
                    # 4. Time to Each Goal
                    fig, ax = plt.subplots(figsize=(8, 6))
                    ax.bar(range(1, len(times_goal)+1), times_goal, color='gold', edgecolor='k')
                    ax.set_xlabel('Goal #')
                    ax.set_ylabel('Time (s)')
                    ax.set_title('Cumulative Time to Each Goal')
                    ax.grid(True, alpha=0.3, axis='y')
                    fig.tight_layout()
                    fig.savefig(os.path.join(folder, f'04_goals_time_{sess}.png'), dpi=150, bbox_inches='tight', facecolor='white')
                    saved.append('04_goals_time')
                    plt.close(fig)
                    
                    # 5. Inter-Goal Time
                    if len(times_goal) > 1:
                        inter = np.diff(times_goal)
                        fig, ax = plt.subplots(figsize=(8, 6))
                        ax.bar(range(1, len(inter)+1), inter, color='#3498db', edgecolor='k')
                        ax.axhline(np.mean(inter), color='r', ls='--', lw=2, label=f'Mean {np.mean(inter):.1f}s')
                        ax.set_xlabel('Interval')
                        ax.set_ylabel('Time (s)')
                        ax.set_title('Time Between Goals')
                        ax.legend()
                        ax.grid(True, alpha=0.3, axis='y')
                        fig.tight_layout()
                        fig.savefig(os.path.join(folder, f'05_goals_intervals_{sess}.png'), dpi=150, bbox_inches='tight', facecolor='white')
                        saved.append('05_goals_intervals')
                        plt.close(fig)
                    
                    # 6. Goal Positions
                    if 'x' in coll.columns and 'z' in coll.columns:
                        fig, ax = plt.subplots(figsize=(8, 8))
                        if 'x' in track.columns:
                            ax.plot(track['x'], track['z'], 'b-', alpha=0.3, lw=0.5)
                        for i, (_, r) in enumerate(coll.iterrows()):
                            ax.scatter(r['x'], r['z'], c='gold', s=200, marker='*', edgecolors='k', zorder=10)
                            ax.annotate(f'{i+1}', (r['x'], r['z']), xytext=(5,5), textcoords='offset points', fontsize=10)
                        ax.set_xlabel('X (m)')
                        ax.set_ylabel('Z (m)')
                        ax.set_title('Goal Positions on Path')
                        ax.set_aspect('equal')
                        ax.grid(True, alpha=0.3)
                        fig.tight_layout()
                        fig.savefig(os.path.join(folder, f'06_goals_positions_{sess}.png'), dpi=150, bbox_inches='tight', facecolor='white')
                        saved.append('06_goals_positions')
                        plt.close(fig)
            
            # SAFETY
            dist_safe = 'dist_boundary' if 'dist_boundary' in track.columns else ('dist_local' if 'dist_local' in track.columns else None)
            
            # 7. Safety Zones Over Time
            if dist_safe:
                dist_s = track[dist_safe].values
                dist_s = np.where(dist_s < 0, 999, dist_s)
                
                fig, ax = plt.subplots(figsize=(10, 6))
                ax.fill_between(time_arr, 0, 5, where=dist_s<1, color='red', alpha=0.5, label='Danger <1m')
                ax.fill_between(time_arr, 0, 5, where=(dist_s>=1)&(dist_s<2), color='yellow', alpha=0.5, label='Warning 1-2m')
                ax.fill_between(time_arr, 0, 5, where=dist_s>=2, color='green', alpha=0.3, label='Safe >2m')
                ax.plot(time_arr, np.minimum(dist_s, 5), 'k-', lw=0.5, alpha=0.5)
                ax.set_xlabel('Time (s)')
                ax.set_ylabel('Distance (m)')
                ax.set_title('Safety Zones Over Time')
                ax.legend()
                ax.set_ylim(0, 5)
                ax.grid(True, alpha=0.3)
                fig.tight_layout()
                fig.savefig(os.path.join(folder, f'07_safety_zones_{sess}.png'), dpi=150, bbox_inches='tight', facecolor='white')
                saved.append('07_safety_zones')
                plt.close(fig)
            
            # 8. Events by Category
            if 'event' in data.columns and 'category' in data.columns:
                enter = data[data['event'] == 'ENTER']
                if len(enter) > 0:
                    cats = {0:'Boundary', 1:'Obstacle', 2:'Goal', 3:'Interact', 4:'Hazard'}
                    counts = enter['category'].value_counts()
                    labels = [cats.get(int(c), f'C{c}') for c in counts.index]
                    colors = ['#1abc9c', '#e67e22', '#9b59b6', '#3498db', '#c0392b']
                    
                    fig, ax = plt.subplots(figsize=(8, 6))
                    ax.bar(labels, counts.values, color=colors[:len(labels)], edgecolor='k')
                    ax.set_xlabel('Category')
                    ax.set_ylabel('ENTER Events')
                    ax.set_title('Proximity Events by Category')
                    ax.tick_params(axis='x', rotation=45)
                    ax.grid(True, alpha=0.3, axis='y')
                    fig.tight_layout()
                    fig.savefig(os.path.join(folder, f'08_safety_events_{sess}.png'), dpi=150, bbox_inches='tight', facecolor='white')
                    saved.append('08_safety_events')
                    plt.close(fig)
            
            # 9. Distance Distribution
            if dist_safe:
                dv = dist_s[dist_s < 100]
                if len(dv) > 0:
                    fig, ax = plt.subplots(figsize=(8, 6))
                    ax.hist(dv, bins=30, color='#3498db', edgecolor='k', alpha=0.7)
                    ax.axvline(2.0, color='r', ls='--', lw=2, label='Safety Threshold')
                    ax.axvline(np.mean(dv), color='g', ls='-', lw=2, label=f'Mean {np.mean(dv):.1f}m')
                    ax.set_xlabel('Distance (m)')
                    ax.set_ylabel('Frequency')
                    ax.set_title('Distance to Boundary Distribution')
                    ax.legend()
                    ax.grid(True, alpha=0.3)
                    fig.tight_layout()
                    fig.savefig(os.path.join(folder, f'09_safety_distribution_{sess}.png'), dpi=150, bbox_inches='tight', facecolor='white')
                    saved.append('09_safety_distribution')
                    plt.close(fig)
            
            # 10. Cumulative Collisions
            if 'collisions' in track.columns:
                fig, ax = plt.subplots(figsize=(10, 6))
                ax.plot(time_arr, track['collisions'].values, 'r-', lw=2)
                ax.fill_between(time_arr, 0, track['collisions'].values, color='red', alpha=0.3)
                ax.set_xlabel('Time (s)')
                ax.set_ylabel('Cumulative Collisions')
                ax.set_title('Collision Accumulation Over Time')
                ax.grid(True, alpha=0.3)
                fig.tight_layout()
                fig.savefig(os.path.join(folder, f'10_safety_collisions_{sess}.png'), dpi=150, bbox_inches='tight', facecolor='white')
                saved.append('10_safety_collisions')
                plt.close(fig)
            
            # VELOCITY
            if 'velocity' in track.columns or 'x' in track.columns:
                if 'velocity' in track.columns:
                    vel = track['velocity'].values
                else:
                    dx = np.diff(track['x'].values, prepend=track['x'].iloc[0])
                    dz = np.diff(track['z'].values, prepend=track['z'].iloc[0])
                    dt = np.diff(time_arr, prepend=0)
                    dt[0] = dt[1] if len(dt) > 1 else 0.1
                    dt = np.where(dt == 0, 0.001, dt)
                    vel = np.sqrt(dx**2 + dz**2) / dt
                
                # 11. Velocity Over Time
                fig, ax = plt.subplots(figsize=(10, 6))
                ax.plot(time_arr, vel, 'b-', alpha=0.5, lw=1, label='Raw')
                if HAS_SCIPY and len(vel) > 15:
                    w = min(51, len(vel)//2*2+1)
                    if w >= 5:
                        try:
                            ax.plot(time_arr, savgol_filter(vel, w, 3), 'r-', lw=2, label='Smooth')
                        except:
                            pass
                m = np.mean(vel)
                s = np.std(vel)
                ax.axhline(m, color='g', ls='--', lw=2, label=f'Mean {m:.2f}')
                ax.fill_between(time_arr, m-s, m+s, color='g', alpha=0.1)
                ax.set_xlabel('Time (s)')
                ax.set_ylabel('Velocity (m/s)')
                ax.set_title('Velocity Profile Over Time')
                ax.legend()
                ax.grid(True, alpha=0.3)
                fig.tight_layout()
                fig.savefig(os.path.join(folder, f'11_velocity_profile_{sess}.png'), dpi=150, bbox_inches='tight', facecolor='white')
                saved.append('11_velocity_profile')
                plt.close(fig)
                
                # 12. Velocity Distribution
                fig, ax = plt.subplots(figsize=(8, 6))
                ax.hist(vel, bins=40, color='#3498db', edgecolor='k', alpha=0.7, density=True)
                ax.axvline(m, color='g', ls='-', lw=2, label=f'Mean {m:.2f}')
                ax.axvline(np.median(vel), color='orange', ls='--', lw=2, label=f'Median {np.median(vel):.2f}')
                ax.set_xlabel('Velocity (m/s)')
                ax.set_ylabel('Density')
                ax.set_title('Velocity Distribution')
                ax.legend()
                ax.grid(True, alpha=0.3)
                fig.tight_layout()
                fig.savefig(os.path.join(folder, f'12_velocity_distribution_{sess}.png'), dpi=150, bbox_inches='tight', facecolor='white')
                saved.append('12_velocity_distribution')
                plt.close(fig)
            
            # HEADING
            if 'x' in track.columns and 'z' in track.columns:
                x, z = track['x'].values, track['z'].values
                dx, dz = np.diff(x), np.diff(z)
                mag = np.sqrt(dx**2 + dz**2)
                valid = mag > 0.01
                angles = np.arctan2(dz, dx)
                time_h = time_arr[1:]
                
                # 13. Heading Over Time
                fig, ax = plt.subplots(figsize=(10, 6))
                ax.plot(time_h[valid], np.degrees(angles[valid]), 'b-', alpha=0.5, lw=1)
                ax.set_xlabel('Time (s)')
                ax.set_ylabel('Heading (degrees)')
                ax.set_title('Heading Over Time')
                ax.set_ylim(-180, 180)
                ax.grid(True, alpha=0.3)
                fig.tight_layout()
                fig.savefig(os.path.join(folder, f'13_heading_time_{sess}.png'), dpi=150, bbox_inches='tight', facecolor='white')
                saved.append('13_heading_time')
                plt.close(fig)
                
                # 14. Heading Distribution (Polar)
                fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(projection='polar'))
                hist, bins = np.histogram(angles[valid], bins=16, range=(-np.pi, np.pi))
                ax.bar(bins[:-1], hist, width=2*np.pi/16, alpha=0.7, color='#3498db', edgecolor='k')
                ax.set_title('Heading Distribution (Polar)', pad=20)
                fig.tight_layout()
                fig.savefig(os.path.join(folder, f'14_heading_polar_{sess}.png'), dpi=150, bbox_inches='tight', facecolor='white')
                saved.append('14_heading_polar')
                plt.close(fig)
                
                # 15. Direction Changes
                fig, ax = plt.subplots(figsize=(10, 6))
                if 'heading_changes' in track.columns:
                    ax.plot(time_arr, track['heading_changes'].values, 'purple', lw=2)
                    ax.fill_between(time_arr, 0, track['heading_changes'].values, color='purple', alpha=0.3)
                else:
                    changes = np.abs(np.diff(angles[valid]))
                    changes = np.where(changes > np.pi, 2*np.pi - changes, changes)
                    cum = np.cumsum(changes > 0.5)
                    ax.plot(time_h[valid][1:], cum, 'purple', lw=2)
                    ax.fill_between(time_h[valid][1:], 0, cum, color='purple', alpha=0.3)
                ax.set_xlabel('Time (s)')
                ax.set_ylabel('Cumulative Changes')
                ax.set_title('Significant Direction Changes (>30°)')
                ax.grid(True, alpha=0.3)
                fig.tight_layout()
                fig.savefig(os.path.join(folder, f'15_heading_changes_{sess}.png'), dpi=150, bbox_inches='tight', facecolor='white')
                saved.append('15_heading_changes')
                plt.close(fig)
                
                # 16. Movement Vectors
                fig, ax = plt.subplots(figsize=(10, 10))
                step = max(1, len(x)//100)
                q = ax.quiver(x[:-1:step], z[:-1:step], dx[::step], dz[::step], mag[::step], cmap='viridis', alpha=0.7)
                fig.colorbar(q, ax=ax, label='Magnitude')
                ax.set_xlabel('X (m)')
                ax.set_ylabel('Z (m)')
                ax.set_title('Movement Vectors')
                ax.set_aspect('equal')
                ax.grid(True, alpha=0.3)
                fig.tight_layout()
                fig.savefig(os.path.join(folder, f'16_heading_vectors_{sess}.png'), dpi=150, bbox_inches='tight', facecolor='white')
                saved.append('16_heading_vectors')
                plt.close(fig)
            
            # Index file
            with open(os.path.join(folder, f'00_index_{sess}.txt'), 'w') as f:
                f.write(f"Lyra Scientific Figures\n")
                f.write(f"Session: {self.current_session}\n")
                f.write(f"Generated: {datetime.now()}\n")
                f.write(f"Total Figures: {len(saved)}\n\n")
                f.write("Files:\n")
                for s in sorted(saved):
                    f.write(f"  {s}.png\n")
            
            messagebox.showinfo("OK", f"Saved {len(saved)} individual figures to:\n{folder}")
        except Exception as e:
            messagebox.showerror("Error", str(e))
            import traceback
            traceback.print_exc()

    def run_full_analysis(self):
        if self.df is None:
            messagebox.showwarning("Warning", "Load data first")
            return
        
        data = self._get_data()
        track = self._get_track()
        time = self._get_time(data)
        duration = time[-1] if len(time) > 0 else 0
        
        r = []
        r.append("=" * 60)
        r.append("LYRA SCIENTIFIC REPORT")
        r.append("=" * 60)
        r.append(f"Generated: {datetime.now()}")
        r.append(f"Session: {self.current_session}")
        r.append(f"File: {os.path.basename(self.current_file)}")
        
        r.append("\n" + "=" * 60)
        r.append("1. SESSION OVERVIEW")
        r.append("=" * 60)
        r.append(f"Records: {len(data)}")
        r.append(f"Track Points: {len(track)}")
        r.append(f"Duration: {duration:.1f}s ({duration/60:.1f} min)")
        
        if 'event' in data.columns:
            r.append("\nEvents:")
            for e, c in data['event'].value_counts().items():
                r.append(f"  {e}: {c}")
        
        r.append("\n" + "=" * 60)
        r.append("2. NAVIGATION")
        r.append("=" * 60)
        
        if 'total_distance' in track.columns:
            dist = track['total_distance'].max()
            r.append(f"Total Distance: {dist:.1f} m")
        elif 'x' in track.columns:
            dx = np.diff(track['x'].values)
            dz = np.diff(track['z'].values)
            dist = np.sum(np.sqrt(dx**2 + dz**2))
            r.append(f"Distance (calc): {dist:.1f} m")
        
        if 'velocity' in track.columns:
            v = track['velocity'].values
            r.append(f"\nVelocity:")
            r.append(f"  Mean: {np.mean(v):.3f} m/s")
            r.append(f"  SD: {np.std(v):.3f}")
            r.append(f"  Max: {np.max(v):.3f}")
        
        r.append("\n" + "=" * 60)
        r.append("3. GOALS")
        r.append("=" * 60)
        
        if 'event' in data.columns:
            coll = data[data['event'] == 'COLLECT']
            r.append(f"Goals Collected: {len(coll)}")
            if len(coll) > 0:
                times = self._get_time(coll)
                r.append(f"First Goal: {times[0]:.1f}s")
                r.append(f"Last Goal: {times[-1]:.1f}s")
                if len(times) > 1:
                    inter = np.diff(times)
                    r.append(f"Mean Interval: {np.mean(inter):.1f}s")
        
        r.append("\n" + "=" * 60)
        r.append("4. SAFETY")
        r.append("=" * 60)
        
        if 'collisions' in track.columns:
            r.append(f"Collisions: {int(track['collisions'].max())}")
        
        for col in ['dist_boundary', 'dist_local']:
            if col in track.columns:
                d = track[col].values
                d = d[d > 0]
                if len(d) > 0:
                    r.append(f"\nDistance ({col}):")
                    r.append(f"  Mean: {np.mean(d):.2f} m")
                    r.append(f"  Min: {np.min(d):.2f} m")
                    danger = np.sum(d < 1) / len(d) * 100
                    r.append(f"  Danger Zone: {danger:.1f}%")
                break
        
        r.append("\n" + "=" * 60)
        r.append("END OF REPORT")
        r.append("=" * 60)
        
        self.report_text.config(state=tk.NORMAL)
        self.report_text.delete(1.0, tk.END)
        self.report_text.insert(tk.END, "\n".join(r))
        self.report_text.config(state=tk.DISABLED)
        
        self.notebook.select(self.tabs['Report'])

    def export_report(self):
        if self.df is None:
            return
        
        content = self.report_text.get(1.0, tk.END)
        if not content.strip():
            self.run_full_analysis()
            content = self.report_text.get(1.0, tk.END)
        
        sess = self.current_session.replace(':', '-').replace('/', '-')[:25]
        fpath = filedialog.asksaveasfilename(
            title="Save Report",
            defaultextension=".txt",
            initialfile=f"lyra_report_{sess}.txt"
        )
        
        if fpath:
            try:
                with open(fpath, 'w', encoding='utf-8') as f:
                    f.write(content)
                messagebox.showinfo("OK", f"Saved to:\n{fpath}")
            except Exception as e:
                messagebox.showerror("Error", str(e))

    def show_about(self):
        messagebox.showinfo("About", """LYRA Scientific Data Analyser
Version 1.0.0

A comprehensive analysis tool for the Lyra Framework
for Non-Visual Spatial Navigation research.

Features:
• Path visualization and analysis
• Goal achievement metrics
• Safety zone analysis
• Velocity profiling
• Scientific report generation

For research in:
• Spatial Cognition
• Blind Navigation
• Auditory Wayfinding
• 3D Mental Map Construction

Authors:
João Antônio Temochko Andre
Johnata Souza Santicioli
Carolina André da Silva

© 2026 Instituto Federal de Educação, Ciência e Tecnologia de São Paulo & Universidade do Vale do Itajaí""")

    def show_metrics_help(self):
        messagebox.showinfo("Metrics", """
Path Tortuosity: actual/straight distance
Movement Entropy: directional randomness (0-1)
CV: velocity consistency (SD/Mean)
Safety Zones: <1m danger, 1-2m warning, >2m safe
        """)


def main():
    root = tk.Tk()
    try:
        ttk.Style().theme_use('clam')
    except:
        pass
    LyraAnalyser(root)
    root.mainloop()


if __name__ == "__main__":
    main()
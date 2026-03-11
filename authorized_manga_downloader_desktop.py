#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QProcess, Qt, QTimer
from PySide6.QtGui import QAction, QFontDatabase, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QDoubleSpinBox,
    QSplitter,
    QStatusBar,
    QTextEdit,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

APP_ROOT = Path(__file__).resolve().parent
DATA_ROOT = APP_ROOT / "ui-data"
CONFIG_DIR = DATA_ROOT / "desktop-configs"
RUN_DIR = DATA_ROOT / "desktop-runs"
DEFAULT_OUT = str(Path.home() / "Downloads")
WINDOW_TITLE = "漫咚咚"

for path in (DATA_ROOT, CONFIG_DIR, RUN_DIR):
    path.mkdir(parents=True, exist_ok=True)

DEFAULT_CONFIG = {
    "url": "",
    "out": DEFAULT_OUT,
    "title": "",
    "dynamic": True,
    "wait_ms": 2500,
    "delay": 0.3,
    "referer": "",
    "user_agent": "",
    "same_origin_only": False,
    "dry_run": True,
    "flat": False,
    "skip_existing": True,
    "download_timeout": 60,
    "retries": 2,
    "page_start": 1,
    "page_end": None,
    "page_limit": None,
    "save_discovery": True,
    "use_common_page_selectors": False,
    "img_selector": ["img::attr(data-src)", "img::attr(src)"],
    "page_link_selector": [],
    "img_regex": "",
    "page_link_regex": "",
    "manifest_name": "manifest.json",
}


@dataclass
class RunStats:
    discovered_pages: int = 0
    selected_pages: int = 0
    current_page: int = 0
    found_images: int = 0
    downloaded: int = 0
    skipped: int = 0
    failed: int = 0


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.process: QProcess | None = None
        self.current_config_path: Path | None = None
        self.current_run_dir: Path | None = None
        self.current_run_config_path: Path | None = None
        self.current_manifest_path: Path | None = None
        self.current_log_path: Path | None = None
        self.stats = RunStats()

        self.setWindowTitle(WINDOW_TITLE)
        self.resize(1180, 780)
        self._build_ui()
        self._apply_theme()
        self.load_default_config()
        self.refresh_saved_configs()
        self.update_status("漫咚咚待命")

    def _build_ui(self) -> None:
        toolbar = QToolBar("main")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        act_new = QAction("新建模板", self)
        act_new.triggered.connect(self.load_default_config)
        toolbar.addAction(act_new)

        act_open = QAction("打开模板", self)
        act_open.triggered.connect(self.open_config_dialog)
        toolbar.addAction(act_open)

        act_save = QAction("保存模板", self)
        act_save.triggered.connect(self.save_config_dialog)
        toolbar.addAction(act_save)

        act_out = QAction("打开下载目录", self)
        act_out.triggered.connect(self.open_output_dir)
        toolbar.addAction(act_out)

        toolbar.addSeparator()

        act_preview = QAction("试跑预览", self)
        act_preview.triggered.connect(lambda: self.start_run(force_dry_run=True))
        toolbar.addAction(act_preview)

        act_start = QAction("正式下载", self)
        act_start.triggered.connect(lambda: self.start_run(force_dry_run=False))
        toolbar.addAction(act_start)

        act_stop = QAction("停止当前任务", self)
        act_stop.triggered.connect(self.stop_run)
        toolbar.addAction(act_stop)

        root = QWidget()
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)

        self.status_label = QLabel("漫咚咚待命")
        self.summary_label = QLabel("建议先试跑预览，确认抓得啱再正式开下。")
        self.summary_label.setObjectName("summaryLabel")
        outer.addWidget(self.status_label)
        outer.addWidget(self.summary_label)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        outer.addWidget(splitter, 1)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(self._build_basic_group())
        left_layout.addWidget(self._build_selector_group())
        left_layout.addWidget(self._build_option_group())
        left_layout.addStretch(1)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.addWidget(self._build_saved_group(), 0)
        right_layout.addWidget(self._build_log_group(), 1)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([640, 500])

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)

        status = QStatusBar()
        status.addPermanentWidget(self.progress, 1)
        self.setStatusBar(status)

    def _build_basic_group(self) -> QGroupBox:
        box = QGroupBox("基本设置")
        form = QFormLayout(box)

        self.url_edit = QLineEdit()
        self.out_edit = QLineEdit()
        self.title_edit = QLineEdit()
        self.referer_edit = QLineEdit()
        self.user_agent_edit = QLineEdit()

        out_row = QWidget()
        out_layout = QHBoxLayout(out_row)
        out_layout.setContentsMargins(0, 0, 0, 0)
        out_layout.addWidget(self.out_edit, 1)
        browse_btn = QPushButton("选择路径")
        browse_btn.clicked.connect(self.choose_output_dir)
        out_layout.addWidget(browse_btn)

        form.addRow("URL", self.url_edit)
        form.addRow("输出目录", out_row)
        form.addRow("标题", self.title_edit)
        form.addRow("Referer", self.referer_edit)
        form.addRow("User-Agent", self.user_agent_edit)
        return box

    def _build_selector_group(self) -> QGroupBox:
        box = QGroupBox("规则与过滤")
        grid = QGridLayout(box)

        self.img_selector_edit = QPlainTextEdit()
        self.page_selector_edit = QPlainTextEdit()
        self.img_regex_edit = QLineEdit()
        self.page_regex_edit = QLineEdit()

        grid.addWidget(QLabel("图片选择器（每行一个）"), 0, 0)
        grid.addWidget(QLabel("章节/子页选择器（每行一个）"), 0, 1)
        grid.addWidget(self.img_selector_edit, 1, 0)
        grid.addWidget(self.page_selector_edit, 1, 1)
        grid.addWidget(QLabel("图片过滤正则"), 2, 0)
        grid.addWidget(QLabel("页面过滤正则"), 2, 1)
        grid.addWidget(self.img_regex_edit, 3, 0)
        grid.addWidget(self.page_regex_edit, 3, 1)
        return box

    def _build_option_group(self) -> QGroupBox:
        box = QGroupBox("下载选项")
        layout = QGridLayout(box)

        self.wait_spin = QSpinBox(); self.wait_spin.setRange(0, 120000); self.wait_spin.setSingleStep(100)
        self.delay_spin = QDoubleSpinBox(); self.delay_spin.setRange(0, 60); self.delay_spin.setDecimals(1); self.delay_spin.setSingleStep(0.1)
        self.retries_spin = QSpinBox(); self.retries_spin.setRange(0, 20)
        self.timeout_spin = QSpinBox(); self.timeout_spin.setRange(1, 600)
        self.page_start_spin = QSpinBox(); self.page_start_spin.setRange(1, 999999)
        self.page_end_spin = QSpinBox(); self.page_end_spin.setRange(0, 999999); self.page_end_spin.setSpecialValueText("不限")
        self.page_limit_spin = QSpinBox(); self.page_limit_spin.setRange(0, 999999); self.page_limit_spin.setSpecialValueText("不限")

        self.dynamic_check = QCheckBox("dynamic")
        self.dry_run_check = QCheckBox("dry_run")
        self.flat_check = QCheckBox("flat")
        self.skip_check = QCheckBox("skip_existing")
        self.same_origin_check = QCheckBox("same_origin_only")
        self.discovery_check = QCheckBox("save_discovery")
        self.common_pages_check = QCheckBox("use_common_page_selectors")

        layout.addWidget(QLabel("wait_ms"), 0, 0)
        layout.addWidget(self.wait_spin, 0, 1)
        layout.addWidget(QLabel("delay"), 0, 2)
        layout.addWidget(self.delay_spin, 0, 3)
        layout.addWidget(QLabel("retries"), 1, 0)
        layout.addWidget(self.retries_spin, 1, 1)
        layout.addWidget(QLabel("download_timeout"), 1, 2)
        layout.addWidget(self.timeout_spin, 1, 3)
        layout.addWidget(QLabel("page_start"), 2, 0)
        layout.addWidget(self.page_start_spin, 2, 1)
        layout.addWidget(QLabel("page_end"), 2, 2)
        layout.addWidget(self.page_end_spin, 2, 3)
        layout.addWidget(QLabel("page_limit"), 3, 0)
        layout.addWidget(self.page_limit_spin, 3, 1)

        checks = [
            self.dynamic_check,
            self.dry_run_check,
            self.flat_check,
            self.skip_check,
            self.same_origin_check,
            self.discovery_check,
            self.common_pages_check,
        ]
        row = 4
        col = 0
        for check in checks:
            layout.addWidget(check, row, col, 1, 2)
            col += 2
            if col >= 4:
                row += 1
                col = 0
        return box

    def _build_saved_group(self) -> QGroupBox:
        box = QGroupBox("已保存模板")
        layout = QVBoxLayout(box)
        top = QHBoxLayout()
        self.saved_combo = QComboBox()
        self.saved_combo.setMinimumWidth(260)
        top.addWidget(self.saved_combo, 1)

        load_btn = QPushButton("载入模板")
        load_btn.clicked.connect(self.load_selected_config)
        save_btn = QPushButton("另存模板")
        save_btn.clicked.connect(self.save_config_dialog)
        refresh_btn = QPushButton("刷新列表")
        refresh_btn.clicked.connect(self.refresh_saved_configs)
        top.addWidget(load_btn)
        top.addWidget(save_btn)
        top.addWidget(refresh_btn)
        layout.addLayout(top)
        return box

    def _build_log_group(self) -> QGroupBox:
        box = QGroupBox("运行日志")
        layout = QVBoxLayout(box)
        self.log_edit = QTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setAcceptRichText(True)
        fixed = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        self.log_edit.setFont(fixed)
        layout.addWidget(self.log_edit, 1)

        btns = QHBoxLayout()
        clear_btn = QPushButton("清空记录")
        clear_btn.clicked.connect(self.log_edit.clear)
        open_run_btn = QPushButton("打开运行目录")
        open_run_btn.clicked.connect(self.open_run_dir)
        open_manifest_btn = QPushButton("打开 manifest")
        open_manifest_btn.clicked.connect(self.open_manifest)
        btns.addWidget(clear_btn)
        btns.addWidget(open_run_btn)
        btns.addWidget(open_manifest_btn)
        btns.addStretch(1)
        layout.addLayout(btns)
        return box

    def _apply_theme(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow, QWidget { background: #0f172a; color: #e5e7eb; }
            QGroupBox { border: 1px solid #243145; border-radius: 10px; margin-top: 12px; padding: 12px; font-weight: 600; }
            QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 4px; }
            QLineEdit, QPlainTextEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {
                background: #111827; border: 1px solid #334155; border-radius: 8px; padding: 6px;
            }
            QPushButton { background: #2563eb; border: 0; border-radius: 8px; padding: 8px 12px; }
            QPushButton:hover { background: #3b82f6; }
            QToolBar { spacing: 8px; padding: 6px; border-bottom: 1px solid #243145; }
            QStatusBar { background: #111827; }
            QLabel#summaryLabel { color: #94a3b8; }
            QProgressBar { background: #111827; border: 1px solid #334155; border-radius: 6px; text-align: center; }
            QProgressBar::chunk { background: #22c55e; border-radius: 6px; }
            """
        )

    def current_config(self) -> dict:
        page_end = self.page_end_spin.value() or None
        page_limit = self.page_limit_spin.value() or None
        return {
            "url": self.url_edit.text().strip(),
            "out": self.out_edit.text().strip(),
            "title": self.title_edit.text().strip(),
            "dynamic": self.dynamic_check.isChecked(),
            "wait_ms": self.wait_spin.value(),
            "delay": self.delay_spin.value(),
            "referer": self.referer_edit.text().strip(),
            "user_agent": self.user_agent_edit.text().strip(),
            "same_origin_only": self.same_origin_check.isChecked(),
            "dry_run": self.dry_run_check.isChecked(),
            "flat": self.flat_check.isChecked(),
            "skip_existing": self.skip_check.isChecked(),
            "download_timeout": self.timeout_spin.value(),
            "retries": self.retries_spin.value(),
            "page_start": self.page_start_spin.value(),
            "page_end": page_end,
            "page_limit": page_limit,
            "save_discovery": self.discovery_check.isChecked(),
            "use_common_page_selectors": self.common_pages_check.isChecked(),
            "img_selector": self._lines(self.img_selector_edit),
            "page_link_selector": self._lines(self.page_selector_edit),
            "img_regex": self.img_regex_edit.text().strip(),
            "page_link_regex": self.page_regex_edit.text().strip(),
            "manifest_name": "manifest.json",
        }

    def set_config(self, config: dict) -> None:
        cfg = dict(DEFAULT_CONFIG)
        cfg.update(config or {})
        self.url_edit.setText(str(cfg.get("url") or ""))
        self.out_edit.setText(str(cfg.get("out") or DEFAULT_OUT))
        self.title_edit.setText(str(cfg.get("title") or ""))
        self.referer_edit.setText(str(cfg.get("referer") or ""))
        self.user_agent_edit.setText(str(cfg.get("user_agent") or ""))
        self.wait_spin.setValue(int(cfg.get("wait_ms") or 2500))
        self.delay_spin.setValue(float(cfg.get("delay") or 0.3))
        self.retries_spin.setValue(int(cfg.get("retries") or 2))
        self.timeout_spin.setValue(int(cfg.get("download_timeout") or 60))
        self.page_start_spin.setValue(max(1, int(cfg.get("page_start") or 1)))
        self.page_end_spin.setValue(int(cfg.get("page_end") or 0) if cfg.get("page_end") else 0)
        self.page_limit_spin.setValue(int(cfg.get("page_limit") or 0) if cfg.get("page_limit") else 0)
        self.dynamic_check.setChecked(bool(cfg.get("dynamic")))
        self.dry_run_check.setChecked(bool(cfg.get("dry_run")))
        self.flat_check.setChecked(bool(cfg.get("flat")))
        self.skip_check.setChecked(bool(cfg.get("skip_existing", True)))
        self.same_origin_check.setChecked(bool(cfg.get("same_origin_only")))
        self.discovery_check.setChecked(bool(cfg.get("save_discovery", True)))
        self.common_pages_check.setChecked(bool(cfg.get("use_common_page_selectors")))
        self.img_selector_edit.setPlainText("\n".join(cfg.get("img_selector") or []))
        self.page_selector_edit.setPlainText("\n".join(cfg.get("page_link_selector") or []))
        self.img_regex_edit.setText(str(cfg.get("img_regex") or ""))
        self.page_regex_edit.setText(str(cfg.get("page_link_regex") or ""))

    def load_default_config(self) -> None:
        self.current_config_path = None
        self.set_config(DEFAULT_CONFIG)
        self.log_edit.clear()
        self.current_run_dir = None
        self.current_manifest_path = None
        self.current_log_path = None
        self.reset_stats()
        self.update_status("漫咚咚待命")

    def refresh_saved_configs(self) -> None:
        self.saved_combo.clear()
        files = sorted(CONFIG_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        for path in files:
            self.saved_combo.addItem(path.name, str(path))

    def save_config_dialog(self) -> None:
        stamp = time.strftime("%Y%m%d-%H%M%S")
        default_name = self.current_config_path.name if self.current_config_path else f"desktop-config-{stamp}.json"
        path_str, _ = QFileDialog.getSaveFileName(self, "保存模板", str(CONFIG_DIR / default_name), "JSON Files (*.json)")
        if not path_str:
            return
        path = Path(path_str)
        path.write_text(json.dumps(self.current_config(), ensure_ascii=False, indent=2), encoding="utf-8")
        self.current_config_path = path
        self.refresh_saved_configs()
        self.update_status(f"模板已存好：{path.name}")

    def open_config_dialog(self) -> None:
        path_str, _ = QFileDialog.getOpenFileName(self, "打开模板", str(CONFIG_DIR), "JSON Files (*.json)")
        if not path_str:
            return
        self.load_config(Path(path_str))

    def load_selected_config(self) -> None:
        path_str = self.saved_combo.currentData()
        if path_str:
            self.load_config(Path(path_str))

    def load_config(self, path: Path) -> None:
        try:
            config = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            QMessageBox.critical(self, "模板载入失败", str(exc))
            return
        self.current_config_path = path
        self.set_config(config)
        self.update_status(f"模板已载入：{path.name}")

    def choose_output_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "选择下载目录", self.out_edit.text() or DEFAULT_OUT)
        if path:
            self.out_edit.setText(path)

    def open_output_dir(self) -> None:
        self.open_dir(Path(self.out_edit.text().strip() or DEFAULT_OUT))

    def open_run_dir(self) -> None:
        if self.current_run_dir:
            self.open_dir(self.current_run_dir)

    def open_manifest(self) -> None:
        if self.current_manifest_path and self.current_manifest_path.exists():
            self.open_dir(self.current_manifest_path.parent)
        else:
            QMessageBox.information(self, "还没有结果清单", "这一趟还没生成 manifest，可能未跑完，或者中途失败了。")

    def open_dir(self, path: Path) -> None:
        if not path:
            return
        path.mkdir(parents=True, exist_ok=True)
        if sys.platform.startswith("darwin"):
            subprocess.Popen(["open", str(path)])
        elif os.name == "nt":
            os.startfile(str(path))
        else:
            subprocess.Popen(["xdg-open", str(path)])

    def start_run(self, force_dry_run: bool) -> None:
        if self.process and self.process.state() != QProcess.ProcessState.NotRunning:
            QMessageBox.warning(self, "漫咚咚忙紧", "已经有任务在跑，先停掉当前这趟，再开新的。")
            return

        config = self.current_config()
        config["dry_run"] = force_dry_run
        if not config["url"]:
            QMessageBox.warning(self, "缺少链接", "URL 不能为空，先贴一个目标链接先。")
            return
        if not config["out"]:
            QMessageBox.warning(self, "缺少下载目录", "输出目录不能为空，拣个保存位置先。")
            return

        self.reset_stats()
        run_id = time.strftime("%Y%m%d-%H%M%S")
        self.current_run_dir = RUN_DIR / run_id
        self.current_run_dir.mkdir(parents=True, exist_ok=True)
        self.current_run_config_path = self.current_run_dir / "config.json"
        self.current_run_config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
        self.current_log_path = self.current_run_dir / "run.log"
        self.current_manifest_path = None
        self.log_edit.clear()
        self.append_log(f"[ui] run_id={run_id}")
        self.append_log(f"[ui] 模式={'试跑预览' if force_dry_run else '正式下载'}")

        self.process = QProcess(self)
        self.process.setWorkingDirectory(str(APP_ROOT))
        self.process.setProgram(sys.executable)
        self.process.setArguments([str(APP_ROOT / "authorized_manga_downloader.py"), "--config", str(self.current_run_config_path)])
        self.process.readyReadStandardOutput.connect(self.on_stdout)
        self.process.readyReadStandardError.connect(self.on_stderr)
        self.process.finished.connect(self.on_finished)
        self.process.started.connect(lambda: self.update_status("漫咚咚开工中"))
        self.process.start()

    def stop_run(self) -> None:
        if not self.process or self.process.state() == QProcess.ProcessState.NotRunning:
            self.update_status("当前没有任务在跑")
            return
        self.append_log("[ui] stopping process...")
        pid = int(self.process.processId())
        try:
            if os.name == "nt":
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], check=False, capture_output=True)
            else:
                os.kill(pid, signal.SIGTERM)
        except Exception as exc:
            self.append_log(f"<span style='color:#ef4444'>[ui] stop failed: {exc}</span>")
        self.process.kill()
        self.update_status("已停止当前任务")

    def on_stdout(self) -> None:
        if not self.process:
            return
        text = bytes(self.process.readAllStandardOutput()).decode("utf-8", errors="replace")
        self._consume_output(text)

    def on_stderr(self) -> None:
        if not self.process:
            return
        text = bytes(self.process.readAllStandardError()).decode("utf-8", errors="replace")
        self._consume_output(text, is_error=True)

    def _consume_output(self, text: str, is_error: bool = False) -> None:
        if not text:
            return
        if self.current_log_path:
            with self.current_log_path.open("a", encoding="utf-8") as fh:
                fh.write(text)
        for raw_line in text.splitlines():
            self._parse_line(raw_line)
            color = "#ef4444" if is_error or "[warn]" in raw_line.lower() else None
            self.append_log(raw_line, color=color)

    def _parse_line(self, line: str) -> None:
        m = re.search(r"\[info\] discovered pages: (\d+)", line)
        if m:
            self.stats.discovered_pages = int(m.group(1))
        m = re.search(r"\[info\] selected pages: (\d+)", line)
        if m:
            self.stats.selected_pages = int(m.group(1))
        m = re.search(r"\[info\] scanning page (\d+)/(\d+)", line)
        if m:
            self.stats.current_page = int(m.group(1))
            self.stats.selected_pages = int(m.group(2))
        m = re.search(r"\[info\] found (\d+) image\(s\)", line)
        if m:
            self.stats.found_images += int(m.group(1))
        if line.startswith("[ok]"):
            self.stats.downloaded += 1
        elif line.startswith("[skip]"):
            self.stats.skipped += 1
        elif "[warn] failed:" in line:
            self.stats.failed += 1
        if line.startswith("[done] manifest -> "):
            self.current_manifest_path = Path(line.split("->", 1)[1].strip())
        self.refresh_progress()

    def refresh_progress(self) -> None:
        total = self.stats.selected_pages or 0
        current = min(self.stats.current_page, total) if total else 0
        value = int(current * 100 / total) if total else 0
        self.progress.setValue(value)
        bits = []
        if self.stats.selected_pages:
            bits.append(f"页 {self.stats.current_page}/{self.stats.selected_pages}")
        if self.stats.downloaded:
            bits.append(f"已下 {self.stats.downloaded}")
        if self.stats.skipped:
            bits.append(f"跳过 {self.stats.skipped}")
        if self.stats.failed:
            bits.append(f"失败 {self.stats.failed}")
        if self.stats.found_images:
            bits.append(f"发现图片 {self.stats.found_images}")
        self.summary_label.setText(" · ".join(bits) if bits else "建议先试跑预览，确认抓得啱再正式开下。")

    def on_finished(self, exit_code: int, _status) -> None:
        if exit_code == 0:
            self.progress.setValue(100)
            self.update_status("这一趟已完成")
        else:
            self.update_status(f"任务异常结束（退出码 {exit_code}）")
        self.refresh_progress()

    def append_log(self, text: str, color: str | None = None) -> None:
        cursor = self.log_edit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        html = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        if color:
            html = f"<span style='color:{color}'>{html}</span>"
        cursor.insertHtml(html + "<br>")
        self.log_edit.setTextCursor(cursor)
        self.log_edit.ensureCursorVisible()

    def update_status(self, text: str) -> None:
        self.status_label.setText(f"漫咚咚状态：{text}")
        self.statusBar().showMessage(text)

    def reset_stats(self) -> None:
        self.stats = RunStats()
        self.progress.setValue(0)
        self.summary_label.setText("建议先试跑预览，确认抓得啱再正式开下。")

    @staticmethod
    def _lines(edit: QPlainTextEdit) -> list[str]:
        return [line.strip() for line in edit.toPlainText().splitlines() if line.strip()]


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(WINDOW_TITLE)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

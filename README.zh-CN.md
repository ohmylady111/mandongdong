# 漫咚咚 / ManDongDong

[![Windows Release Build](https://github.com/ohmylady111/mandongdong/actions/workflows/windows-release.yml/badge.svg)](https://github.com/ohmylady111/mandongdong/actions/workflows/windows-release.yml)
[![Release](https://img.shields.io/github/v/release/ohmylady111/mandongdong)](https://github.com/ohmylady111/mandongdong/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

一个偏可爱风、但实际能干活的 **授权来源漫画 / 图集下载器**。

> 程序界面显示名是 **漫咚咚**；为了减少 Windows 打包链对中文文件名的兼容问题，EXE / 安装包文件名采用 **ManDongDong**。

[English README](./README.md)

![漫咚咚展示图](./screenshots/mandongdong-hero.svg)

## 这是个什么项目

漫咚咚是一个基于 **PySide6 原生桌面界面** + **Scrapling 抓取能力** 的下载工具。

适用场景：
- 你自己的网站
- 你拥有版权的内容
- 你被明确授权可归档、迁移、备份的来源

**不适用于** 未授权抓取第三方版权内容。

## 当前状态

目前是一个 **MVP 版本**，已经可用，但仍有继续打磨空间。

目前已具备：
- PySide6 原生桌面窗口
- URL / 输出目录 / 标题 / Referer / User-Agent 输入
- 多行 `img_selector` / `page_link_selector`
- 试跑预览（Dry Run）
- 正式下载
- 停止当前任务
- 保存 / 载入 JSON 模板
- 实时日志
- 简单进度统计
- Windows 单文件 EXE / 安装包打包脚本
- GitHub Actions Windows 自动构建流程

## 项目结构

```text
.
├── authorized_manga_downloader.py          # 下载核心逻辑
├── authorized_manga_downloader_desktop.py  # 原生桌面 GUI（PySide6）
├── ManDongDong.spec                        # PyInstaller 打包配置
├── make_program_icon.py                    # 经典图标生成脚本
├── make_program_icon_anime.py              # 二次元图标生成脚本
├── windows-exe-bundle/                     # Windows 打包材料
├── .github/workflows/                      # GitHub Actions 工作流
└── screenshots/                            # 展示图 / 截图资源
```

## 运行要求

### Python
- Python 3.10+

### 桌面界面
- `PySide6>=6.8`

### 抓取引擎
- `scrapling[all]>=0.4.2`

本机安装依赖：

```bash
python3 -m pip install -r requirements.txt
```

## 本地运行

```bash
python3 authorized_manga_downloader_desktop.py
```

## Windows 打包

请看：
- `windows-exe-bundle/README-Windows.md`
- `windows-exe-bundle/START-HERE.txt`

常用入口：
- `windows-exe-bundle/run_native_ui_windows.bat`
- `windows-exe-bundle/build_native_ui_onefile.bat`
- `windows-exe-bundle/build_native_ui_installer.bat`

预期产物：
- `dist\ManDongDong.exe`
- `output\ManDongDong-Setup.exe`

## GitHub Actions 自动构建

仓库现在已经带了 Windows 自动构建流程：

- 工作流文件：`.github/workflows/windows-release.yml`
- 触发方式：
  - 手动触发（workflow_dispatch）
  - 推送类似 `v0.1.1` 的 tag

当你推送版本 tag 时，工作流会构建并把 `dist/ManDongDong.exe` 挂到 Release 里。

## 目前已知限制

- 桌面版已经支持 packaged / frozen 模式下自启动 downloader worker，不再依赖外部 `.py` 路径。
- 当前桌面版仍然是通过子进程调用下载核心，不是把下载逻辑完全重写进 GUI。
- 停止任务目前属于 MVP 式“直接终止进程”，还不是细粒度的优雅取消。
- 进度主要根据页级信号估算，不是按图片精确统计。
- Scrapling 首次安装运行时可能会比较慢。

## 使用边界

请只用于你**有权访问和归档**的来源。

## 许可证

[MIT](./LICENSE)

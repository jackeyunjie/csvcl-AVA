@echo off
chcp 65001 >nul
cd /d "d:\qoder\csvcl - AVA\MT5_AI_Trading"

echo ============================================================
echo   State 数据库 — 一键构建
echo ============================================================
echo.
echo  [前置] 请确认 AVATRADE MT5 已启动并登录
echo  [耗时] 首次约 5-8 分钟，后续约 1 分钟
echo  [产出] data\state_db.sqlite （含34品种×4视角+历史切片）
echo.
echo  按任意键开始，或 Ctrl+C 退出...
pause >nul

echo.
echo [1/3] 清理旧数据...
if exist data\state_db.sqlite del data\state_db.sqlite

echo [2/3] 构建State数据库...
python build_state_db.py

echo.
echo [3/3] 生成可视化报告...
python -c "from python.core.state_database import StateDatabase;from python.core.state_slicer import StateSlicer;db=StateDatabase();s=StateSlicer(db);stats=db.get_stats();aligned=s.get_aligned_symbols('D1',2);print(f'快照:{stats[\"total_snapshots\"]} 切片:{stats[\"total_slices\"]} 品种:{stats[\"unique_symbols\"]}');print(f'EF>=2品种: {len(aligned)}个');[print(f'  {a[\"symbol\"]} {a[\"pattern\"]} ef={a[\"ef_count\"]}') for a in aligned[:10]]"

echo.
echo ============================================================
echo   [完成] State 数据库已位于 data\state_db.sqlite
echo   大小: 请查看文件属性
echo ============================================================
pause

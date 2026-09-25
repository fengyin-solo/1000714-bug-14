"""养护施工业务规则：状态流转、字段校验与筛选口径都收在这里。"""
from __future__ import annotations

from datetime import date
from typing import Any

from app.store import store

MODULE = "work"
REQUIRED_FIELDS = ["施工编号", "关联计划", "承接单位"]
STATUS_ORDER = ["待开工", "施工中", "待验收", "已完工"]
ACTION_RULES = {"确认开工": "施工中", "提交验收": "待验收", "确认完工": "已完工"}
NEGATIVE_ACTIONS = []

# 施工进度只由状态推导，列表、详情、统计都走这一个口径，避免出现两个百分比。
PROGRESS_BY_STATUS = {"待开工": 0, "施工中": 50, "待验收": 80, "已完工": 100}
# 进行中的合计只统计真正在途的任务，待开工不算进来。
ONGOING_STATUSES = ["施工中", "待验收"]
# 编辑时允许修改的字段，状态类字段只能走动作流转，避免被直接改乱。
EDITABLE_FIELDS = ["关联计划", "承接单位", "开工日期", "完工日期", "完成工程量", "监理人员"]


def _serialize(row: dict[str, Any]) -> dict[str, Any]:
    """列表与详情共用的输出结构：进度在这里统一计算，保证两处看到同一个数。"""
    item = dict(row)
    item["施工进度"] = PROGRESS_BY_STATUS.get(str(row.get("status", "")), 0)
    return item


class WorkService:
    def list_entries(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        rows = store.rows(MODULE)
        if keyword:
            rows = [row for row in rows if keyword in str(row.get("施工编号", ""))]
        if status:
            rows = [row for row in rows if row.get("status") == status]
        total = len(rows)
        start = max(page - 1, 0) * size
        return [_serialize(row) for row in rows[start:start + size]], total

    def get_entry(self, entry_id: int) -> dict[str, Any] | None:
        row = store.find(MODULE, entry_id)
        if row is None:
            return None
        return _serialize(row)

    def stats(self) -> list[dict[str, Any]]:
        """列表页统计卡片：进行中只含施工中与待验收，未开工不计入。"""
        rows = store.rows(MODULE)
        month = date.today().strftime("%Y-%m")
        finished_this_month = sum(
            1
            for row in rows
            if row.get("status") == "已完工" and str(row.get("完工日期") or "").startswith(month)
        )
        return [
            {"label": "待开工施工", "value": sum(1 for row in rows if row.get("status") == "待开工")},
            {"label": "施工中单据", "value": sum(1 for row in rows if row.get("status") in ONGOING_STATUSES)},
            {"label": "本月完工数", "value": finished_this_month},
        ]

    def create_entry(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
        missing = [field for field in REQUIRED_FIELDS if not str(values.get(field) or "").strip()]
        if missing:
            return None, missing
        rows = store.rows(MODULE)
        entry = {"id": max((int(row.get("id", 0)) for row in rows), default=0) + 1}
        entry.update({field: values.get(field) for field in REQUIRED_FIELDS})
        entry["status"] = STATUS_ORDER[0]
        entry["pending"] = True
        entry["abnormal"] = False
        rows.append(entry)
        return _serialize(entry), []

    def update_entry(self, entry_id: int, values: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
        """保存编辑结果：只更新白名单字段，保存后列表与详情读到的就是同一条记录。"""
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None, f"施工任务 {entry_id} 不存在或已归档"
        changed = False
        for field in EDITABLE_FIELDS:
            if field in values:
                entry[field] = values.get(field)
                changed = True
        if not changed:
            return None, "没有可保存的字段，请至少修改一项内容"
        return _serialize(entry), "施工任务已保存"

    def run_action(self, entry_id: int, action: str) -> tuple[dict[str, Any] | None, str]:
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None, f"施工任务 {entry_id} 不存在或已归档"
        if action not in ACTION_RULES:
            return None, f"动作「{action}」不属于养护施工可执行范围"
        target = ACTION_RULES[action]
        if target not in STATUS_ORDER:
            return None, f"目标状态「{target}」不在允许的状态序列里"
        entry["status"] = target
        entry["施工状态"] = target
        entry["pending"] = target != STATUS_ORDER[-1]
        entry["abnormal"] = action in NEGATIVE_ACTIONS
        today = date.today().isoformat()
        if action == "确认开工" and not entry.get("开工日期"):
            entry["开工日期"] = today
        if action == "确认完工":
            # 完工日期在这里落定，竣工验收页读的是同一条记录，不会再错位。
            entry["完工日期"] = today
        return _serialize(entry), f"施工任务已{action}"

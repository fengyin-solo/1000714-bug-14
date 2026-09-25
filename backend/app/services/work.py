"""养护施工业务规则：状态流转、字段校验与筛选口径都收在这里。"""
from __future__ import annotations

from datetime import date
from typing import Any

from app.store import store

MODULE = "work"
REQUIRED_FIELDS = ["施工编号", "关联计划", "承接单位"]
EDITABLE_FIELDS = ["关联计划", "承接单位", "开工日期", "完工日期", "完成工程量", "监理人员"]
STATUS_ORDER = ["待开工", "施工中", "待验收", "已完工"]
ACTION_RULES = {"确认开工": "施工中", "提交验收": "待验收", "确认完工": "已完工"}
NEGATIVE_ACTIONS: list[str] = []
PROGRESS_BY_STATUS = {"待开工": 0, "施工中": 50, "待验收": 90, "已完工": 100}
IN_PROGRESS_STATUS = "施工中"


class WorkService:
    def _serialize(self, row: dict[str, Any]) -> dict[str, Any]:
        """列表、详情、导出共用同一份序列化结果，施工进度只在这里算一次。"""
        item = dict(row)
        status = str(row.get("status") or "")
        item["施工状态"] = status or row.get("施工状态")
        item["施工进度"] = PROGRESS_BY_STATUS.get(status, 0)
        return item

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
        return [self._serialize(row) for row in rows[start:start + size]], total

    def get_entry(self, entry_id: int) -> dict[str, Any] | None:
        row = store.find(MODULE, entry_id)
        return self._serialize(row) if row is not None else None

    def stats(self) -> list[dict[str, Any]]:
        """列表头部的合计：进行中的口径只算真正在施工的任务，未开工不计入。"""
        rows = store.rows(MODULE)
        month = date.today().strftime("%Y-%m")
        return [
            {"label": "待开工施工", "value": sum(1 for row in rows if row.get("status") == STATUS_ORDER[0])},
            {"label": "施工中单据", "value": sum(1 for row in rows if row.get("status") == IN_PROGRESS_STATUS)},
            {
                "label": "本月完工数",
                "value": sum(
                    1
                    for row in rows
                    if row.get("status") == STATUS_ORDER[-1]
                    and str(row.get("完工日期") or "").startswith(month)
                ),
            },
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
        return self._serialize(entry), []

    def update_entry(self, entry_id: int, values: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
        """更新承接单位等基础信息；写回同一条记录，列表、详情与验收处读到的自然一致。"""
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None, f"施工任务 {entry_id} 不存在或已归档"
        if "承接单位" in values and not str(values.get("承接单位") or "").strip():
            return None, "承接单位不能为空"
        changed = [field for field in EDITABLE_FIELDS if field in values]
        if not changed:
            return None, "没有可更新的字段，请至少填写一项"
        for field in changed:
            entry[field] = values[field]
        return self._serialize(entry), "施工任务已更新"

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
        entry["pending"] = target != STATUS_ORDER[-1]
        entry["abnormal"] = action in NEGATIVE_ACTIONS
        return self._serialize(entry), f"施工任务已{action}"

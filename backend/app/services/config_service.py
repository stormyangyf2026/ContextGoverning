"""Configuration service — loads system config with priority: DB > env > YAML file.

Also manages user-specific settings and configuration change logging.
"""
from typing import Any, Optional
from sqlalchemy.orm import Session
from app.models.system_config import SystemConfig
from app.models.user_setting import UserSetting
from app.models.config_change_log import ConfigChangeLog
from app.config import get_settings

settings = get_settings()

# Config sections as defined in 08_configuration_management.md
# Loaded from Settings (env vars / .env), comma-separated
VALID_SECTIONS: tuple = tuple(
    s.strip() for s in settings.config_valid_sections.split(",") if s.strip()
)


def get_config(db: Session, section: str, key: str, default: Any = None) -> Any:
    """Get a single config value. Returns DB value if exists, else default."""
    row = (
        db.query(SystemConfig)
        .filter(SystemConfig.section == section, SystemConfig.config_key == key)
        .first()
    )
    return row.config_value if row else default


def get_section(db: Session, section: str) -> dict[str, Any]:
    """Get all config values for a section as a dict {key: value}."""
    rows = db.query(SystemConfig).filter(SystemConfig.section == section).all()
    return {r.config_key: r.config_value for r in rows}


def get_all_configs(db: Session) -> dict[str, dict[str, Any]]:
    """Get all system configs grouped by section."""
    rows = db.query(SystemConfig).order_by(SystemConfig.section, SystemConfig.sort_order).all()
    result: dict[str, dict[str, Any]] = {}
    for r in rows:
        if r.section not in result:
            result[r.section] = {}
        result[r.section][r.config_key] = {
            "value": r.config_value,
            "value_type": r.value_type,
            "description": r.description,
            "default": r.default_value,
            "validation": r.validation,
            "input_hint": r.input_hint,
            "impact_note": r.impact_note,
            "updated_by": r.updated_by,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        }
    return result


def set_config(
    db: Session,
    section: str,
    key: str,
    value: Any,
    changed_by: str,
    reason: str = "",
) -> SystemConfig:
    """Set a single config value. Logs the change."""
    row = (
        db.query(SystemConfig)
        .filter(SystemConfig.section == section, SystemConfig.config_key == key)
        .first()
    )
    if row is None:
        raise ValueError(f"Config not found: {section}.{key}")

    old_value = row.config_value
    row.config_value = value
    row.updated_by = changed_by

    # Log change
    log = ConfigChangeLog(
        config_type="system",
        section=section,
        config_key=key,
        old_value=old_value,
        new_value=value,
        changed_by=changed_by,
        change_reason=reason,
    )
    db.add(log)
    db.commit()
    db.refresh(row)
    return row


def reset_section_to_default(db: Session, section: str, changed_by: str) -> int:
    """Reset all configs in a section to their default values."""
    rows = db.query(SystemConfig).filter(SystemConfig.section == section).all()
    count = 0
    for r in rows:
        if r.config_value != r.default_value:
            log = ConfigChangeLog(
                config_type="system",
                section=section,
                config_key=r.config_key,
                old_value=r.config_value,
                new_value=r.default_value,
                changed_by=changed_by,
                change_reason="Reset to default",
            )
            db.add(log)
            r.config_value = r.default_value
            r.updated_by = changed_by
            count += 1
    db.commit()
    return count


# ---- User Settings ----

def get_user_setting(db: Session, user_id: str, section: str, key: str, default: Any = None) -> Any:
    """Get a user setting value."""
    row = (
        db.query(UserSetting)
        .filter(
            UserSetting.user_id == user_id,
            UserSetting.section == section,
            UserSetting.setting_key == key,
        )
        .first()
    )
    return row.setting_value if row else default


def get_user_settings_section(db: Session, user_id: str, section: str) -> dict[str, Any]:
    """Get all settings for a user in a section."""
    rows = (
        db.query(UserSetting)
        .filter(UserSetting.user_id == user_id, UserSetting.section == section)
        .all()
    )
    return {r.setting_key: r.setting_value for r in rows}


def get_all_user_settings(db: Session, user_id: str) -> dict[str, dict[str, Any]]:
    """Get all user settings grouped by section."""
    rows = db.query(UserSetting).filter(UserSetting.user_id == user_id).all()
    result: dict[str, dict[str, Any]] = {}
    for r in rows:
        if r.section not in result:
            result[r.section] = {}
        result[r.section][r.setting_key] = r.setting_value
    return result


def set_user_setting(
    db: Session, user_id: str, section: str, key: str, value: Any
) -> UserSetting:
    """Upsert a single user setting."""
    row = (
        db.query(UserSetting)
        .filter(
            UserSetting.user_id == user_id,
            UserSetting.section == section,
            UserSetting.setting_key == key,
        )
        .first()
    )
    if row:
        row.setting_value = value
    else:
        row = UserSetting(
            user_id=user_id,
            section=section,
            setting_key=key,
            setting_value=value,
        )
        db.add(row)
    db.commit()
    db.refresh(row)
    return row


def init_default_user_settings(db: Session, user_id: str) -> None:
    """Initialize default settings for a new user."""
    defaults = [
        # Notification preferences
        ("notification_preferences", "channels.in_app", True),
        ("notification_preferences", "channels.email", False),
        ("notification_preferences", "channels.feishu_bot", True),
        ("notification_preferences", "quiet_hours_enabled", False),
        ("notification_preferences", "quiet_hours_start", "22:00"),
        ("notification_preferences", "quiet_hours_end", "08:00"),
        ("notification_preferences", "enabled_types", ["alert", "review_task", "context_update"]),
        # Search preferences
        ("search_preferences", "default_search_mode", "hybrid"),
        ("search_preferences", "results_per_page", 20),
        ("search_preferences", "show_decayed_contexts", False),
        ("search_preferences", "default_sort", "relevance"),
        # UI preferences
        ("ui_preferences", "theme", "light"),
        ("ui_preferences", "language", "zh-CN"),
        ("ui_preferences", "graph_default_zoom", 1.0),
        ("ui_preferences", "graph_show_labels", True),
        ("ui_preferences", "sidebar_collapsed", False),
    ]
    for section, key, value in defaults:
        existing = (
            db.query(UserSetting)
            .filter(
                UserSetting.user_id == user_id,
                UserSetting.section == section,
                UserSetting.setting_key == key,
            )
            .first()
        )
        if not existing:
            db.add(UserSetting(user_id=user_id, section=section, setting_key=key, setting_value=value))
    db.commit()

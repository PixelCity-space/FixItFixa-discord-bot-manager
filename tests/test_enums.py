from core.common.enums import AccessLevel, ActionType, BotStatus


def test_access_level_values_and_ordering():
    assert AccessLevel.USER.value == 0
    assert AccessLevel.INSPECTOR.value == 1
    assert AccessLevel.MECHANIC.value == 2
    assert AccessLevel.BOSS.value == 3
    assert AccessLevel.BOSS > AccessLevel.MECHANIC > AccessLevel.INSPECTOR > AccessLevel.USER


def test_bot_status_enum_values():
    assert BotStatus.RUNNING.value == "running"
    assert BotStatus.STOPPED.value == "stopped"
    assert BotStatus.FAILED.value == "failed"
    assert BotStatus.UNCERTAIN.value == "uncertain"
    assert BotStatus.UPDATING.value == "updating"


def test_action_type_enum_values():
    assert ActionType.RESTART.value == "restart"
    assert ActionType.UPDATE.value == "update"
    assert ActionType.STOP.value == "stop"

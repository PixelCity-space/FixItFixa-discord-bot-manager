import asyncio
from unittest.mock import MagicMock

from bot.autocomplete import bot_id_autocomplete
from core.config.models import BotConfig


def test_autocomplete_logs_command_individual_bots():
    async def run():
        interaction = MagicMock()
        interaction.command.name = "logs"

        bot1 = BotConfig(id="b1", name="Bot Alpha", path="C:\\bots\\alpha", cmd="python app.py")
        bot2 = BotConfig(id="b2", name="Bot Beta", path="C:\\bots\\beta", cmd="python app.py")

        interaction.client.bots = {"b1": bot1, "b2": bot2}

        # Search matches "Alpha"
        choices = await bot_id_autocomplete(interaction, "alpha")
        assert len(choices) == 1
        assert choices[0].name == "Bot Alpha"
        assert choices[0].value == "b1"

    asyncio.run(run())


def test_autocomplete_clustering_for_lifecycle_commands():
    async def run():
        interaction = MagicMock()
        interaction.command.name = "restart"

        bot1 = BotConfig(id="b1", name="Worker 1", path="C:\\bots\\cluster", cmd="python w1.py")
        bot2 = BotConfig(id="b2", name="Worker 2", path="C:\\bots\\cluster", cmd="python w2.py")
        bot3 = BotConfig(id="b3", name="Solo Bot", path="C:\\bots\\solo", cmd="python solo.py")

        interaction.client.bots = {"b1": bot1, "b2": bot2, "b3": bot3}

        # Empty search query returns grouped cluster + solo bot
        choices = await bot_id_autocomplete(interaction, "")
        assert len(choices) == 2
        names = [c.name for c in choices]
        assert "Worker 1 + Worker 2" in names
        assert "Solo Bot" in names

    asyncio.run(run())


def test_autocomplete_filtering_query():
    async def run():
        interaction = MagicMock()
        interaction.command.name = "update"

        bot1 = BotConfig(id="b1", name="Frontend", path="C:\\bots\\fe", cmd="cmd")
        bot2 = BotConfig(id="b2", name="Backend", path="C:\\bots\\be", cmd="cmd")

        interaction.client.bots = {"b1": bot1, "b2": bot2}

        choices = await bot_id_autocomplete(interaction, "front")
        assert len(choices) == 1
        assert choices[0].name == "Frontend"

    asyncio.run(run())


def test_autocomplete_caps_at_25():
    async def run():
        interaction = MagicMock()
        interaction.command.name = "restart"

        bots = {f"b{i}": BotConfig(id=f"b{i}", name=f"Bot {i}", path=f"C:\\bots\\b{i}", cmd="cmd") for i in range(40)}
        interaction.client.bots = bots

        choices = await bot_id_autocomplete(interaction, "")
        assert len(choices) == 25

    asyncio.run(run())

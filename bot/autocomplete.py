import discord
from discord import app_commands

async def bot_id_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    """
    Intelligent autocomplete for bot choices in slash commands.
    Clusters grouped/multi-process bots by repository path for lifecycle actions.
    """
    bot_manager = interaction.client
    choices = []

    cmd_name = interaction.command.name if interaction.command else ""
    is_logs_command = "logs" in cmd_name.lower()

    bots_data = getattr(bot_manager, "bots", {})

    if is_logs_command:
        for bot_id, bot_config in bots_data.items():
            name = bot_config.name
            if current.lower() in name.lower():
                choices.append(app_commands.Choice(name=name, value=bot_id))
    else:
        path_groups = {}
        for bot_id, bot_config in bots_data.items():
            path = bot_config.path
            if path not in path_groups:
                path_groups[path] = []
            path_groups[path].append((bot_id, bot_config.name))

        for path, bots_in_group in path_groups.items():
            if len(bots_in_group) > 1:
                combined_name = " + ".join([b[1] for b in bots_in_group])
                representative_id = bots_in_group[0][0]
                if current.lower() in combined_name.lower():
                    choices.append(app_commands.Choice(name=combined_name, value=representative_id))
            else:
                bot_id, name = bots_in_group[0]
                if current.lower() in name.lower():
                    choices.append(app_commands.Choice(name=name, value=bot_id))

    return choices[:25]

__all__ = ["bot_id_autocomplete"]

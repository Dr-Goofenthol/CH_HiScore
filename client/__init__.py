"""
Clone Hero High Score Client

Local client that monitors Clone Hero scores and submits them to the bot.
"""

from .file_watcher import CloneHeroWatcher, ScoreState

__all__ = ['CloneHeroWatcher', 'ScoreState']

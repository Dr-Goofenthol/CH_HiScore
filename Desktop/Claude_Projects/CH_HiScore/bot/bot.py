"""
Clone Hero High Score Discord Bot

Main bot file with Discord commands and HTTP API
"""

import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import sys
from pathlib import Path

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

from .config import Config
from .api import ScoreAPI
from .database import Database

# Version and update check
BOT_VERSION = "2.4.8"
GITHUB_REPO = "Dr-Goofenthol/CH_HiScore"


def check_for_client_update():
    """Check GitHub for latest client version and return info if newer than bot version"""
    if not HAS_REQUESTS:
        return None

    try:
        response = requests.get(
            f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest",
            timeout=10,
            headers={"Accept": "application/vnd.github.v3+json"}
        )

        if response.status_code != 200:
            return None

        release = response.json()
        latest_version = release["tag_name"].lstrip("v")

        # Check if there's a client update available
        # Find the client asset
        client_url = None
        for asset in release.get("assets", []):
            if "Tracker" in asset["name"] and asset["name"].endswith(".exe"):
                client_url = asset["browser_download_url"]
                break

        if client_url and latest_version > BOT_VERSION:
            return {
                "version": latest_version,
                "download_url": client_url,
                "release_notes": release.get("body", ""),
                "release_url": release["html_url"]
            }

        return None

    except Exception:
        return None


class CloneHeroBot(commands.Bot):
    """Clone Hero High Score Bot"""

    def __init__(self):
        # Set up intents (permissions for what the bot can see/do)
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True

        super().__init__(
            command_prefix='!',  # Fallback prefix (we'll use slash commands)
            intents=intents,
            application_id=Config.DISCORD_APP_ID
        )

        self.pairing_codes = {}  # Store pairing codes temporarily
        self.db = Database()  # Database connection
        self.api = ScoreAPI(self)  # HTTP API for score submission

    async def setup_hook(self):
        """Called when bot is starting up"""
        print("[*] Setting up bot...")

        # Run migrations before initializing schema
        print("[*] Running database migrations...")
        try:
            from .migrations import run_migrations
            run_migrations(self.db.db_path)
        except Exception as e:
            print(f"[!] Migration warning: {e}")

        # Initialize database
        self.db.connect()
        self.db.initialize_schema()

        # Sync slash commands with Discord
        # For testing, sync to specific guild (faster)
        # For production, remove guild parameter to sync globally (takes up to 1 hour)
        if Config.DISCORD_GUILD_ID:
            guild = discord.Object(id=int(Config.DISCORD_GUILD_ID))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            print(f"[+] Commands synced to guild {Config.DISCORD_GUILD_ID}")
        else:
            await self.tree.sync()
            print("[+] Commands synced globally")

    async def on_ready(self):
        """Called when bot successfully connects to Discord"""
        print("\n" + "=" * 50)
        print(f"[+] Bot is online and connected!")
        print(f"[+] Logged in as: {self.user.name} (ID: {self.user.id})")
        print(f"[+] Connected to {len(self.guilds)} server(s)")
        print("=" * 50 + "\n")

        # List servers
        if self.guilds:
            print("Connected to servers:")
            for guild in self.guilds:
                print(f"  - {guild.name} (ID: {guild.id})")
            print()

        # Start HTTP API
        await self.api.start()

        # Check for updates and notify Discord channel
        await self.check_and_notify_update()

    async def check_and_notify_update(self):
        """Check for client updates and send one-time notification to Discord"""
        try:
            # Only notify once per bot session
            if hasattr(self, '_update_notified') and self._update_notified:
                return

            update_info = check_for_client_update()
            if not update_info:
                print("[*] No client updates available")
                return

            # Get announcement channel
            channel_id = Config.DISCORD_CHANNEL_ID
            if not channel_id:
                return

            channel = self.get_channel(int(channel_id))
            if not channel:
                return

            # Create update announcement embed
            embed = discord.Embed(
                title="🔄 Client Update Available!",
                description=f"A new version of the Clone Hero Score Tracker is available.",
                color=discord.Color.blue()
            )

            embed.add_field(
                name="New Version",
                value=f"v{update_info['version']}",
                inline=True
            )

            embed.add_field(
                name="Current Bot Version",
                value=f"v{BOT_VERSION}",
                inline=True
            )

            # Add release notes if available (truncated)
            if update_info.get("release_notes"):
                notes = update_info["release_notes"].strip()
                if len(notes) > 500:
                    notes = notes[:500] + "..."
                embed.add_field(
                    name="What's New",
                    value=notes,
                    inline=False
                )

            embed.add_field(
                name="Download",
                value=f"[Get the latest version]({update_info['release_url']})",
                inline=False
            )

            embed.set_footer(text="Players should update their clients to get the latest features and fixes.")

            await channel.send(embed=embed)
            self._update_notified = True
            print(f"[+] Update notification sent to #{channel.name}")

        except Exception as e:
            print(f"[!] Error sending update notification: {e}")


# Create bot instance
bot = CloneHeroBot()


# ============================================================================
# SLASH COMMANDS
# ============================================================================

@bot.tree.command(name="ping", description="Check if the bot is responsive")
async def ping(interaction: discord.Interaction):
    """Simple ping command to test bot"""
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(
        f"🏓 Pong! Latency: {latency}ms",
        ephemeral=True  # Only visible to user who ran command
    )


@bot.tree.command(name="pair", description="Link your Discord account to your Clone Hero client")
@app_commands.describe(code="The 6-digit pairing code from your client")
async def pair(interaction: discord.Interaction, code: str):
    """
    Pair a user's Discord account with their Clone Hero client

    The flow:
    1. User runs local client, gets pairing code
    2. User runs /pair <code> in Discord
    3. Bot validates code and links Discord ID to client
    4. Client receives auth token for future score submissions
    """
    await interaction.response.defer(ephemeral=True)

    # Normalize code (uppercase, remove spaces)
    code = code.upper().strip()

    # Validate code format
    if len(code) != 6 or not code.isalnum():
        await interaction.followup.send(
            "Invalid pairing code format. Please enter the 6-character code shown in your client.",
            ephemeral=True
        )
        return

    # Attempt to complete pairing
    discord_id = str(interaction.user.id)
    discord_username = interaction.user.display_name

    auth_token = bot.db.complete_pairing(code, discord_id, discord_username)

    if auth_token:
        await interaction.followup.send(
            f"**Pairing successful!**\n\n"
            f"Your Discord account is now linked to your Clone Hero client.\n"
            f"Scores will automatically be submitted when you play!\n\n"
            f"*Your client should now show 'Paired' status.*",
            ephemeral=True
        )
        print(f"[+] User paired: {discord_username} ({discord_id})")
    else:
        await interaction.followup.send(
            f"**Pairing failed!**\n\n"
            f"The code `{code}` is invalid or has expired.\n"
            f"Please generate a new code from your client and try again.\n\n"
            f"*Codes expire after 5 minutes.*",
            ephemeral=True
        )


@bot.tree.command(name="leaderboard", description="Show Clone Hero high scores")
@app_commands.describe(
    difficulty="Filter by difficulty",
    instrument="Filter by instrument"
)
@app_commands.choices(
    difficulty=[
        app_commands.Choice(name="Easy", value=0),
        app_commands.Choice(name="Medium", value=1),
        app_commands.Choice(name="Hard", value=2),
        app_commands.Choice(name="Expert", value=3),
    ],
    instrument=[
        app_commands.Choice(name="Lead Guitar", value=0),
        app_commands.Choice(name="Bass", value=1),
        app_commands.Choice(name="Rhythm", value=2),
        app_commands.Choice(name="Keys", value=3),
        app_commands.Choice(name="Drums", value=4),
    ]
)
async def leaderboard(
    interaction: discord.Interaction,
    difficulty: app_commands.Choice[int] = None,
    instrument: app_commands.Choice[int] = None
):
    """Show high scores leaderboard"""
    await interaction.response.defer()

    # Get filters
    difficulty_id = difficulty.value if difficulty else None
    instrument_id = instrument.value if instrument else None

    # Get leaderboard from database
    scores = bot.db.get_leaderboard(
        limit=10,
        instrument_id=instrument_id,
        difficulty_id=difficulty_id
    )

    # Build filter text
    filters = []
    if difficulty:
        filters.append(difficulty.name)
    if instrument:
        filters.append(instrument.name)
    filter_text = " | ".join(filters) if filters else "All"

    embed = discord.Embed(
        title="Clone Hero High Scores",
        description=f"**Filters:** {filter_text}",
        color=discord.Color.blue()
    )

    if scores:
        # Format leaderboard
        instruments = {0: "Lead", 1: "Bass", 2: "Rhythm", 3: "Keys", 4: "Drums"}
        difficulties = {0: "Easy", 1: "Med", 2: "Hard", 3: "Expert"}

        leaderboard_text = ""
        for i, score in enumerate(scores, 1):
            inst = instruments.get(score['instrument_id'], '?')
            diff = difficulties.get(score['difficulty_id'], '?')

            # Show full chart hash if title is available, or just hash if not
            song_title = score.get('song_title')
            artist = score.get('song_artist')
            chart_hash = score['chart_hash']

            if song_title:
                song_display = f"{song_title}"
                if artist:
                    song_display += f" - {artist}"
                # Truncate hash to first 8 chars to avoid embed length limits
                song_display += f"\n   Hash: `{chart_hash[:8]}...`"
            else:
                # Truncate hash to first 8 chars
                song_display = f"Chart Hash: `{chart_hash[:8]}...`"

            leaderboard_text += f"**{i}.** {score['discord_username']}\n"
            leaderboard_text += f"   {score['score']:,} pts | {diff} {inst}\n"
            leaderboard_text += f"   {song_display}\n"

        embed.add_field(
            name="Top Scores",
            value=leaderboard_text or "No scores yet!",
            inline=False
        )
    else:
        embed.add_field(
            name="No Scores",
            value="No scores have been submitted yet.\nPlay Clone Hero to set some records!",
            inline=False
        )

    embed.set_footer(text="Use /pair to link your client and start submitting!")

    await interaction.followup.send(embed=embed)


@bot.tree.command(name="mystats", description="Show Clone Hero statistics for yourself or another user")
@app_commands.describe(user="The user to look up (leave empty for your own stats)")
async def mystats(interaction: discord.Interaction, user: discord.Member = None):
    """Show user's personal stats"""
    await interaction.response.defer()

    # Use provided user or default to command caller
    target_user = user or interaction.user
    discord_id = str(target_user.id)
    display_name = target_user.display_name

    stats = bot.db.get_user_stats(discord_id)
    records = bot.db.get_user_records(discord_id, limit=5)

    embed = discord.Embed(
        title=f"Stats for {display_name}",
        color=discord.Color.green()
    )

    if stats:
        # Main stats row
        embed.add_field(
            name="Total Scores",
            value=str(stats['total_scores']),
            inline=True
        )
        embed.add_field(
            name="Records Held",
            value=str(stats['high_scores_held']),
            inline=True
        )
        embed.add_field(
            name="Records Broken",
            value=str(stats['record_breaks']),
            inline=True
        )

        # Performance stats row
        embed.add_field(
            name="Total Points",
            value=f"{stats['total_points']:,}",
            inline=True
        )
        embed.add_field(
            name="Avg Accuracy",
            value=f"{stats['avg_accuracy']:.1f}%",
            inline=True
        )
        embed.add_field(
            name="Avg Stars",
            value=f"{stats['avg_stars']:.1f}",
            inline=True
        )

        # Top records held
        if records:
            instruments = {0: "Lead", 1: "Bass", 2: "Rhythm", 3: "Keys", 4: "Drums"}
            difficulties = {0: "Easy", 1: "Med", 2: "Hard", 3: "Expert"}

            records_text = ""
            for rec in records:
                inst = instruments.get(rec['instrument_id'], '?')
                diff = difficulties.get(rec['difficulty_id'], '?')

                # Show full chart hash with title/artist if available
                song_title = rec.get('song_title')
                artist = rec.get('song_artist')
                chart_hash = rec['chart_hash']

                if song_title:
                    song_display = f"{song_title}"
                    if artist:
                        song_display += f" - {artist}"
                else:
                    # Truncate hash to first 8 chars
                    song_display = f"Hash: `{chart_hash[:8]}...`"

                records_text += f"• {song_display} ({diff} {inst})\n"
                records_text += f"  {rec['score']:,} pts | Hash: `{chart_hash[:8]}...`\n"

            embed.add_field(
                name="Top Records Held",
                value=records_text,
                inline=False
            )

        embed.set_footer(text=f"Member since: {stats['member_since'][:10]}")
    else:
        if target_user == interaction.user:
            # Viewing own stats
            embed.add_field(
                name="No Data",
                value="You haven't submitted any scores yet!\n\n"
                      "**To get started:**\n"
                      "1. Run the client: `CloneHeroScoreTracker.exe`\n"
                      "2. Complete the pairing process\n"
                      "3. Play Clone Hero!",
                inline=False
            )
        else:
            # Viewing another user's stats
            embed.add_field(
                name="No Data",
                value=f"{display_name} hasn't submitted any scores yet.",
                inline=False
            )

    await interaction.followup.send(embed=embed)


@bot.tree.command(name="lookupsong", description="Search for a song and view/update its metadata")
@app_commands.describe(query="Song title to search for")
async def lookupsong(interaction: discord.Interaction, query: str):
    """Search for songs in the database by title"""
    await interaction.response.defer(ephemeral=True)

    # Search for songs matching the query
    songs = bot.db.search_songs(query, limit=10)

    if not songs:
        await interaction.followup.send(
            f"No songs found matching '{query}'.\n\n"
            f"Songs are only added to the database after someone submits a score for them.",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title=f"Songs matching '{query}'",
        color=discord.Color.blue()
    )

    results_text = ""
    for i, song in enumerate(songs, 1):
        title = song.get('title', '[Unknown]')
        artist = song.get('artist') or '*No artist*'
        hash_short = song['chart_hash'][:8]
        results_text += f"**{i}.** {title}\n"
        results_text += f"    Artist: {artist}\n"
        results_text += f"    Chart Hash: `{hash_short}`\n\n"

    embed.add_field(
        name=f"Found {len(songs)} song(s)",
        value=results_text,
        inline=False
    )

    embed.set_footer(text="Use /setartist <hash> <artist> to update artist info")

    await interaction.followup.send(embed=embed, ephemeral=True)


@bot.tree.command(name="setartist", description="Manually set the artist for a song")
@app_commands.describe(
    hash_prefix="First 8+ characters of the song's chart hash",
    artist="The artist name to set"
)
async def setartist(interaction: discord.Interaction, hash_prefix: str, artist: str):
    """Manually set artist for a song"""
    await interaction.response.defer(ephemeral=True)

    # Clean inputs
    hash_prefix = hash_prefix.lower().strip()
    artist = artist.strip()

    if len(hash_prefix) < 8:
        await interaction.followup.send(
            "Please provide at least 8 characters of the chart hash.\n"
            "Use `/lookupsong <title>` to find the chart hash for a song.",
            ephemeral=True
        )
        return

    # Search for songs with matching hash prefix
    songs = bot.db.search_songs('', limit=100)  # Get all songs
    matching_songs = [s for s in songs if s['chart_hash'].startswith(hash_prefix)]

    # Also try direct lookup if it's a full hash
    if len(hash_prefix) == 32:
        song = bot.db.get_song_info(hash_prefix)
        if song:
            matching_songs = [song]

    if not matching_songs:
        # Try searching by chart hash in the database directly
        bot.db.cursor.execute("""
            SELECT * FROM songs WHERE chart_hash LIKE ?
        """, (f'{hash_prefix}%',))
        rows = bot.db.cursor.fetchall()
        matching_songs = [dict(row) for row in rows]

    if not matching_songs:
        await interaction.followup.send(
            f"No song found with chart hash starting with `{hash_prefix}`.\n\n"
            f"Use `/lookupsong <title>` to find the correct chart hash.",
            ephemeral=True
        )
        return

    if len(matching_songs) > 1:
        # Multiple matches - show them
        songs_list = "\n".join([
            f"• `{s['chart_hash'][:12]}...` - {s.get('title', '[Unknown]')}"
            for s in matching_songs[:5]
        ])
        await interaction.followup.send(
            f"Multiple songs match `{hash_prefix}`:\n{songs_list}\n\n"
            f"Please provide more characters of the chart hash to be specific.",
            ephemeral=True
        )
        return

    # Single match - update the artist
    song = matching_songs[0]
    chart_hash = song['chart_hash']
    old_artist = song.get('artist') or '*None*'

    success = bot.db.update_song_artist(chart_hash, artist)

    if success:
        await interaction.followup.send(
            f"**Artist updated!**\n\n"
            f"**Song:** {song.get('title', '[Unknown]')}\n"
            f"**Old Artist:** {old_artist}\n"
            f"**New Artist:** {artist}\n\n"
            f"*Future leaderboard displays will show the new artist.*",
            ephemeral=True
        )
        print(f"[Bot] Artist updated: {song.get('title')} -> {artist} (by {interaction.user.display_name})")
    else:
        await interaction.followup.send(
            f"Failed to update artist. The song may have been removed.",
            ephemeral=True
        )


@bot.tree.command(name="updatesong", description="Manually update song title and/or artist")
@app_commands.describe(
    hash_prefix="First 8+ characters of the song's chart hash",
    title="The song title to set (optional)",
    artist="The artist name to set (optional)"
)
async def updatesong(interaction: discord.Interaction, hash_prefix: str, title: str = None, artist: str = None):
    """Manually update song title and/or artist"""
    await interaction.response.defer(ephemeral=True)

    # Clean inputs
    hash_prefix = hash_prefix.lower().strip()
    if title:
        title = title.strip()
    if artist:
        artist = artist.strip()

    # Must provide at least one field to update
    if not title and not artist:
        await interaction.followup.send(
            "Please provide at least a `title` or `artist` to update.",
            ephemeral=True
        )
        return

    if len(hash_prefix) < 8:
        await interaction.followup.send(
            "Please provide at least 8 characters of the chart hash.\n"
            "Use `/lookupsong <title>` to find the chart hash for a song.",
            ephemeral=True
        )
        return

    # Search for songs with matching chart hash prefix
    bot.db.cursor.execute("""
        SELECT * FROM songs WHERE chart_hash LIKE ?
    """, (f'{hash_prefix}%',))
    rows = bot.db.cursor.fetchall()
    matching_songs = [dict(row) for row in rows]

    if not matching_songs:
        await interaction.followup.send(
            f"No song found with chart hash starting with `{hash_prefix}`.\n\n"
            f"Use `/lookupsong <title>` to find the correct chart hash.",
            ephemeral=True
        )
        return

    if len(matching_songs) > 1:
        # Multiple matches - show them
        songs_list = "\n".join([
            f"• `{s['chart_hash'][:12]}...` - {s.get('title', '[Unknown]')}"
            for s in matching_songs[:5]
        ])
        await interaction.followup.send(
            f"Multiple songs match `{hash_prefix}`:\n{songs_list}\n\n"
            f"Please provide more characters of the chart hash to be specific.",
            ephemeral=True
        )
        return

    # Single match - update the metadata
    song = matching_songs[0]
    chart_hash = song['chart_hash']
    old_title = song.get('title') or '*None*'
    old_artist = song.get('artist') or '*None*'

    success = bot.db.update_song_metadata(chart_hash, title=title, artist=artist)

    if success:
        response = "**Song metadata updated!**\n\n"
        if title:
            response += f"**Title:** {old_title} → {title}\n"
        else:
            response += f"**Title:** {old_title} (unchanged)\n"

        if artist:
            response += f"**Artist:** {old_artist} → {artist}\n"
        else:
            response += f"**Artist:** {old_artist} (unchanged)\n"

        response += f"\n**Chart Hash:** `{chart_hash[:8]}...`\n"
        response += "\n*Future displays will show the updated info.*"

        await interaction.followup.send(response, ephemeral=True)
        print(f"[Bot] Song updated: {chart_hash[:8]} - title={title}, artist={artist} (by {interaction.user.display_name})")
    else:
        await interaction.followup.send(
            f"Failed to update song. The song may have been removed.",
            ephemeral=True
        )


@bot.tree.command(name="missingartists", description="Show songs that are missing artist information")
async def missingartists(interaction: discord.Interaction):
    """Show songs without artist info"""
    await interaction.response.defer(ephemeral=True)

    songs = bot.db.get_songs_without_artist(limit=15)

    if not songs:
        await interaction.followup.send(
            "All songs have artist information! Nice work!",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="Songs Missing Artist Info",
        description="These songs need artist information.",
        color=discord.Color.orange()
    )

    results_text = ""
    for song in songs:
        title = song.get('title', '[Unknown]')
        hash_short = song['chart_hash'][:8]
        score_count = song.get('score_count', 0)
        results_text += f"• **{title}** ({score_count} scores)\n  Chart Hash: `{hash_short}`\n"

    embed.add_field(
        name=f"{len(songs)} song(s) without artist",
        value=results_text or "None found",
        inline=False
    )

    embed.set_footer(text="Use /setartist <hash> <artist> to add artist info")

    await interaction.followup.send(embed=embed, ephemeral=True)


@bot.tree.command(name="recent", description="Show recent record breaks")
@app_commands.describe(count="Number of recent records to show (1-20, default 5)")
async def recent(interaction: discord.Interaction, count: int = 5):
    """Show recent record breaks"""
    await interaction.response.defer()

    # Validate count
    if count < 1:
        count = 1
    elif count > 20:
        count = 20

    records = bot.db.get_recent_record_breaks(limit=count)

    embed = discord.Embed(
        title="Recent Record Breaks",
        color=discord.Color.gold()
    )

    if records:
        instruments = {0: "Lead", 1: "Bass", 2: "Rhythm", 3: "Keys", 4: "Drums"}
        difficulties = {0: "Easy", 1: "Med", 2: "Hard", 3: "Expert"}

        records_text = ""
        for rec in records:
            inst = instruments.get(rec['instrument_id'], '?')
            diff = difficulties.get(rec['difficulty_id'], '?')
            song = rec.get('song_title', f"[{rec['chart_hash'][:8]}]")
            artist = rec.get('song_artist')
            if artist:
                song = f"{song} - {artist}"

            # Format the timestamp
            broken_at = rec['broken_at'][:10] if rec.get('broken_at') else '?'

            # Build the record text
            records_text += f"**{rec['breaker_name']}** broke the record on:\n"
            records_text += f"  {song} ({diff} {inst})\n"
            records_text += f"  Score: {rec['new_score']:,}"
            if rec.get('previous_score'):
                records_text += f" (was {rec['previous_score']:,}"
                if rec.get('previous_holder_name'):
                    records_text += f" by {rec['previous_holder_name']}"
                records_text += ")"
            records_text += f"\n  *{broken_at}*\n\n"

        embed.add_field(
            name=f"Last {len(records)} Record Break(s)",
            value=records_text[:1024] if len(records_text) > 1024 else records_text,
            inline=False
        )
    else:
        embed.add_field(
            name="No Records Yet",
            value="No record breaks have been recorded yet.\nPlay some songs and beat those high scores!",
            inline=False
        )

    await interaction.followup.send(embed=embed)


# ============================================================================
# ERROR HANDLING
# ============================================================================

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Handle errors in slash commands"""
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(
            f"⏱️ Command on cooldown. Try again in {error.retry_after:.1f}s",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f"❌ An error occurred: {str(error)}",
            ephemeral=True
        )
        print(f"[!] Command error: {error}")


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Start the bot"""
    print("Clone Hero High Score Bot")
    print("=" * 50)

    # Validate configuration
    try:
        Config.validate()
        Config.print_config()
    except ValueError as e:
        print(f"[!] Configuration Error:\n{e}")
        return

    # Check if guild/channel IDs are set
    if not Config.DISCORD_GUILD_ID:
        print("⚠️  WARNING: DISCORD_GUILD_ID not set in .env")
        print("   Commands will sync globally (slower)")
        print("   Get your server ID and add it to .env for faster testing\n")

    if not Config.DISCORD_CHANNEL_ID:
        print("⚠️  WARNING: DISCORD_CHANNEL_ID not set in .env")
        print("   High score announcements will not be posted")
        print("   Get your channel ID and add it to .env\n")

    print("[*] Starting bot...")
    print("[*] Press Ctrl+C to stop\n")

    try:
        bot.run(Config.DISCORD_TOKEN)
    except KeyboardInterrupt:
        print("\n[*] Bot stopped by user")
    except Exception as e:
        print(f"\n[!] Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()

"""
HTTP API for receiving scores from local clients

This API runs alongside the Discord bot and accepts score submissions.
"""

from aiohttp import web
import asyncio
import json
import urllib.parse
from datetime import datetime
from .config import Config
from shared.console import print_success, print_info, print_warning, print_error
from shared.logger import get_bot_logger, log_exception

# Initialize logger
logger = get_bot_logger()


def generate_enchor_url(song_title=None, song_artist=None, charter=None):
    """
    Generate enchor.us search URL based on song metadata.

    Args:
        song_title: Song title (e.g., "Afterglow")
        song_artist: Artist name (e.g., "Syncatto")
        charter: Charter name (e.g., "RLOMBARDI")

    Returns:
        URL string or None if insufficient metadata
    """
    # Need at least title or artist to make a useful search
    if not song_title and not song_artist:
        return None

    params = {}

    if song_title:
        params['name'] = song_title.lower()

    if song_artist:
        params['artist'] = song_artist.lower()

    # Charter parameter helps distinguish multiple charts of same song
    if charter:
        params['charter'] = charter

    # Build URL
    base_url = "https://www.enchor.us/"
    query_string = urllib.parse.urlencode(params)

    return f"{base_url}?{query_string}"


class ScoreAPI:
    """HTTP API for score submission"""

    def __init__(self, bot, config_manager=None):
        """
        Initialize the API

        Args:
            bot: The Discord bot instance
            config_manager: ConfigManager instance for reading settings
        """
        self.bot = bot
        self.config = config_manager
        self.app = web.Application()
        self.setup_routes()
        self.runner = None

    def setup_routes(self):
        """Set up API routes"""
        self.app.router.add_get('/', self.index)
        self.app.router.add_get('/health', self.health)
        self.app.router.add_post('/api/score', self.submit_score)
        self.app.router.add_post('/api/pair/request', self.request_pairing)
        self.app.router.add_get('/api/pair/status/{client_id}', self.check_pairing_status)
        self.app.router.add_post('/api/debug/authorize', self.authorize_debug)
        self.app.router.add_get('/api/unresolved_hashes', self.get_unresolved_hashes)
        self.app.router.add_post('/api/resolve_hashes', self.resolve_hashes)

    async def index(self, request):
        """Root endpoint - API info"""
        return web.json_response({
            'name': 'Clone Hero High Score API',
            'version': '1.0.0',
            'status': 'online',
            'endpoints': {
                'POST /api/score': 'Submit a score',
                'POST /api/pair/request': 'Request a pairing code',
                'GET /api/pair/status/{client_id}': 'Check pairing status',
                'GET /health': 'Health check'
            }
        })

    async def health(self, request):
        """Health check endpoint"""
        return web.json_response({
            'status': 'healthy',
            'bot_connected': self.bot.is_ready(),
            'timestamp': datetime.utcnow().isoformat()
        })

    async def submit_score(self, request):
        """
        Submit a score from a local client

        Expected JSON body:
        {
            "auth_token": "user's auth token from pairing",
            "chart_hash": "ecd1c69af09ebeec96a4ad24754f3eed",
            "instrument_id": 0,
            "difficulty_id": 3,
            "score": 147392,
            "completion_percent": 98.5,
            "stars": 5
        }
        """
        try:
            data = await request.json()

            # Validate required fields
            required = ['auth_token', 'chart_hash', 'instrument_id', 'difficulty_id', 'score']
            missing = [field for field in required if field not in data]
            if missing:
                return web.json_response({
                    'success': False,
                    'error': f'Missing required fields: {", ".join(missing)}'
                }, status=400)

            # Submit score to database
            result = self.bot.db.submit_score(
                auth_token=data['auth_token'],
                chart_hash=data['chart_hash'],
                instrument_id=data['instrument_id'],
                difficulty_id=data['difficulty_id'],
                score=data['score'],
                completion_percent=data.get('completion_percent', 0),
                stars=data.get('stars', 0),
                song_title=data.get('song_title', ''),
                song_artist=data.get('song_artist', ''),
                song_charter=data.get('song_charter', '')
            )

            if not result['success']:
                return web.json_response({
                    'success': False,
                    'error': result.get('error', 'Unknown error')
                }, status=401)

            # Get instrument and difficulty names for logging
            instruments = {0: "Lead", 1: "Bass", 2: "Rhythm", 3: "Keys", 4: "Drums"}
            difficulties = {0: "Easy", 1: "Medium", 2: "Hard", 3: "Expert"}
            inst_name = instruments.get(data['instrument_id'], f"Inst{data['instrument_id']}")
            diff_name = difficulties.get(data['difficulty_id'], f"Diff{data['difficulty_id']}")

            # Log the submission with all fields
            song_title = data.get('song_title', f"[{data['chart_hash'][:8]}]")
            song_artist = data.get('song_artist', '')
            score_type = data.get('score_type', 'raw')  # "raw" or "rich"
            notes_hit = data.get('notes_hit')
            notes_total = data.get('notes_total')
            best_streak = data.get('best_streak')
            ocr_artist = data.get('ocr_artist')

            # If we got an OCR artist and the song doesn't have one, update the DB
            if ocr_artist and not song_artist:
                self.bot.db.update_song_artist(data['chart_hash'], ocr_artist)
                song_artist = ocr_artist

            song_display = song_title
            if song_artist:
                song_display = f"{song_title} - {song_artist}"

            print(f"\n[API] Score received from {result['username']} [{score_type.upper()}]:")
            print(f"  Song: {song_display}")
            print(f"  Chart Hash: {data['chart_hash']}")
            print(f"  Score: {data['score']:,} | {diff_name} {inst_name}")
            if notes_hit is not None and notes_total is not None:
                print(f"  Notes: {notes_hit}/{notes_total} ({data.get('completion_percent', 0):.1f}%)")
            else:
                print(f"  Accuracy: {data.get('completion_percent', 0):.1f}%")
            if best_streak is not None:
                print(f"  Best Streak: {best_streak}")
            print(f"  Stars: {data.get('stars', 0)}")
            print(f"  Result: {'RECORD BROKEN!' if result['is_record_broken'] else 'High Score' if result['is_high_score'] else 'Not a record'}")

            # Post announcements based on achievement type
            # Check if record broken, first-time score, or personal best
            should_announce_record = result.get('is_record_broken', False)
            should_announce_first_time = result.get('is_first_time_score', False)
            should_announce_pb = False

            # Check personal best with improvement thresholds
            if result.get('is_personal_best', False):
                user_prev = result.get('user_previous_score', 0)
                new_score = data.get('score', 0)

                if user_prev > 0:
                    # Calculate improvement
                    points_improvement = new_score - user_prev
                    percent_improvement = (points_improvement / user_prev) * 100

                    # Get thresholds from config (default: 5% and 10,000 points)
                    if self.config:
                        min_percent = self.config.config.get('announcements', {}).get('personal_bests', {}).get('min_improvement_percent', 5.0)
                        min_points = self.config.config.get('announcements', {}).get('personal_bests', {}).get('min_improvement_points', 10000)
                    else:
                        min_percent = 5.0
                        min_points = 10000

                    # Must meet BOTH thresholds to announce
                    if percent_improvement >= min_percent and points_improvement >= min_points:
                        should_announce_pb = True

            should_announce = should_announce_record or should_announce_first_time or should_announce_pb

            if should_announce:
                await self.announce_score(data, result)

            return web.json_response({
                'success': True,
                'message': 'Score submitted successfully',
                'is_high_score': result['is_high_score'],
                'is_record_broken': result['is_record_broken'],
                'previous_score': result.get('previous_score'),
                'previous_holder': result.get('previous_holder'),
                'your_best_score': result.get('your_best_score')  # User's PB for feedback
            })

        except json.JSONDecodeError:
            return web.json_response({
                'success': False,
                'error': 'Invalid JSON'
            }, status=400)
        except Exception as e:
            print_error(f"[API] Error processing score: {e}")
            log_exception(logger, "Error processing score", e)
            import traceback
            traceback.print_exc()
            return web.json_response({
                'success': False,
                'error': str(e)
            }, status=500)

    async def announce_score(self, score_data: dict, result: dict):
        """Post high score announcement to Discord"""
        try:
            channel_id = Config.DISCORD_CHANNEL_ID
            if not channel_id:
                print_warning("[API] No announcement channel configured")
                return

            channel = self.bot.get_channel(int(channel_id))
            if not channel:
                print_error(f"[API] Could not find channel {channel_id}")
                return

            # Get instrument and difficulty names
            instruments = {0: "Lead Guitar", 1: "Bass", 2: "Rhythm", 3: "Keys", 4: "Drums"}
            difficulties = {0: "Easy", 1: "Medium", 2: "Hard", 3: "Expert"}

            instrument_name = instruments.get(score_data['instrument_id'], "Unknown")
            difficulty_name = difficulties.get(score_data['difficulty_id'], "Unknown")

            import discord

            # Determine announcement type and styling
            is_record_broken = result.get('is_record_broken', False)
            is_first_time = result.get('is_first_time_score', False)
            is_personal_best = result.get('is_personal_best', False)

            # Set title, emoji, color, and description based on announcement type
            if is_record_broken:
                title = "🏆 NEW RECORD SET!"
                # Read color from config (default: Gold)
                if self.config:
                    color_hex = self.config.config.get('announcements', {}).get('record_breaks', {}).get('embed_color', '#FFD700')
                else:
                    color_hex = '#FFD700'
                try:
                    color = discord.Color.from_str(color_hex)
                except ValueError:
                    print_warning(f"[API] Invalid color '{color_hex}' for record breaks, using default gold")
                    color = discord.Color.from_str('#FFD700')
                action_text = "set a new server record!"
            elif is_first_time:
                title = "🎸 FIRST SCORE ON CHART!"
                # Read color from config (default: Blue)
                if self.config:
                    color_hex = self.config.config.get('announcements', {}).get('first_time_scores', {}).get('embed_color', '#4169E1')
                else:
                    color_hex = '#4169E1'
                try:
                    color = discord.Color.from_str(color_hex)
                except ValueError:
                    print_warning(f"[API] Invalid color '{color_hex}' for first-time scores, using default blue")
                    color = discord.Color.from_str('#4169E1')
                action_text = "was the first to score on this chart!"
            elif is_personal_best:
                title = "📈 PERSONAL BEST!"
                # Read color from config (default: Green)
                if self.config:
                    color_hex = self.config.config.get('announcements', {}).get('personal_bests', {}).get('embed_color', '#32CD32')
                else:
                    color_hex = '#32CD32'
                try:
                    color = discord.Color.from_str(color_hex)
                except ValueError:
                    print_warning(f"[API] Invalid color '{color_hex}' for personal bests, using default green")
                    color = discord.Color.from_str('#32CD32')
                action_text = "improved their personal best!"
            else:
                # Fallback (shouldn't happen)
                title = "NEW HIGH SCORE!"
                color = discord.Color.gold()
                action_text = "set a new score!"

            # Check for minimalist mode based on announcement type
            use_minimalist_mode = False
            minimalist_config_path = None

            if self.config:
                if is_record_broken:
                    style = self.config.config.get('announcements', {}).get('record_breaks', {}).get('style', 'full')
                    use_minimalist_mode = (style == 'minimalist')
                    minimalist_config_path = 'announcements.record_breaks.minimalist_fields'
                elif is_first_time:
                    style = self.config.config.get('announcements', {}).get('first_time_scores', {}).get('style', 'full')
                    use_minimalist_mode = (style == 'minimalist')
                    minimalist_config_path = 'announcements.first_time_scores.minimalist_fields'
                elif is_personal_best:
                    style = self.config.config.get('announcements', {}).get('personal_bests', {}).get('style', 'full')
                    use_minimalist_mode = (style == 'minimalist')
                    minimalist_config_path = 'announcements.personal_bests.minimalist_fields'

            # Common data extraction for both modes
            stars_count = score_data.get('stars', 0)
            stars_display = "⭐" * stars_count if stars_count > 0 else "-"

            song_title = score_data.get('song_title', '')
            song_artist = score_data.get('song_artist', '')
            if song_title and not song_title.startswith('['):
                chart_display = song_title
                if song_artist:
                    chart_display = f"{song_title} - {song_artist}"
            else:
                chart_display = f"[{score_data['chart_hash'][:8]}]"

            # MINIMALIST MODE: Simplified announcement with configurable fields
            if use_minimalist_mode and minimalist_config_path:
                # Get minimalist fields configuration
                fields_config = self.config.config.get('announcements', {})
                if is_record_broken:
                    fields_config = fields_config.get('record_breaks', {}).get('minimalist_fields', {})
                elif is_first_time:
                    fields_config = fields_config.get('first_time_scores', {}).get('minimalist_fields', {})
                elif is_personal_best:
                    fields_config = fields_config.get('personal_bests', {}).get('minimalist_fields', {})

                # Build description
                user_mention = f"<@{result['discord_id']}>"
                description = f"{user_mention} {action_text}\n\n"

                # Song title (always in description)
                if fields_config.get('song_title', True):
                    description += f"**Song:** *{chart_display}*\n"

                # Score (always in description)
                if fields_config.get('score', True):
                    description += f"**Score:** *{score_data['score']:,}* points"

                    # Show improvement if applicable
                    if fields_config.get('improvement', False) and result.get('user_previous_score') and (is_personal_best or is_record_broken):
                        diff = score_data['score'] - result['user_previous_score']
                        description += f" (+{diff:,})"

                embed = discord.Embed(
                    title=title,
                    description=description,
                    color=color
                )

                # Configurable inline fields
                if fields_config.get('difficulty_instrument', True):
                    embed.add_field(name="Instrument", value=instrument_name, inline=True)
                    embed.add_field(name="Difficulty", value=difficulty_name, inline=True)

                if fields_config.get('stars', True):
                    embed.add_field(name="Stars", value=stars_display, inline=True)

                # Optional fields based on configuration
                if fields_config.get('charter', False):
                    charter_name = score_data.get('song_charter')
                    if charter_name:
                        embed.add_field(name="Charter", value=charter_name, inline=True)

                if fields_config.get('accuracy', False):
                    accuracy = score_data.get('completion_percent', 0)
                    notes_hit = score_data.get('notes_hit')
                    notes_total = score_data.get('notes_total')
                    if notes_hit is not None and notes_total is not None:
                        accuracy_display = f"{notes_hit}/{notes_total} ({accuracy:.1f}%)"
                    else:
                        accuracy_display = f"{accuracy:.1f}%"
                    embed.add_field(name="Accuracy", value=accuracy_display, inline=True)

                if fields_config.get('play_count', False):
                    play_count = score_data.get('play_count')
                    if play_count is not None:
                        embed.add_field(name="Play Count", value=str(play_count), inline=True)

                # Previous record/best info
                if is_record_broken and fields_config.get('previous_record', False):
                    if result.get('previous_holder'):
                        prev_text = f"{result['previous_holder']}: {result.get('previous_score', 0):,} pts"
                        embed.add_field(name="Previous Record", value=prev_text, inline=False)

                if is_personal_best and fields_config.get('previous_best', False):
                    if result.get('user_previous_score'):
                        prev_text = f"{result['user_previous_score']:,} pts"
                        embed.add_field(name="Previous Best", value=prev_text, inline=True)

                # Server record holder info for personal bests
                if is_personal_best and fields_config.get('server_record_holder', False):
                    # This would need to be fetched from database - placeholder for now
                    pass

                # Enchor.us link
                if fields_config.get('enchor_link', False):
                    enchor_url = generate_enchor_url(
                        score_data.get('song_title'),
                        score_data.get('song_artist'),
                        score_data.get('song_charter')
                    )
                    if enchor_url:
                        embed.add_field(
                            name="Find This Chart",
                            value=f"[Search on enchor.us]({enchor_url})",
                            inline=False
                        )

                # Chart hash
                if fields_config.get('chart_hash', True):
                    chart_hash = score_data['chart_hash']
                    hash_format = fields_config.get('chart_hash_format', 'abbreviated')
                    if hash_format == 'abbreviated':
                        hash_display = f"`{chart_hash[:8]}`"
                    else:
                        hash_display = f"`{chart_hash}`"
                    embed.add_field(name="Chart Hash", value=hash_display, inline=False)

                # Timestamp
                if fields_config.get('timestamp', True):
                    import pytz
                    from datetime import datetime

                    # Get display timezone from config
                    tz_name = self.config.config.get('display', {}).get('timezone', 'UTC')
                    try:
                        display_timezone = pytz.timezone(tz_name)
                    except pytz.exceptions.UnknownTimeZoneError:
                        display_timezone = pytz.UTC

                    now_utc = datetime.utcnow().replace(tzinfo=pytz.UTC)
                    now_display = now_utc.astimezone(display_timezone)
                    timestamp_str = now_display.strftime("%Y-%m-%d %I:%M %p")
                    tz_abbr = now_display.strftime("%Z")
                    embed.add_field(name="Achieved", value=f"{timestamp_str} {tz_abbr}", inline=True)

                await channel.send(embed=embed)
                print_success(f"[API] Minimalist announcement posted to #{channel.name}")
                return  # Early return for minimalist mode

            # FULL MODE: Continue with regular detailed announcement

            # Accuracy/Notes display
            accuracy = score_data.get('completion_percent', 0)
            notes_hit = score_data.get('notes_hit')
            notes_total = score_data.get('notes_total')

            if notes_hit is not None and notes_total is not None:
                accuracy_display = f"{notes_hit}/{notes_total} ({accuracy:.1f}%)"
            else:
                accuracy_display = f"{accuracy:.1f}%"

            # User mention
            user_mention = f"<@{result['discord_id']}>"

            # Build description with mention, song, and score
            description = f"{user_mention} {action_text}\n\n"
            description += f"**Song:** *{chart_display}*\n"
            description += f"**Score:** *{score_data['score']:,}* points"

            # Show improvement for personal bests and record breaks
            if result.get('user_previous_score') and (is_personal_best or is_record_broken):
                diff = score_data['score'] - result['user_previous_score']
                description += f" (+{diff:,})"

            embed = discord.Embed(
                title=title,
                description=description,
                color=color
            )

            # Get OCR-enriched fields (only present for "rich" scores)
            best_streak = score_data.get('best_streak')
            score_type = score_data.get('score_type', 'raw')

            # Row of key info
            embed.add_field(
                name="Instrument",
                value=instrument_name,
                inline=True
            )
            embed.add_field(
                name="Difficulty",
                value=difficulty_name,
                inline=True
            )
            embed.add_field(
                name="Stars",
                value=stars_display,
                inline=True
            )

            # Charter field (if available)
            charter_name = score_data.get('song_charter')
            if charter_name:
                embed.add_field(
                    name="Charter",
                    value=charter_name,
                    inline=True
                )

            # Accuracy field - show notes if we have rich score data
            if notes_hit is not None and notes_total is not None:
                embed.add_field(
                    name="Accuracy",
                    value=f"{notes_hit}/{notes_total} ({accuracy:.1f}%)",
                    inline=True
                )
            else:
                embed.add_field(
                    name="Accuracy",
                    value=f"{accuracy:.1f}%",
                    inline=True
                )

            # Play count field (if available)
            play_count = score_data.get('play_count')
            if play_count is not None:
                embed.add_field(
                    name="Play Count",
                    value=str(play_count),
                    inline=True
                )

            # Only show streak if available (rich score)
            if best_streak is not None:
                embed.add_field(
                    name="Best Streak",
                    value=str(best_streak),
                    inline=True
                )

            # Generate enchor.us link if we have metadata
            chart_hash = score_data['chart_hash']
            enchor_url = generate_enchor_url(
                score_data.get('song_title'),
                score_data.get('song_artist'),
                score_data.get('song_charter')
            )

            # Show enchor.us link if available
            if enchor_url:
                embed.add_field(
                    name="Find This Chart",
                    value=f"[Search on enchor.us]({enchor_url})",
                    inline=False
                )

            # Always show chart hash (unique identifier for our database)
            embed.add_field(
                name="Chart Hash",
                value=f"`{chart_hash}`",
                inline=False
            )

            # Timezone handling for timestamps
            import pytz
            from datetime import datetime

            # Get display timezone from config (default: UTC)
            if self.config:
                tz_name = self.config.config.get('display', {}).get('timezone', 'UTC')
                try:
                    display_timezone = pytz.timezone(tz_name)
                except pytz.exceptions.UnknownTimeZoneError:
                    print_warning(f"Unknown timezone '{tz_name}', using UTC")
                    display_timezone = pytz.UTC
            else:
                display_timezone = pytz.UTC

            # Add timestamp field showing when THIS score was achieved
            now_utc = datetime.utcnow().replace(tzinfo=pytz.UTC)
            now_display = now_utc.astimezone(display_timezone)
            timestamp_str = now_display.strftime("%Y-%m-%d %I:%M %p")
            tz_abbr = now_display.strftime("%Z")

            embed.add_field(
                name="Achieved",
                value=f"{timestamp_str} {tz_abbr}",
                inline=True
            )

            # Previous record holder - always show if there was one
            if result.get('previous_holder') and result.get('previous_holder_discord_id'):
                prev_discord_id = result['previous_holder_discord_id']
                prev_mention = f"<@{prev_discord_id}>"

                # Calculate how long the record was held
                footer_text = f"Previous record: {result['previous_holder']} ({result.get('previous_score', 0):,} pts)"

                if result.get('previous_record_timestamp'):
                    try:
                        prev_time = datetime.fromisoformat(result['previous_record_timestamp'])
                        # Assume prev_time is in UTC (from database)
                        if prev_time.tzinfo is None:
                            prev_time = prev_time.replace(tzinfo=pytz.UTC)

                        time_held = now_utc - prev_time

                        # Format as days/hours/minutes
                        total_seconds = time_held.total_seconds()
                        if total_seconds >= 86400:  # 1 day or more
                            days = int(total_seconds // 86400)
                            footer_text += f" • Held for {days} day{'s' if days != 1 else ''}"
                        elif total_seconds >= 3600:  # 1 hour or more
                            hours = int(total_seconds // 3600)
                            footer_text += f" • Held for {hours} hour{'s' if hours != 1 else ''}"
                        else:  # Less than 1 hour
                            minutes = int(total_seconds // 60)
                            footer_text += f" • Held for {minutes} minute{'s' if minutes != 1 else ''}"

                        # Add previous record timestamp (converted to display timezone)
                        prev_time_display = prev_time.astimezone(display_timezone)
                        prev_timestamp_str = prev_time_display.strftime("%Y-%m-%d %I:%M %p")
                        footer_text += f" • Set on {prev_timestamp_str} {tz_abbr}"
                    except (ValueError, TypeError):
                        pass  # If timestamp parsing fails, just show the basic info

                embed.set_footer(text=footer_text)

                # Only ping the previous holder if it's a different person
                if str(prev_discord_id) != str(result['discord_id']):
                    await channel.send(f"{prev_mention} - your record was beaten!", embed=embed)
                else:
                    await channel.send(embed=embed)
            else:
                await channel.send(embed=embed)

            print_success(f"[API] High score announcement posted to #{channel.name}")

        except Exception as e:
            print_error(f"[API] Error posting announcement: {e}")
            log_exception(logger, "Error posting announcement", e)
            import traceback
            traceback.print_exc()

    async def request_pairing(self, request):
        """
        Request a pairing code for a new client

        Expected JSON body:
        {
            "client_id": "unique-client-identifier"
        }

        Returns:
        {
            "success": true,
            "pairing_code": "ABC123",
            "expires_in": 300
        }
        """
        try:
            data = await request.json()

            if 'client_id' not in data:
                return web.json_response({
                    'success': False,
                    'error': 'client_id is required'
                }, status=400)

            client_id = data['client_id']

            # Generate pairing code using database
            pairing_code = self.bot.db.create_pairing_code(client_id, expires_minutes=5)

            return web.json_response({
                'success': True,
                'pairing_code': pairing_code,
                'expires_in': 300,
                'instructions': f'Run this command in Discord: /pair {pairing_code}'
            })

        except Exception as e:
            print_error(f"[API] Error requesting pairing: {e}")
            log_exception(logger, "Error requesting pairing", e)
            return web.json_response({
                'success': False,
                'error': str(e)
            }, status=500)

    async def check_pairing_status(self, request):
        """
        Check if a client has been paired

        Returns:
        {
            "success": true,
            "paired": true/false,
            "auth_token": "..." (if paired)
        }
        """
        client_id = request.match_info['client_id']

        # Check database for pairing status
        auth_token = self.bot.db.check_pairing_status(client_id)

        if auth_token:
            return web.json_response({
                'success': True,
                'paired': True,
                'auth_token': auth_token
            })
        else:
            return web.json_response({
                'success': True,
                'paired': False,
                'auth_token': None
            })

    async def authorize_debug(self, request):
        """
        Authorize debug mode access with password

        Expected payload:
        {
            "password": "..."
        }

        Returns:
        {
            "success": true/false,
            "authorized": true/false
        }
        """
        try:
            data = await request.json()
            password = data.get('password', '')

            # Check against server's debug password
            if password == Config.DEBUG_PASSWORD:
                return web.json_response({
                    'success': True,
                    'authorized': True
                })
            else:
                return web.json_response({
                    'success': True,
                    'authorized': False
                }, status=401)

        except Exception as e:
            print_error(f"[API] Error authorizing debug: {e}")
            log_exception(logger, "Error authorizing debug", e)
            return web.json_response({
                'success': False,
                'error': str(e)
            }, status=500)

    async def get_unresolved_hashes(self, request):
        """
        Get list of chart hashes that don't have metadata

        Requires authentication via auth_token header

        Returns:
        {
            "success": true,
            "hashes": ["hash1", "hash2", ...]
        }
        """
        try:
            # Check authentication
            auth_token = request.headers.get('Authorization', '').replace('Bearer ', '')
            if not auth_token:
                return web.json_response({
                    'success': False,
                    'error': 'Missing auth token'
                }, status=401)

            # Verify user exists
            user = self.bot.db.get_user_by_auth_token(auth_token)
            if not user:
                return web.json_response({
                    'success': False,
                    'error': 'Invalid auth token'
                }, status=401)

            # Get unresolved hashes for this user only
            hashes = self.bot.db.get_unresolved_hashes(user['id'])

            return web.json_response({
                'success': True,
                'count': len(hashes),
                'hashes': hashes
            })

        except Exception as e:
            print_error(f"[API] Error getting unresolved hashes: {e}")
            log_exception(logger, "Error getting unresolved hashes", e)
            return web.json_response({
                'success': False,
                'error': str(e)
            }, status=500)

    async def resolve_hashes(self, request):
        """
        Batch update song metadata for chart hashes

        Requires authentication via auth_token header

        Expected payload:
        {
            "metadata": [
                {
                    "chart_hash": "abc123...",
                    "title": "Song Title",
                    "artist": "Artist Name",
                    "charter": "Charter Name"
                },
                ...
            ]
        }

        Returns:
        {
            "success": true,
            "updated_count": 42
        }
        """
        try:
            # Check authentication
            auth_token = request.headers.get('Authorization', '').replace('Bearer ', '')
            if not auth_token:
                return web.json_response({
                    'success': False,
                    'error': 'Missing auth token'
                }, status=401)

            # Verify user exists
            user = self.bot.db.get_user_by_auth_token(auth_token)
            if not user:
                return web.json_response({
                    'success': False,
                    'error': 'Invalid auth token'
                }, status=401)

            # Get metadata from request
            data = await request.json()
            metadata_list = data.get('metadata', [])

            if not metadata_list:
                return web.json_response({
                    'success': False,
                    'error': 'No metadata provided'
                }, status=400)

            # Update database
            updated_count = self.bot.db.batch_update_song_metadata(metadata_list)

            print_success(f"[API] Resolved {updated_count} hashes (by {user['discord_username']})")

            return web.json_response({
                'success': True,
                'updated_count': updated_count
            })

        except Exception as e:
            print_error(f"[API] Error resolving hashes: {e}")
            log_exception(logger, "Error resolving hashes", e)
            return web.json_response({
                'success': False,
                'error': str(e)
            }, status=500)

    async def start(self):
        """Start the API server"""
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()

        site = web.TCPSite(
            self.runner,
            Config.API_HOST,
            Config.API_PORT
        )

        await site.start()

        print(f"\n[API] HTTP API started on http://{Config.API_HOST}:{Config.API_PORT}")
        print_info(f"[API] Try: http://{Config.API_HOST}:{Config.API_PORT}/health\n")

    async def stop(self):
        """Stop the API server"""
        if self.runner:
            await self.runner.cleanup()
            print_info("[API] HTTP API stopped")

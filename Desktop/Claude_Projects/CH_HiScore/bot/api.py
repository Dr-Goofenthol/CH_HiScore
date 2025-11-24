"""
HTTP API for receiving scores from local clients

This API runs alongside the Discord bot and accepts score submissions.
"""

from aiohttp import web
import asyncio
import json
from datetime import datetime
from .config import Config


class ScoreAPI:
    """HTTP API for score submission"""

    def __init__(self, bot):
        """
        Initialize the API

        Args:
            bot: The Discord bot instance
        """
        self.bot = bot
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
            "chart_md5": "ecd1c69af09ebeec96a4ad24754f3eed",
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
            required = ['auth_token', 'chart_md5', 'instrument_id', 'difficulty_id', 'score']
            missing = [field for field in required if field not in data]
            if missing:
                return web.json_response({
                    'success': False,
                    'error': f'Missing required fields: {", ".join(missing)}'
                }, status=400)

            # Submit score to database
            result = self.bot.db.submit_score(
                auth_token=data['auth_token'],
                chart_md5=data['chart_md5'],
                instrument_id=data['instrument_id'],
                difficulty_id=data['difficulty_id'],
                score=data['score'],
                completion_percent=data.get('completion_percent', 0),
                stars=data.get('stars', 0),
                song_title=data.get('song_title', ''),
                song_artist=data.get('song_artist', '')
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
            song_title = data.get('song_title', f"[{data['chart_md5'][:8]}]")
            song_artist = data.get('song_artist', '')
            score_type = data.get('score_type', 'raw')  # "raw" or "rich"
            notes_hit = data.get('notes_hit')
            notes_total = data.get('notes_total')
            best_streak = data.get('best_streak')
            ocr_artist = data.get('ocr_artist')

            # If we got an OCR artist and the song doesn't have one, update the DB
            if ocr_artist and not song_artist:
                self.bot.db.update_song_artist(data['chart_md5'], ocr_artist)
                song_artist = ocr_artist

            song_display = song_title
            if song_artist:
                song_display = f"{song_title} - {song_artist}"

            print(f"\n[API] Score received from {result['username']} [{score_type.upper()}]:")
            print(f"  Song: {song_display}")
            print(f"  MD5: {data['chart_md5']}")
            print(f"  Score: {data['score']:,} | {diff_name} {inst_name}")
            if notes_hit is not None and notes_total is not None:
                print(f"  Notes: {notes_hit}/{notes_total} ({data.get('completion_percent', 0):.1f}%)")
            else:
                print(f"  Accuracy: {data.get('completion_percent', 0):.1f}%")
            if best_streak is not None:
                print(f"  Best Streak: {best_streak}")
            print(f"  Stars: {data.get('stars', 0)}")
            print(f"  Result: {'RECORD BROKEN!' if result['is_record_broken'] else 'High Score' if result['is_high_score'] else 'Not a record'}")

            # Only post announcement when an EXISTING record is broken
            # (not for first-time scores on a chart)
            if result['is_record_broken']:
                await self.announce_high_score(data, result)

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
            print(f"[API] Error processing score: {e}")
            import traceback
            traceback.print_exc()
            return web.json_response({
                'success': False,
                'error': str(e)
            }, status=500)

    async def announce_high_score(self, score_data: dict, result: dict):
        """Post high score announcement to Discord"""
        try:
            channel_id = Config.DISCORD_CHANNEL_ID
            if not channel_id:
                print("[API] No announcement channel configured")
                return

            channel = self.bot.get_channel(int(channel_id))
            if not channel:
                print(f"[API] Could not find channel {channel_id}")
                return

            # Get instrument and difficulty names
            instruments = {0: "Lead Guitar", 1: "Bass", 2: "Rhythm", 3: "Keys", 4: "Drums"}
            difficulties = {0: "Easy", 1: "Medium", 2: "Hard", 3: "Expert"}

            instrument_name = instruments.get(score_data['instrument_id'], "Unknown")
            difficulty_name = difficulties.get(score_data['difficulty_id'], "Unknown")

            import discord

            # Stars display with emoji
            stars_count = score_data.get('stars', 0)
            stars_display = "⭐" * stars_count if stars_count > 0 else "-"

            # Chart display - use song title if available
            song_title = score_data.get('song_title', '')
            song_artist = score_data.get('song_artist', '')
            if song_title and not song_title.startswith('['):
                chart_display = song_title
                if song_artist:
                    chart_display = f"{song_title} - {song_artist}"
            else:
                chart_display = f"[{score_data['chart_md5'][:8]}]"

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
            description = f"{user_mention} set a new record!\n\n"
            description += f"**Song:** *{chart_display}*\n"
            description += f"**Score:** *{score_data['score']:,}* points"

            if result.get('previous_score'):
                diff = score_data['score'] - result['previous_score']
                description += f" (+{diff:,})"

            embed = discord.Embed(
                title="NEW HIGH SCORE!",
                description=description,
                color=discord.Color.gold()
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

            # Only show notes/accuracy if we have notes data (rich score)
            if notes_hit is not None and notes_total is not None:
                embed.add_field(
                    name="Notes",
                    value=f"{notes_hit}/{notes_total} ({accuracy:.1f}%)",
                    inline=True
                )
            else:
                embed.add_field(
                    name="Accuracy",
                    value=f"{accuracy:.1f}%",
                    inline=True
                )

            # Only show streak if available (rich score)
            if best_streak is not None:
                embed.add_field(
                    name="Best Streak",
                    value=str(best_streak),
                    inline=True
                )

            # Add full MD5 hash for enchor.us lookup (copy-friendly format)
            chart_md5 = score_data['chart_md5']
            embed.add_field(
                name="Chart MD5 (for enchor.us lookup)",
                value=f"`{chart_md5}`",
                inline=False
            )

            # Previous record holder - always show if there was one
            if result.get('previous_holder') and result.get('previous_holder_discord_id'):
                prev_discord_id = result['previous_holder_discord_id']
                prev_mention = f"<@{prev_discord_id}>"
                embed.set_footer(text=f"Previous record: {result['previous_holder']} ({result.get('previous_score', 0):,} pts)")

                # Only ping the previous holder if it's a different person
                if str(prev_discord_id) != str(result['discord_id']):
                    await channel.send(f"{prev_mention} - your record was beaten!", embed=embed)
                else:
                    await channel.send(embed=embed)
            else:
                await channel.send(embed=embed)

            print(f"[API] High score announcement posted to #{channel.name}")

        except Exception as e:
            print(f"[API] Error posting announcement: {e}")
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
            print(f"[API] Error requesting pairing: {e}")
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
        print(f"[API] Try: http://{Config.API_HOST}:{Config.API_PORT}/health\n")

    async def stop(self):
        """Stop the API server"""
        if self.runner:
            await self.runner.cleanup()
            print("[API] HTTP API stopped")

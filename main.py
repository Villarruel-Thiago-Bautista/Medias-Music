import discord
from discord.ext import commands, tasks
import yt_dlp as youtube_dl
import asyncio
from functools import lru_cache
import time
from collections import OrderedDict
import random
import os
import json
from dotenv import load_dotenv

load_dotenv()


# Ruta al archivo de cookies secreto en Render
cookies_path = "/run/secrets/cookies.txt"


# Fallback para desarrollo local
if not os.path.exists(cookies_path):
    cookies_path = os.path.join(os.getcwd(), "cookies.txt")  # tu archivo local

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
bot = commands.Bot(command_prefix='!', intents=intents)

ytdl_options = {
    'format': 'bestaudio/best',
    'noplaylist': False,
    'quiet': True,
    'no_warnings': True,
    'nocheckcertificate': True,
    'geo_bypass': True,
    'cachedir': False,
    'default_search': 'ytsearch',
    'source_address': '0.0.0.0',
    'extract_flat': 'in_playlist',
    'ignoreerrors': True,
    'age_limit': None,
    'socket_timeout': 10,
    'cookiefile': cookies_path,  # aquí usamos la ruta correcta
}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -bufsize 512k'
}

ytdl = youtube_dl.YoutubeDL(ytdl_options)

queues = {}
now_playing = {}
preloaded_tracks = {}  # guild_id -> info de siguiente canción pre-cargada
search_cache = OrderedDict()
CACHE_EXPIRY = 3600
MAX_CACHE_SIZE = 100  # Máximo 100 búsquedas en caché
last_activity = {}  # guild_id -> timestamp de última actividad
INACTIVITY_TIMEOUT = 300  # 5 minutos de inactividad

KAOMOJIS = {
    'happy': ['(◕‿◕✿)', '(｡♥‿♥｡)', '(◠‿◠✿)', '♡(ᐢ ᴗ ᐢ)♡'],
    'music': ['♪(๑ᴖ◡ᴖ๑)♪', '♬♪♫ ヾ(´︶`♡)ﾉ ♬♪♫', '(ﾉ◕ヮ◕)ﾉ*:･ﾟ✧'],
    'loading': ['(｡•̀ᴗ-)✧', '(◕ᴗ◕✿)', '(｡♥‿♥｡)'],
    'error': ['(｡•́︿•̀｡)', '(◞‸◟；)', '(｡•́ - •̀｡)'],
    'success': ['(ﾉ◕ヮ◕)ﾉ*:･ﾟ✧', '✧*｡٩(ˊᗜˋ*)و✧*｡', '(ﾉ´ヮ`)ﾉ*: ･ﾟ']
}

COLORS = {
    'primary': 0xFFB7C5,      # Rosa pastel Sakura
    'success': 0xFFD4E0,      # Rosa claro éxito
    'warning': 0xFFABC1,      # Rosa medio advertencia
    'error': 0xFF9EAF,        # Rosa coral error
    'playing': 0xFF8FA3,      # Rosa vibrante reproducción
    'queue': 0xFFC9D6,        # Rosa suave cola
    'info': 0xFFE0E9,         # Rosa muy claro info
}

SAKURA_GIFS = {
    'playing': [
        'https://media.tenor.com/8v3arEeFiroAAAAM/sakura-naruto.gif',
        'https://media.tenor.com/_4978jxLrnQAAAAM/sakura-sakura-haruno.gif',
        'https://media.tenor.com/v6FFqk_HSecAAAAM/sakura-sakura-haruno.gif',
        'https://media.tenor.com/kr4rRKz81P4AAAAM/sakura-sakura-haruno.gif',
        'https://media.tenor.com/hXfgXB3JxS8AAAAm/sakura.webp',
    ],
    'happy': [
        'https://media.tenor.com/2gwoU1h3G6IAAAAM/anime-boruto.gif',
        'https://media.tenor.com/8v3arEeFiroAAAAM/sakura-naruto.gif',
        'https://media.tenor.com/_4978jxLrnQAAAAM/sakura-sakura-haruno.gif',
        'https://media.tenor.com/YUYDXBaAthcAAAAM/naruto-shippuden-sakura-haruno.gif',
        'https://media.tenor.com/kr4rRKz81P4AAAAM/sakura-sakura-haruno.gif',
    ],
    'loading': [
        'https://media.tenor.com/I56S14_iwt0AAAAM/sakura-anime.gif',
        'https://media.tenor.com/tUUyN9N72aUAAAAM/sakura-ninjutsu-medico.gif',
    ],
    'error': [
        'https://media.tenor.com/x9lOhN4kbgcAAAAM/naruto-funny.gif',
        'https://media.tenor.com/ELVlq5sW43YAAAAM/naruto-shippuden-sakura-haruno.gif',
        'https://media.tenor.com/rF2mndxZKiIAAAAM/naruto-naruto-shippuden.gif',
    ],
    'success': [
        'https://media.tenor.com/5UmCSija7J4AAAAM/sakura.gif',
        'https://media.tenor.com/hQkgwEF4oOAAAAAM/sakura-sakura-haruno.gif',
    ],
    'queue': [
        'https://media.tenor.com/v6FFqk_HSecAAAAM/sakura-sakura-haruno.gif',
        'https://media.tenor.com/v6FFqk_HSecAAAAM/sakura-sakura-haruno.gif',
        'https://media.tenor.com/QrjrRGV--f4AAAAM/sasuke-uchiha-sasuke.gif',
    ],
    'pause': [
        'https://media.tenor.com/2-FxZWXpsmcAAAAM/sakura-uchiha.gif',
        'https://media.tenor.com/5UmCSija7J4AAAAM/sakura.gif',
    ],
    'goodbye': [
        'https://media.tenor.com/Q9vIbSaQ93UAAAAM/sakura-haruno-naruto.gif',
        'https://media.tenor.com/x9lOhN4kbgcAAAAM/naruto-funny.gif',
        'https://media.tenor.com/aRKZw-qF-1gAAAAM/naruto-naruto-shippuden.gif',
    ]
}

def get_sakura_gif(category='happy'):
    """Obtiene un GIF aleatorio de Sakura según la categoría"""
    if category in SAKURA_GIFS:
        return random.choice(SAKURA_GIFS[category])
    return random.choice(SAKURA_GIFS['happy'])


def clean_cache():
    """Limpia entradas antiguas del caché"""
    current_time = time.time()
    to_remove = []
    
    for key, (data, timestamp) in search_cache.items():
        if current_time - timestamp > CACHE_EXPIRY:
            to_remove.append(key)
    
    for key in to_remove:
        search_cache.pop(key, None)
    
    # Si aún excede el límite, eliminar las más antiguas
    while len(search_cache) > MAX_CACHE_SIZE:
        search_cache.popitem(last=False)


async def extract_info_async(query, extract_flat=False):
    """Extrae info de forma asíncrona con caché optimizado"""
    cache_key = f"{query}_{extract_flat}"
    
    if cache_key in search_cache:
        cached_data, timestamp = search_cache[cache_key]
        if time.time() - timestamp < CACHE_EXPIRY:
            # Mover al final (más reciente)
            search_cache.move_to_end(cache_key)
            return cached_data
    
    loop = asyncio.get_event_loop()
    opts = ytdl_options.copy()
    if extract_flat:
        opts['extract_flat'] = True
    
    temp_ytdl = youtube_dl.YoutubeDL(opts)
    
    try:
        data = await loop.run_in_executor(
            None, 
            lambda: temp_ytdl.extract_info(query, download=False)
        )
        search_cache[cache_key] = (data, time.time())
        clean_cache()  # Limpiar caché después de agregar
        return data
    except Exception as e:
        print(f"Error extrayendo info: {e}")
        return None


async def preload_next_track(ctx, guild_id):
    """Pre-carga la siguiente canción en la cola para reproducción instantánea"""
    if guild_id in queues and queues[guild_id]:
        next_track = queues[guild_id][0]
        try:
            info = await extract_info_async(next_track['url'])
            if info and 'entries' in info:
                info = info['entries'][0]
            if info:
                preloaded_tracks[guild_id] = info
        except Exception as e:
            print(f"Error pre-cargando: {e}")


def update_activity(guild_id):
    """Actualiza el timestamp de última actividad"""
    last_activity[guild_id] = time.time()


async def play_next(ctx):
    """Reproduce la siguiente canción en la cola"""
    guild_id = ctx.guild.id
    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)

    if not voice_client:
        return

    if guild_id in queues and queues[guild_id]:
        track = queues[guild_id].pop(0)
        await start_playback(ctx, track)
    else:
        goodbye_embed = discord.Embed(
            title=f"🌸 ¡Hasta pronto! {random.choice(KAOMOJIS['happy'])}",
            description="La cola ha terminado. ¡Gracias por escuchar música conmigo!",
            color=COLORS['info']
        )
        goodbye_embed.set_image(url=get_sakura_gif('goodbye'))
        goodbye_embed.set_footer(text="Desconectando con amor ♡")
        await ctx.send(embed=goodbye_embed)
        
        now_playing.pop(guild_id, None)
        preloaded_tracks.pop(guild_id, None)
        last_activity.pop(guild_id, None)
        
        await asyncio.sleep(1)
        if voice_client.is_connected():
            await voice_client.disconnect()


async def start_playback(ctx, track_info):
    """Inicia reproducción de una canción con pre-carga optimizada"""
    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    guild_id = ctx.guild.id
    
    update_activity(guild_id)
    
    try:
        if guild_id in preloaded_tracks:
            info = preloaded_tracks.pop(guild_id)
        else:
            info = await extract_info_async(track_info['url'])
        
        if not info:
            error_embed = discord.Embed(
                title=f"✨ Oops... {random.choice(KAOMOJIS['error'])}",
                description=f"No pude cargar esta canción:\n**{track_info['title']}**",
                color=COLORS['error']
            )
            error_embed.set_image(url=get_sakura_gif('error'))
            error_embed.set_footer(text="Intentando con la siguiente... ♡")
            await ctx.send(embed=error_embed)
            await play_next(ctx)
            return
        
        if 'entries' in info:
            info = info['entries'][0]

        audio_url = info['url']
        
        source = discord.FFmpegPCMAudio(audio_url, **ffmpeg_options)
        source = discord.PCMVolumeTransformer(source, volume=0.5)

        def after_playing(err):
            if err:
                print(f"Error al reproducir: {err}")
            asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)

        voice_client.play(source, after=after_playing)
        
        now_playing[guild_id] = track_info
        
        asyncio.create_task(preload_next_track(ctx, guild_id))

        mins, secs = divmod(track_info.get('duration', 0), 60)
        
        embed = discord.Embed(
            title=f"🌸 ¡Reproduciendo con amor! {random.choice(KAOMOJIS['music'])}",
            description=f"### [{track_info['title']}]({track_info['url']})",
            color=COLORS['playing']
        )
        
        progress_bar = "✧･ﾟ: *✧･ﾟ:*━━━━━━━━━━*:･ﾟ✧*:･ﾟ✧"
        embed.add_field(
            name="⏱️ Duración",
            value=f"`00:00 {progress_bar} {mins:02}:{secs:02}`",
            inline=False
        )
        
        embed.add_field(
            name="💗 Solicitado por",
            value=f"{track_info['requester'].mention}",
            inline=True
        )
        
        embed.add_field(
            name="🎀 Canciones en Cola",
            value=f"`{len(queues.get(guild_id, []))} canciones`",
            inline=True
        )
        
        embed.set_image(url=get_sakura_gif('playing'))
        
        embed.set_footer(
            text=f"Reproduciendo con todo mi corazón ♡ • {ctx.guild.name}",
            icon_url=ctx.guild.icon.url if ctx.guild.icon else None
        )
        embed.timestamp = discord.utils.utcnow()
        
        msg = await ctx.send(embed=embed)
        
        reactions = ['🌸', '💗', '✨']
        for emoji in reactions:
            try:
                await msg.add_reaction(emoji)
            except:
                pass
        
    except Exception as e:
        error_embed = discord.Embed(
            title=f"✨ Error inesperado {random.choice(KAOMOJIS['error'])}",
            description=f"`{str(e)}`",
            color=COLORS['error']
        )
        error_embed.set_image(url=get_sakura_gif('error'))
        error_embed.set_footer(text="Continuando con la siguiente pista... ♡")
        await ctx.send(embed=error_embed)
        await play_next(ctx)


@tasks.loop(minutes=1)
async def check_inactivity():
    """Verifica y desconecta bots inactivos"""
    current_time = time.time()
    to_disconnect = []
    
    for guild_id, last_time in list(last_activity.items()):
        if current_time - last_time > INACTIVITY_TIMEOUT:
            to_disconnect.append(guild_id)
    
    for guild_id in to_disconnect:
        guild = bot.get_guild(guild_id)
        if guild:
            voice_client = discord.utils.get(bot.voice_clients, guild=guild)
            if voice_client and voice_client.is_connected():
                # Buscar un canal de texto para enviar mensaje
                channel = None
                for text_channel in guild.text_channels:
                    if text_channel.permissions_for(guild.me).send_messages:
                        channel = text_channel
                        break
                
                if channel:
                    timeout_embed = discord.Embed(
                        title=f"💤 Desconectando por inactividad {random.choice(KAOMOJIS['happy'])}",
                        description="He estado inactiva por 5 minutos. ¡Nos vemos pronto!",
                        color=COLORS['info']
                    )
                    timeout_embed.set_image(url=get_sakura_gif('goodbye'))
                    timeout_embed.set_footer(text="Usa !play para volver a escuchar música ♡")
                    await channel.send(embed=timeout_embed)
                
                await voice_client.disconnect()
                queues.pop(guild_id, None)
                now_playing.pop(guild_id, None)
                preloaded_tracks.pop(guild_id, None)
                last_activity.pop(guild_id, None)


@bot.command()
async def play(ctx, *, query):
    """Reproduce canción o playlist de YouTube"""
    update_activity(ctx.guild.id)
    
    if not ctx.author.voice:
        error_embed = discord.Embed(
            title=f"🎀 ¡Ups! {random.choice(KAOMOJIS['error'])}",
            description="Necesitas estar en un canal de voz para que pueda reproducir música para ti.",
            color=COLORS['error']
        )
        error_embed.set_image(url=get_sakura_gif('error'))
        error_embed.set_footer(text="Únete a un canal de voz e intenta de nuevo ♡")
        await ctx.send(embed=error_embed)
        return

    channel = ctx.author.voice.channel
    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    
    if not voice_client:
        voice_client = await channel.connect()
    elif voice_client.channel != channel:
        await voice_client.move_to(channel)

    guild_id = ctx.guild.id
    queues.setdefault(guild_id, [])

    loading_embed = discord.Embed(
        title=f"✨ Buscando tu canción {random.choice(KAOMOJIS['loading'])}",
        description="Estoy preparando todo con mucho cariño...",
        color=COLORS['primary']
    )
    loading_embed.set_image(url=get_sakura_gif('loading'))
    loading_embed.set_footer(text="Esto solo tomará un momento ♡")
    loading_msg = await ctx.send(embed=loading_embed)

    try:
        is_url = query.startswith(('http://', 'https://', 'www.', 'youtu.be', 'youtube.com'))
        
        if is_url:
            info = await extract_info_async(query, extract_flat=True)
            
            if not info:
                error_embed = discord.Embed(
                    title=f"✨ No encontré nada {random.choice(KAOMOJIS['error'])}",
                    description="No pude cargar ese enlace. ¿Podrías verificarlo?",
                    color=COLORS['error']
                )
                error_embed.set_image(url=get_sakura_gif('error'))
                await loading_msg.edit(embed=error_embed)
                return
            
            if 'entries' in info:
                added = 0
                for entry in info['entries']:
                    if entry:
                        track = {
                            'title': entry.get('title', 'Desconocido'),
                            'url': entry.get('url') or entry.get('webpage_url'),
                            'duration': entry.get('duration', 0),
                            'thumbnail': entry.get('thumbnail'),
                            'requester': ctx.author
                        }
                        queues[guild_id].append(track)
                        added += 1
                
                playlist_embed = discord.Embed(
                    title=f"🌺 ¡Playlist agregada! {random.choice(KAOMOJIS['success'])}",
                    description=f"He agregado **{added}** canciones hermosas a la cola.",
                    color=COLORS['success']
                )
                playlist_embed.add_field(
                    name="💫 Total en Cola",
                    value=f"`{len(queues[guild_id])} canciones esperando`",
                    inline=True
                )
                playlist_embed.add_field(
                    name="💗 Solicitado por",
                    value=ctx.author.mention,
                    inline=True
                )
                playlist_embed.set_image(url=get_sakura_gif('success'))
                playlist_embed.set_footer(text=f"¡Disfruta la música! ♡ • {ctx.guild.name}")
                playlist_embed.timestamp = discord.utils.utcnow()
                
                msg = await loading_msg.edit(embed=playlist_embed)
                await msg.add_reaction('🌺')
                
                if not voice_client.is_playing():
                    await play_next(ctx)
            else:
                track = {
                    'title': info.get('title', 'Desconocido'),
                    'url': info.get('webpage_url') or query,
                    'duration': info.get('duration', 0),
                    'thumbnail': info.get('thumbnail'),
                    'requester': ctx.author
                }
                
                if voice_client.is_playing():
                    mins, secs = divmod(track.get('duration', 0), 60)
                    queue_embed = discord.Embed(
                        title=f"💗 ¡Agregada a la cola! {random.choice(KAOMOJIS['success'])}",
                        description=f"### [{track['title']}]({track['url']})",
                        color=COLORS['success']
                    )
                    queue_embed.add_field(
                        name="⏱️ Duración",
                        value=f"`{mins:02}:{secs:02}`",
                        inline=True
                    )
                    queue_embed.add_field(
                        name="🎀 Posición",
                        value=f"`#{len(queues[guild_id]) + 1} en la cola`",
                        inline=True
                    )
                    queue_embed.add_field(
                        name="💗 Solicitado por",
                        value=ctx.author.mention,
                        inline=True
                    )
                    queue_embed.set_image(url=get_sakura_gif('happy'))
                    queue_embed.set_footer(text=f"Tu canción sonará pronto ♡ • {ctx.guild.name}")
                    queue_embed.timestamp = discord.utils.utcnow()
                    
                    queues[guild_id].append(track)
                    msg = await loading_msg.edit(embed=queue_embed)
                    await msg.add_reaction('💗')
                else:
                    await loading_msg.delete()
                    await start_playback(ctx, track)
        else:
            search_query = f"ytsearch1:{query}"
            info = await extract_info_async(search_query)
            
            if not info:
                error_embed = discord.Embed(
                    title=f"✨ Error en la búsqueda {random.choice(KAOMOJIS['error'])}",
                    description="No pude realizar la búsqueda. ¿Podrías intentar de nuevo?",
                    color=COLORS['error']
                )
                error_embed.set_image(url=get_sakura_gif('error'))
                await loading_msg.edit(embed=error_embed)
                return
            
            if 'entries' in info and info['entries']:
                first = info['entries'][0]
            else:
                first = info
            
            if not first:
                no_results_embed = discord.Embed(
                    title=f"✨ No encontré nada {random.choice(KAOMOJIS['error'])}",
                    description=f"No encontré resultados para: **{query}**",
                    color=COLORS['warning']
                )
                no_results_embed.set_image(url=get_sakura_gif('error'))
                no_results_embed.set_footer(text="Intenta con otros términos ♡")
                await loading_msg.edit(embed=no_results_embed)
                return
            
            track = {
                'title': first.get('title', 'Desconocido'),
                'url': first.get('webpage_url') or first.get('url'),
                'duration': first.get('duration', 0),
                'thumbnail': first.get('thumbnail'),
                'requester': ctx.author
            }
            
            if voice_client.is_playing():
                mins, secs = divmod(track.get('duration', 0), 60)
                queue_embed = discord.Embed(
                    title=f"💗 ¡Agregada a la cola! {random.choice(KAOMOJIS['success'])}",
                    description=f"### [{track['title']}]({track['url']})",
                    color=COLORS['success']
                )
                queue_embed.add_field(
                    name="⏱️ Duración",
                    value=f"`{mins:02}:{secs:02}`",
                    inline=True
                )
                queue_embed.add_field(
                    name="🎀 Posición",
                    value=f"`#{len(queues[guild_id]) + 1} en la cola`",
                    inline=True
                )
                queue_embed.add_field(
                    name="💗 Solicitado por",
                    value=ctx.author.mention,
                    inline=True
                )
                queue_embed.set_image(url=get_sakura_gif('happy'))
                queue_embed.set_footer(text=f"Tu canción sonará pronto ♡ • {ctx.guild.name}")
                queue_embed.timestamp = discord.utils.utcnow()
                
                queues[guild_id].append(track)
                msg = await loading_msg.edit(embed=queue_embed)
                await msg.add_reaction('💗')
            else:
                await loading_msg.delete()
                await start_playback(ctx, track)
                
    except Exception as e:
        error_embed = discord.Embed(
            title=f"✨ Algo salió mal {random.choice(KAOMOJIS['error'])}",
            description=f"`{str(e)}`",
            color=COLORS['error']
        )
        error_embed.set_image(url=get_sakura_gif('error'))
        error_embed.set_footer(text="Por favor intenta de nuevo ♡")
        await loading_msg.edit(embed=error_embed)
        print(f"Error en play: {e}")


@bot.command()
async def skip(ctx):
    """Salta a la siguiente canción"""
    update_activity(ctx.guild.id)
    
    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice_client and voice_client.is_playing():
        guild_id = ctx.guild.id
        current = now_playing.get(guild_id)
        
        skip_embed = discord.Embed(
            title=f"⏭️ ¡Saltando! {random.choice(KAOMOJIS['music'])}",
            description=f"Pasando a la siguiente canción...",
            color=COLORS['warning']
        )
        
        if current:
            skip_embed.add_field(
                name="🎵 Canción Omitida",
                value=f"[{current['title']}]({current['url']})",
                inline=False
            )
        
        next_count = len(queues.get(guild_id, []))
        skip_embed.add_field(
            name="🎀 Siguiente",
            value=f"`{next_count} canciones esperando`" if next_count > 0 else "`Cola vacía`",
            inline=True
        )
        skip_embed.set_image(url=get_sakura_gif('playing'))
        skip_embed.set_footer(text=f"Solicitado por {ctx.author.display_name} ♡")
        
        msg = await ctx.send(embed=skip_embed)
        await msg.add_reaction('⏭️')
        voice_client.stop()
    else:
        error_embed = discord.Embed(
            title=f"✨ No hay nada sonando {random.choice(KAOMOJIS['error'])}",
            description="No hay ninguna canción reproduciéndose en este momento.",
            color=COLORS['error']
        )
        error_embed.set_image(url=get_sakura_gif('error'))
        await ctx.send(embed=error_embed)


@bot.command()
async def queue(ctx):
    """Muestra la cola de reproducción"""
    guild_id = ctx.guild.id
    
    if guild_id not in queues or not queues[guild_id]:
        empty_embed = discord.Embed(
            title=f"🎀 Cola de Reproducción {random.choice(KAOMOJIS['happy'])}",
            description="La cola está vacía. Usa `!play` para agregar canciones hermosas.",
            color=COLORS['queue']
        )
        empty_embed.set_image(url=get_sakura_gif('queue'))
        empty_embed.set_footer(text="¡Agrega música para comenzar! ♡")
        await ctx.send(embed=empty_embed)
        return

    embed = discord.Embed(
        title=f"🎀 Cola de Reproducción {random.choice(KAOMOJIS['music'])}",
        color=COLORS['queue']
    )
    
    if guild_id in now_playing:
        current = now_playing[guild_id]
        mins, secs = divmod(current.get('duration', 0), 60)
        
        progress_bar = "✧･ﾟ: *✧･ﾟ:*━━━━━━━━━━*:･ﾟ✧*:･ﾟ✧"
        
        embed.add_field(
            name="🌸 Reproduciendo Ahora",
            value=f"**[{current['title'][:60]}]({current['url']})**\n"
                  f"`00:00 {progress_bar} {mins:02}:{secs:02}`\n"
                  f"💗 {current['requester'].mention}",
            inline=False
        )
        embed.add_field(name="\u200b", value="✧･ﾟ: *✧･ﾟ:*　　*:･ﾟ✧*:･ﾟ✧", inline=False)
    
    total_duration = 0
    queue_text = ""
    
    for i, track in enumerate(queues[guild_id][:10], start=1):
        mins, secs = divmod(track.get('duration', 0), 60)
        total_duration += track.get('duration', 0)
        
        queue_text += f"`{i}.` **[{track['title'][:45]}]({track['url']})**\n"
        queue_text += f"     ⏱️ `{mins:02}:{secs:02}` • 💗 {track['requester'].mention}\n\n"
    
    if queue_text:
        embed.add_field(
            name="🎵 Próximas Canciones",
            value=queue_text,
            inline=False
        )
    
    if len(queues[guild_id]) > 10:
        embed.add_field(
            name="✨ Canciones Adicionales",
            value=f"`Y {len(queues[guild_id]) - 10} canciones más esperando...`",
            inline=False
        )
    
    total_mins, total_secs = divmod(total_duration, 60)
    total_hours, total_mins = divmod(total_mins, 60)
    
    embed.add_field(
        name="💫 Estadísticas",
        value=f"`Total: {len(queues[guild_id])} canciones`\n"
              f"`Tiempo: {total_hours:02}:{total_mins:02}:{total_secs:02}`",
        inline=True
    )
    
    embed.set_image(url=get_sakura_gif('queue'))
    
    embed.set_footer(
        text=f"Cola de {ctx.guild.name} ♡",
        icon_url=ctx.guild.icon.url if ctx.guild.icon else None
    )
    embed.timestamp = discord.utils.utcnow()
    
    msg = await ctx.send(embed=embed)
    await msg.add_reaction('🎀')


@bot.command()
async def nowplaying(ctx):
    """Muestra la canción actual"""
    guild_id = ctx.guild.id
    
    if guild_id not in now_playing:
        error_embed = discord.Embed(
            title=f"✨ No hay nada sonando {random.choice(KAOMOJIS['error'])}",
            description="No hay ninguna canción reproduciéndose en este momento.",
            color=COLORS['error']
        )
        error_embed.set_image(url=get_sakura_gif('error'))
        await ctx.send(embed=error_embed)
        return
    
    track = now_playing[guild_id]
    mins, secs = divmod(track.get('duration', 0), 60)
    
    embed = discord.Embed(
        title=f"🌸 Reproducción Actual {random.choice(KAOMOJIS['music'])}",
        description=f"### [{track['title']}]({track['url']})",
        color=COLORS['playing']
    )
    
    progress_bar = "✧･ﾟ: *✧･ﾟ:*━━━━━━━━━━*:･ﾟ✧*:･ﾟ✧"
    embed.add_field(
        name="⏱️ Progreso",
        value=f"`00:00 {progress_bar} {mins:02}:{secs:02}`",
        inline=False
    )
    
    embed.add_field(
        name="💗 Solicitado por",
        value=track['requester'].mention,
        inline=True
    )
    
    embed.add_field(
        name="🎀 En Cola",
        value=f"`{len(queues.get(guild_id, []))} canciones`",
        inline=True
    )
    
    embed.set_image(url=get_sakura_gif('playing'))
    
    embed.set_footer(
        text=f"Reproduciendo con amor ♡ • {ctx.guild.name}",
        icon_url=ctx.guild.icon.url if ctx.guild.icon else None
    )
    embed.timestamp = discord.utils.utcnow()
    
    msg = await ctx.send(embed=embed)
    await msg.add_reaction('🌸')


@bot.command()
async def pause(ctx):
    """Pausa la reproducción"""
    update_activity(ctx.guild.id)
    
    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice_client and voice_client.is_playing():
        voice_client.pause()
        
        pause_embed = discord.Embed(
            title=f"⏸️ Pausada {random.choice(KAOMOJIS['happy'])}",
            description="La música ha sido pausada. Usa `!resume` para continuar.",
            color=COLORS['warning']
        )
        
        guild_id = ctx.guild.id
        if guild_id in now_playing:
            current = now_playing[guild_id]
            pause_embed.add_field(
                name="🎵 Canción Pausada",
                value=f"[{current['title']}]({current['url']})",
                inline=False
            )
        
        pause_embed.set_image(url=get_sakura_gif('pause'))
        pause_embed.set_footer(text=f"Pausado por {ctx.author.display_name} ♡")
        msg = await ctx.send(embed=pause_embed)
        await msg.add_reaction('⏸️')
    else:
        error_embed = discord.Embed(
            title=f"✨ No hay nada sonando {random.choice(KAOMOJIS['error'])}",
            description="No hay ninguna canción reproduciéndose en este momento.",
            color=COLORS['error']
        )
        error_embed.set_image(url=get_sakura_gif('error'))
        await ctx.send(embed=error_embed)


@bot.command()
async def clear(ctx):
    """Limpia la cola sin desconectar"""
    update_activity(ctx.guild.id)
    
    guild_id = ctx.guild.id
    if guild_id in queues:
        count = len(queues[guild_id])
        queues[guild_id].clear()
        preloaded_tracks.pop(guild_id, None)
        
        clear_embed = discord.Embed(
            title=f"🗑️ Cola limpiada {random.choice(KAOMOJIS['success'])}",
            description=f"He eliminado **{count}** canciones de la cola.",
            color=COLORS['success']
        )
        clear_embed.add_field(
            name="💫 Estado",
            value="`La canción actual continúa reproduciéndose`",
            inline=False
        )
        clear_embed.set_image(url=get_sakura_gif('success'))
        clear_embed.set_footer(text=f"Limpiado por {ctx.author.display_name} ♡")
        
        msg = await ctx.send(embed=clear_embed)
        await msg.add_reaction('✨')
    else:
        empty_embed = discord.Embed(
            title=f"🎀 Cola vacía {random.choice(KAOMOJIS['happy'])}",
            description="La cola de reproducción ya está vacía.",
            color=COLORS['queue']
        )
        empty_embed.set_image(url=get_sakura_gif('happy'))
        await ctx.send(embed=empty_embed)


@bot.command()
async def resume(ctx):
    """Reanuda la reproducción"""
    update_activity(ctx.guild.id)
    
    voice_client = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice_client and voice_client.is_paused():
        voice_client.resume()
        
        resume_embed = discord.Embed(
            title=f"▶️ ¡Continuamos! {random.choice(KAOMOJIS['music'])}",
            description="La música ha sido reanudada.",
            color=COLORS['success']
        )
        
        guild_id = ctx.guild.id
        if guild_id in now_playing:
            current = now_playing[guild_id]
            resume_embed.add_field(
                name="🌸 Canción Actual",
                value=f"[{current['title']}]({current['url']})",
                inline=False
            )
        
        resume_embed.set_image(url=get_sakura_gif('playing'))
        resume_embed.set_footer(text=f"Reanudado por {ctx.author.display_name} ♡")
        msg = await ctx.send(embed=resume_embed)
        await msg.add_reaction('▶️')
    else:
        error_embed = discord.Embed(
            title=f"✨ No hay nada pausado {random.choice(KAOMOJIS['error'])}",
            description="No hay ninguna canción pausada en este momento.",
            color=COLORS['error']
        )
        error_embed.set_image(url=get_sakura_gif('error'))
        await ctx.send(embed=error_embed)


@bot.event
async def on_ready():
    print(f'✅ Bot conectado como {bot.user}')
    print(f'🎵 Listo para reproducir música!')
    check_inactivity.start()
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.listening,
            name="música con amor ♡ | !play"
        )
    )


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        error_embed = discord.Embed(
            title=f"✨ Falta información {random.choice(KAOMOJIS['error'])}",
            description=f"Falta un argumento. Usa: `!help {ctx.command}`",
            color=COLORS['error']
        )
        error_embed.set_image(url=get_sakura_gif('error'))
        error_embed.set_footer(text="Revisa el comando e intenta de nuevo ♡")
        await ctx.send(embed=error_embed)
    elif isinstance(error, commands.CommandNotFound):
        pass
    else:
        error_embed = discord.Embed(
            title=f"✨ Error inesperado {random.choice(KAOMOJIS['error'])}",
            description=f"`{str(error)}`",
            color=COLORS['error']
        )
        error_embed.set_image(url=get_sakura_gif('error'))
        error_embed.set_footer(text="Por favor intenta de nuevo ♡")
        await ctx.send(embed=error_embed)
        print(f"Error en comando {ctx.command}: {error}")


# ----- INICIAR BOT -----
bot.run(TOKEN)


# python -m venv bot-env
#-------------------------
# Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
# bot-env\Scripts\activate
# pip install discord.py[voice] youtube_dl PyNaCl yt-dlp
# python main.py
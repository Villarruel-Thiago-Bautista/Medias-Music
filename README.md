# 🎵 Bot de Música de Discord Optimizado

Bot de música para Discord ultra-rápido y estable con soporte para YouTube.

## 🚀 Características

- ⚡ **Súper rápido**: Caché de búsquedas y extracción optimizada
- 🎶 **Sin cortes**: Reconexión automática y buffering mejorado
- 📋 **Cola completa**: Gestión avanzada de cola de reproducción
- 🎚️ **Control de volumen**: Ajusta el volumen en tiempo real
- 📱 **Comandos intuitivos**: Aliases cortos para comandos frecuentes

## 📦 Instalación

1. Instala las dependencias:
\`\`\`bash
pip install -r requirements.txt
\`\`\`

2. Instala FFmpeg:
   - **Windows**: Descarga desde [ffmpeg.org](https://ffmpeg.org/download.html)
   - **Linux**: `sudo apt install ffmpeg`
   - **Mac**: `brew install ffmpeg`

3. Configura tu token:
   - Ve a [Discord Developer Portal](https://discord.com/developers/applications)
   - Crea una aplicación y un bot
   - Copia el token y reemplázalo en `main.py`

4. Ejecuta el bot:
\`\`\`bash
python main.py
\`\`\`

## 🎮 Comandos

| Comando | Alias | Descripción |
|---------|-------|-------------|
| `!play <canción/url>` | `!p` | Reproduce una canción o playlist |
| `!skip` | `!s` | Salta a la siguiente canción |
| `!queue` | `!q` | Muestra la cola de reproducción |
| `!nowplaying` | `!np`, `!current` | Muestra la canción actual |
| `!pause` | - | Pausa la reproducción |
| `!resume` | - | Reanuda la reproducción |
| `!stop` | - | Detiene y desconecta el bot |
| `!clear` | `!c` | Limpia la cola |
| `!remove <número>` | `!rm` | Elimina una canción de la cola |
| `!volume <0-100>` | `!v` | Ajusta el volumen |

## ⚡ Optimizaciones Implementadas

1. **Caché de búsquedas**: Las búsquedas recientes se guardan por 1 hora
2. **Extracción rápida**: Usa `extract_flat` para playlists
3. **Reconexión automática**: FFmpeg se reconecta si hay problemas de red
4. **Buffer mejorado**: Reduce cortes durante la reproducción
5. **Manejo de errores**: Continúa reproduciendo si una canción falla

## 🔧 Solución de problemas

- **"No module named 'discord'"**: Ejecuta `pip install -r requirements.txt`
- **"FFmpeg not found"**: Instala FFmpeg y agrégalo al PATH
- **Bot lento**: Verifica tu conexión a internet
- **Cortes frecuentes**: Aumenta el buffer en `ffmpeg_options`

## 📝 Notas

- El bot usa yt-dlp (fork mejorado de youtube-dl)
- Las URLs de audio expiran después de ~6 horas (se refrescan automáticamente)
- El caché se limpia automáticamente después de 1 hora

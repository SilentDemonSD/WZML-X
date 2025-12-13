import asyncio
import io
from datetime import datetime
from pyrogram import Client
from pyrogram.types import Message, CallbackQuery
from bot.core.plugin_manager import PluginBase, PluginInfo
from bot.helper.ext_utils.bot_utils import new_task
from bot.helper.telegram_helper.message_utils import send_message, edit_message, send_photo
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot import LOGGER


class SpeedtestPlugin(PluginBase):
    PLUGIN_INFO = PluginInfo(
        name="speedtest",
        version="1.0.0",
        author="WZML-X Team",
        description="Network speed test plugin with multiple servers",
        enabled=True,
        handlers=[],
        commands=["speedtest", "speedtest_servers"],
        dependencies=["speedtest-cli"]
    )

    def __init__(self):
        super().__init__()
        self.servers_cache = {}
        self.last_cache_update = None

    async def on_load(self) -> bool:
        try:
            proc = await asyncio.create_subprocess_exec(
                'speedtest', '--version',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await proc.communicate()
            return proc.returncode == 0
        except Exception:
            return False

    async def get_servers(self):
        try:
            proc = await asyncio.create_subprocess_exec(
                'speedtest', '--list',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()
            if proc.returncode != 0:
                return []
            
            servers = []
            for line in stdout.decode().split('\n'):
                if ')' in line and 'km' in line:
                    parts = line.strip().split(')')
                    if len(parts) >= 2:
                        server_id = parts[0].strip()
                        server_info = parts[1].strip()
                        servers.append(f"{server_id}) {server_info}")
            return servers[:20]
        except Exception as e:
            LOGGER.error(f"Error getting servers: {e}")
            return []

    async def run_speedtest(self, server_id=None):
        try:
            cmd = ['speedtest', '--simple']
            if server_id:
                cmd.extend(['--server', str(server_id)])
            
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            if proc.returncode != 0:
                return None, stderr.decode()
            
            return stdout.decode(), None
        except Exception as e:
            return None, str(e)

    async def create_speedtest_image(self, result_text):
        try:
            from PIL import Image, ImageDraw, ImageFont
            
            img = Image.new('RGB', (800, 400), color='#1a1a1a')
            draw = ImageDraw.Draw(img)
            
            try:
                font_large = ImageFont.truetype("arial.ttf", 36)
                font_medium = ImageFont.truetype("arial.ttf", 24)
                font_small = ImageFont.truetype("arial.ttf", 18)
            except Exception:
                font_large = ImageFont.load_default()
                font_medium = ImageFont.load_default()
                font_small = ImageFont.load_default()
            
            draw.text((50, 50), "WZML-X Speedtest", fill='#00ff00', font=font_large)
            
            y_pos = 120
            for line in result_text.strip().split('\n'):
                if line.strip():
                    if 'Ping' in line:
                        draw.text((50, y_pos), line, fill='#ffff00', font=font_medium)
                    elif 'Download' in line:
                        draw.text((50, y_pos), line, fill='#00ffff', font=font_medium)
                    elif 'Upload' in line:
                        draw.text((50, y_pos), line, fill='#ff00ff', font=font_medium)
                    else:
                        draw.text((50, y_pos), line, fill='#ffffff', font=font_small)
                    y_pos += 40
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            draw.text((50, 350), f"Generated: {timestamp}", fill='#888888', font=font_small)
            
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='PNG')
            img_buffer.seek(0)
            return img_buffer
        except Exception:
            LOGGER.error("Error creating image")
            return None


@new_task
async def speedtest_command(client: Client, message: Message):
    plugin = SpeedtestPlugin()
    
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    server_id = args[0] if args and args[0].isdigit() else None
    
    status_msg = await send_message(message, "🚀 Running speedtest...")
    
    result, error = await plugin.run_speedtest(server_id)
    
    if error:
        await edit_message(status_msg, f"❌ Speedtest failed:\n`{error}`")
        return
    
    if not result:
        await edit_message(status_msg, "❌ No speedtest result received")
        return
    
    try:
        img_buffer = await plugin.create_speedtest_image(result)
        if img_buffer:
            await send_photo(message, img_buffer, caption=f"🚀 **Speedtest Results**\n\n`{result}`")
            await status_msg.delete()
        else:
            await edit_message(status_msg, f"🚀 **Speedtest Results**\n\n`{result}`")
    except Exception as e:
        await edit_message(status_msg, f"🚀 **Speedtest Results**\n\n`{result}`")


@new_task
async def speedtest_servers_command(client: Client, message: Message):
    plugin = SpeedtestPlugin()
    
    status_msg = await send_message(message, "🔍 Getting available servers...")
    
    servers = await plugin.get_servers()
    
    if not servers:
        await edit_message(status_msg, "❌ Could not retrieve server list")
        return
    
    server_text = "🌐 **Available Speedtest Servers:**\n\n"
    server_text += "\n".join(servers[:15])
    server_text += "\n\n📝 Use `/speedtest <server_id>` to test with specific server"
    
    buttons = ButtonMaker()
    buttons.data_button("🚀 Run Default Test", "speedtest_run_default")
    buttons.data_button("🔄 Refresh List", "speedtest_refresh_servers")
    buttons.data_button("❌ Close", "speedtest_close")
    
    await edit_message(status_msg, server_text, buttons.build_menu(1))


@new_task
async def speedtest_callback(client: Client, query: CallbackQuery):
    data = query.data
    plugin = SpeedtestPlugin()
    
    if data == "speedtest_run_default":
        await query.answer("Starting speedtest...")
        status_msg = await edit_message(query.message, "🚀 Running speedtest...")
        
        result, error = await plugin.run_speedtest()
        
        if error:
            await edit_message(status_msg, f"❌ Speedtest failed:\n`{error}`")
            return
        
        try:
            img_buffer = await plugin.create_speedtest_image(result)
            if img_buffer:
                await send_photo(query.message, img_buffer, caption=f"🚀 **Speedtest Results**\n\n`{result}`")
                await status_msg.delete()
            else:
                await edit_message(status_msg, f"🚀 **Speedtest Results**\n\n`{result}`")
        except Exception:
            await edit_message(status_msg, f"🚀 **Speedtest Results**\n\n`{result}`")
    
    elif data == "speedtest_refresh_servers":
        await query.answer("Refreshing server list...")
        servers = await plugin.get_servers()
        
        if servers:
            server_text = "🌐 **Available Speedtest Servers:**\n\n"
            server_text += "\n".join(servers[:15])
            server_text += "\n\n📝 Use `/speedtest <server_id>` to test with specific server"
            
            buttons = ButtonMaker()
            buttons.data_button("🚀 Run Default Test", "speedtest_run_default")
            buttons.data_button("🔄 Refresh List", "speedtest_refresh_servers")
            buttons.data_button("❌ Close", "speedtest_close")
            
            await edit_message(query.message, server_text, buttons.build_menu(1))
        else:
            await query.answer("Failed to refresh server list", show_alert=True)
    
    elif data == "speedtest_close":
        await query.message.delete()
        await query.answer()


plugin_instance = SpeedtestPlugin()

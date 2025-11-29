# -*- coding: utf-8 -*-
# Compression & Download Handler
# Integrated compression features before download

from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
)
import os
import subprocess
import shutil
from pathlib import Path
from .user_compressor_session import session_manager
from bot import LOGGER

# Compression action options
COMPRESSION_OPTIONS = {
    'compress': {'label': '⚡ ضغط الفيديو', 'emoji': '⚡'},
    'burn_subtitle': {'label': '📄 حرق الترجمة', 'emoji': '📄'},
    'extract': {'label': '📝 استخراج مسارات', 'emoji': '📝'},
    'merge_audio': {'label': '🔊 دمج صوت', 'emoji': '🔊'},
    'scale': {'label': '📺 تغيير الدقة', 'emoji': '📺'},
}

async def get_compression_keyboard(user_id: int):
    """Generate inline keyboard for compression options"""
    buttons = []
    
    for action, info in COMPRESSION_OPTIONS.items():
        buttons.append([
            InlineKeyboardButton(
                text=info['label'],
                callback_data=f"comp_toggle_{action}_{user_id}"
            )
        ])
    
    # Add Done button
    buttons.append([
        InlineKeyboardButton(
            text=✅ تم - ابدأ التحميل',
            callback_data=f"comp_done_{user_id}"
        )
    ])
    
    return InlineKeyboardMarkup(buttons)


async def show_compression_menu(client: Client, message: Message, link: str, user_id: int):
    """Display compression options menu before downloading"""
    session = session_manager.create_session(user_id)
    session.set_link(link)
    
    text = f"""🌟 اختر خيارات الضغط والمعالجة قبل التحميل
    
الرابط: `{link}`

اختر الخيارات المطلوبة ثم اضغط 'تم' لبدء التحميل:
"""
    
    keyboard = await get_compression_keyboard(user_id)
    await message.reply_text(text, reply_markup=keyboard)


async def handle_compression_callback(client: Client, callback_query: CallbackQuery):
    """Handle compression option toggles"""
    user_id = callback_query.from_user.id
    data = callback_query.data
    
    if data.startswith('comp_toggle_'):
        parts = data.split('_')
        action = parts[2]
        
        session = session_manager.get_session(user_id)
        if not session:
            await callback_query.answer(❌ جلسة غير موجودة', show_alert=True)
            return
        
        # Toggle action
        if action in session.actions:
            session.remove_action(action)
            status = ✅ تم إلغاء'
        else:
            session.add_action(action)
            status = ✅ تم اختيار'
        
        # Show selected options
        selected = ', '.join([COMPRESSION_OPTIONS[a]['emoji'] for a in session.actions])
        selected_text = selected if selected else '🚩 لم يتم اختيار أي خيار'
        
        await callback_query.answer(f"{status}: {action}")
        await callback_query.edit_message_text(
            text=f"""🌟 اختر خيارات الضغط والمعالجة قبل التحميل
            
الرابط: `{session.link}`

الخيارات المختارة: {selected_text}
            """,
            reply_markup=await get_compression_keyboard(user_id)
        )
        
    elif data.startswith('comp_done_'):
        session = session_manager.get_session(user_id)
        if not session:
            await callback_query.answer('❌ جلسة غير موجودة', show_alert=True)
            return
        
        if 'burn_subtitle' in session.actions:
            await callback_query.answer()
            await callback_query.message.reply_text(
                📄 اختر ملف الترجمة (SRT/ASS/VTT)\n\nأرسل ملف الترجمة الآن:'
            )
        else:
            await callback_query.answer()
            await callback_query.message.reply_text(📁 جاري التحميل والمعالجة...')
            # Proceed with download and compression
            # This will be handled by the existing download logic


async def handle_subtitle_upload(client: Client, message: Message):
    """Handle subtitle file upload for burning"""
    user_id = message.from_user.id
    session = session_manager.get_session(user_id)
    
    if not session or 'burn_subtitle' not in session.actions:
        return
    
    if not message.document:
        await message.reply_text(❌ الرجاء إرسال ملف صحيح')
        return
    
    # Download subtitle
    try:
        file_path = await message.download()
        session.set_subtitle_file(file_path)
        
        await message.reply_text(
            f✅ تم استقبال الترجمة: {message.document.file_name}\n\nجاري التحميل والمعالجة...'
        )
        
        # Now proceed with download and compression
        # This will be triggered by existing download logic
    except Exception as e:
        LOGGER.error(f"Error downloading subtitle: {e}")
        await message.reply_text(f❌ حدث خطأ: {str(e)}')


async def apply_compression(input_file: str, session, output_dir: str = None) -> str:
    """
    Apply compression and encoding based on session options
    Uses orso_compressor.py with selected actions
    """
    try:
        if not output_dir:
            output_dir = os.path.dirname(input_file) or '.'
        
        # Build compression command based on selected actions
        cmd = ['python3', 'encode/orso_compressor_cli.py']
        cmd.extend(['--input', input_file])
        cmd.extend(['--output', output_dir])
        
        # Add selected compression options
        if 'compress' in session.actions:
            cmd.append('--compress')
        
        if 'burn_subtitle' in session.actions and session.subtitle_path:
            cmd.extend(['--subtitle', session.subtitle_path])
            cmd.append('--burn-sub')
        
        if 'scale' in session.actions:
            cmd.extend(['--scale', '1080'])  # Default to 1080p
        
        # Execute compression
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
        
        if result.returncode == 0:
            # Find output file
            output_files = list(Path(output_dir).glob('[Orsozox]*'))
            if output_files:
                return str(output_files[-1])  # Return latest file
            return input_file  # Return original if no output found
        else:
            LOGGER.error(f"Compression error: {result.stderr}")
            return input_file
    
    except Exception as e:
        LOGGER.error(f"Error in apply_compression: {e}")
        return input_file

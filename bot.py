import os
import asyncio
import random
from telegram import Bot
from telegram.ext import Application, CommandHandler, ContextTypes
import logging
from threading import Lock
import time

# دریافت توکن‌ها از متغیر محیطی
BOT_TOKENS = eval(os.getenv('BOT_TOKENS', '["8488494454:AAE1sEmRtRqrbHDL_qg1UiGl0TwJLjj4ByM","8238948579:AAGktvxW6LhuKBXRRA_WsfD9n2bsMMC-izg","8269701842:AAEDLw8chE3jfcODYEw30Et636z3-wX7kPQ","8228864219:AAHuEkDuF5P9WvMNNws9wZigq12RTDdv4uw"]'))
OWNER_ID = int(os.getenv('OWNER_ID', '7798986445'))

class BotConfig:
    def __init__(self):
        self.groups_list = []
        self.admins = [OWNER_ID]
        self.message_delay = 0.2
        self.active_broadcast = False
        self.broadcast_message = ""
        self.broadcast_lock = Lock()
        self.current_task = None

bot_configs = {token: BotConfig() for token in BOT_TOKENS}

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update, context):
    token = context.bot.token
    config = bot_configs[token]
    
    if update.effective_user.id not in config.admins:
        await update.message.reply_text("❌ دسترسی denied!")
        return
        
    await update.message.reply_text(
        "🤖 ربات آماده است!\n\n"
        "📋 دستورات قابل استفاده:\n"
        "/addadmin [user_id] - افزودن ادمین جدید\n"
        "/addgroup [group_id] - افزودن گروه برای ارسال\n"
        "/setdelay [seconds] - تنظیم سرعت ارسال\n"
        "/set_message [پیام] - تنظیم پیام برای ارسال\n"
        "/start_pim - شروع ارسال پیام\n"
        "/stop_pim - توقف ارسال پیام"
    )

async def add_admin(update, context):
    token = context.bot.token
    config = bot_configs[token]
    
    if update.effective_user.id != config.admins[0]:
        await update.message.reply_text("❌ فقط مالک می‌تواند ادمین اضافه کند!")
        return
    
    try:
        new_admin = int(context.args[0])
        config.admins.append(new_admin)
        await update.message.reply_text(f"✅ ادمین {new_admin} افزوده شد!")
    except:
        await update.message.reply_text("❌ فرمت صحیح: /addadmin [user_id]")

async def add_group(update, context):
    token = context.bot.token
    config = bot_configs[token]
    
    if update.effective_user.id not in config.admins:
        await update.message.reply_text("❌ دسترسی denied!")
        return
    
    try:
        group_id = context.args[0]
        config.groups_list.append(group_id)
        await update.message.reply_text(f"✅ گروه {group_id} افزوده شد!")
    except:
        await update.message.reply_text("❌ فرمت صحیح: /addgroup [group_id]")

async def set_delay(update, context):
    token = context.bot.token
    config = bot_configs[token]
    
    if update.effective_user.id not in config.admins:
        await update.message.reply_text("❌ دسترسی denied!")
        return
    
    try:
        config.message_delay = float(context.args[0])
        await update.message.reply_text(f"✅ تأخیر به {config.message_delay} ثانیه تنظیم شد!")
    except:
        await update.message.reply_text("❌ فرمت صحیح: /setdelay [seconds]")

async def set_message(update, context):
    token = context.bot.token
    config = bot_configs[token]
    
    if update.effective_user.id not in config.admins:
        await update.message.reply_text("❌ دسترسی denied!")
        return
    
    if not context.args:
        await update.message.reply_text("❌ لطفا پیام را وارد کنید!")
        return
    
    config.broadcast_message = " ".join(context.args)
    await update.message.reply_text(f"✅ پیام تنظیم شد:\n{config.broadcast_message}")

async def send_message_safe(bot_token, group_id, message):
    try:
        bot = Bot(token=bot_token)
        await bot.send_message(chat_id=group_id, text=message)
        return True
    except Exception as e:
        logger.error(f"Error sending to {group_id} with {bot_token}: {e}")
        return False

async def broadcast_loop(config, token, update):
    success_count = 0
    total_attempts = 0
    
    while config.active_broadcast:
        if not config.broadcast_message:
            await asyncio.sleep(1)
            continue
            
        for group in config.groups_list:
            if not config.active_broadcast:
                break
                
            if await send_message_safe(token, group, config.broadcast_message):
                success_count += 1
            total_attempts += 1
            
            await asyncio.sleep(config.message_delay + random.uniform(0.1, 0.3))
        
        if config.active_broadcast:
            await asyncio.sleep(1)
    
    return success_count, total_attempts

async def start_pim(update, context):
    token = context.bot.token
    config = bot_configs[token]
    
    if update.effective_user.id not in config.admins:
        await update.message.reply_text("❌ دسترسی denied!")
        return
    
    if not config.groups_list:
        await update.message.reply_text("❌ هیچ گروهی افزوده نشده است!")
        return
    
    if not config.broadcast_message:
        await update.message.reply_text("❌ هیچ پیامی تنظیم نشده است!")
        return
    
    with config.broadcast_lock:
        if config.active_broadcast:
            await update.message.reply_text("⚠️ ارسال در حال حاضر فعال است!")
            return
        
        config.active_broadcast = True
        await update.message.reply_text("🚀 شروع ارسال پیام...")
        
        config.current_task = asyncio.create_task(
            broadcast_loop_wrapper(config, token, update)
        )

async def broadcast_loop_wrapper(config, token, update):
    try:
        success_count, total_attempts = await broadcast_loop(config, token, update)
        await update.message.reply_text(
            f"✅ ارسال متوقف شد!\n"
            f"📊 آمار:\n"
            f"• ارسال موفق: {success_count}\n"
            f"• تلاش‌های کل: {total_attempts}"
        )
    except asyncio.CancelledError:
        await update.message.reply_text("⏹️ ارسال متوقف شد")
    except Exception as e:
        logger.error(f"Broadcast error: {e}")
        await update.message.reply_text(f"❌ خطا در ارسال: {e}")
    finally:
        config.active_broadcast = False

async def stop_pim(update, context):
    token = context.bot.token
    config = bot_configs[token]
    
    if update.effective_user.id not in config.admins:
        await update.message.reply_text("❌ دسترسی denied!")
        return
    
    with config.broadcast_lock:
        if not config.active_broadcast:
            await update.message.reply_text("⚠️ ارسال از قبل متوقف است!")
            return
        
        config.active_broadcast = False
        if config.current_task:
            config.current_task.cancel()
        await update.message.reply_text("⏹️ در حال توقف ارسال...")

def main():
    applications = []
    
    for token in BOT_TOKENS:
        try:
            application = Application.builder().token(token).build()
            
            application.add_handler(CommandHandler("start", start))
            application.add_handler(CommandHandler("addadmin", add_admin))
            application.add_handler(CommandHandler("addgroup", add_group))
            application.add_handler(CommandHandler("setdelay", set_delay))
            application.add_handler(CommandHandler("set_message", set_message))
            application.add_handler(CommandHandler("start_pim", start_pim))
            application.add_handler(CommandHandler("stop_pim", stop_pim))
            
            applications.append(application)
            
        except Exception as e:
            logger.error(f"Error starting bot {token}: {e}")

    # اجرای همه ربات‌ها
    for app in applications:
        try:
            app.run_polling()
        except Exception as e:
            logger.error(f"Error running app: {e}")

if __name__ == "__main__":
    main()

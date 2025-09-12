import os
import asyncio
import random
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes
import logging
from threading import Lock
import time
from datetime import datetime

# فقط یک ربات فعال
BOT_TOKENS = ["8488494454:AAE1sEmRtRqrbHDL_qg1UiGl0TwJLjj4ByM"] # ربات اصلی
OWNER_ID = 7798986445 # آیدی مالک

class BotConfig:
    def __init__(self):
        self.groups_list = []
        self.admins = [OWNER_ID]
        self.message_delay = 0.1
        self.active_broadcast = False
        self.broadcast_message = ""
        self.max_messages = 0  # 0 = unlimited
        self.sent_messages = 0
        self.broadcast_lock = Lock()
        self.current_task = None
        self.start_time = None
        self.status = "⏸️ غیرفعال"

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
        "/addadmin [user_id] - افزودن ادمین\n"
        "/removeadmin [user_id] - حذف ادمین\n"
        "/addgroup [group_id] - افزودن گروه\n"
        "/removegroup [group_id] - حذف گروه\n"
        "/listgroups - نمایش گروه‌ها\n"
        "/setdelay [seconds] - تنظیم سرعت\n"
        "/setcount [number] - تنظیم تعداد پیام (0=نامحدود)\n"
        "/set_message [پیام] - تنظیم پیام\n"
        "/clearmessage - حذف پیام تنظیم شده\n"
        "/panel - نمایش پنل مدیریت\n"
        "/start_pim - شروع ارسال\n"
        "/stop_pim - توقف ارسال"
    )

async def panel(update, context):
    token = context.bot.token
    config = bot_configs[token]
    
    if update.effective_user.id not in config.admins:
        await update.message.reply_text("❌ دسترسی denied!")
        return
    
    # محاسبه زمان فعالیت
    uptime = "N/A"
    if config.start_time:
        uptime = str(datetime.now() - config.start_time).split('.')[0]
    
    # ایجاد پنل شیشه ای
    panel_text = f"""
╔══════════════════════╗
║      🚀 پنل مدیریت ربات      ║
╠══════════════════════╣
║ 📊 وضعیت: {config.status}
║ 👥 تعداد گروه‌ها: {len(config.groups_list)}
║ 📨 پیام تنظیم شده: {'✅' if config.broadcast_message else '❌'}
║ ⚡ سرعت ارسال: {config.message_delay} ثانیه
║ 🔢 تعداد پیام: {'∞' if config.max_messages == 0 else config.max_messages}
║ 📤 ارسال شده: {config.sent_messages}
║ ⏰ زمان فعالیت: {uptime}
╠══════════════════════╣
║ 📋 /listgroups - لیست گروه‌ها
║ ⚙️ /setdelay - تنظیم سرعت
║ 🔢 /setcount - تنظیم تعداد
║ 📝 /set_message - تنظیم پیام
║ 🚀 /start_pim - شروع ارسال
║ ⏹️ /stop_pim - توقف ارسال
╚══════════════════════╝
    """
    
    await update.message.reply_text(panel_text)

async def add_admin(update, context):
    token = context.bot.token
    config = bot_configs[token]
    
    if update.effective_user.id != config.admins[0]:
        await update.message.reply_text("❌ فقط مالک می‌تواند ادمین اضافه کند!")
        return
        
    try:
        new_admin = int(context.args[0])
        if new_admin in config.admins:
            await update.message.reply_text("⚠️ این کاربر قبلاً ادمین است!")
            return
            
        config.admins.append(new_admin)
        await update.message.reply_text(f"✅ ادمین {new_admin} افزوده شد!")
    except:
        await update.message.reply_text("❌ فرمت صحیح: /addadmin [user_id]")

async def remove_admin(update, context):
    token = context.bot.token
    config = bot_configs[token]
    
    if update.effective_user.id != config.admins[0]:
        await update.message.reply_text("❌ فقط مالک می‌تواند ادمین حذف کند!")
        return
        
    try:
        admin_id = int(context.args[0])
        if admin_id == config.admins[0]:
            await update.message.reply_text("❌ نمی‌توانی مالک اصلی رو حذف کنی!")
            return
            
        if admin_id not in config.admins:
            await update.message.reply_text("❌ این کاربر ادمین نیست!")
            return
            
        config.admins.remove(admin_id)
        await update.message.reply_text(f"✅ ادمین {admin_id} حذف شد!")
    except:
        await update.message.reply_text("❌ فرمت صحیح: /removeadmin [user_id]")

async def add_group(update, context):
    token = context.bot.token
    config = bot_configs[token]
    
    if update.effective_user.id not in config.admins:
        await update.message.reply_text("❌ دسترسی denied!")
        return
        
    try:
        group_id = context.args[0]
        if group_id in config.groups_list:
            await update.message.reply_text("⚠️ این گروه قبلاً اضافه شده!")
            return
            
        config.groups_list.append(group_id)
        await update.message.reply_text(f"✅ گروه {group_id} افزوده شد!")
    except:
        await update.message.reply_text("❌ فرمت صحیح: /addgroup [group_id]")

async def remove_group(update, context):
    token = context.bot.token
    config = bot_configs[token]
    
    if update.effective_user.id not in config.admins:
        await update.message.reply_text("❌ دسترسی denied!")
        return
        
    try:
        group_id = context.args[0]
        if group_id not in config.groups_list:
            await update.message.reply_text("❌ این گروه وجود ندارد!")
            return
            
        config.groups_list.remove(group_id)
        await update.message.reply_text(f"✅ گروه {group_id} حذف شد!")
    except:
        await update.message.reply_text("❌ فرمت صحیح: /removegroup [group_id]")

async def list_groups(update, context):
    token = context.bot.token
    config = bot_configs[token]
    
    if update.effective_user.id not in config.admins:
        await update.message.reply_text("❌ دسترسی denied!")
        return
        
    if not config.groups_list:
        await update.message.reply_text("📭 هیچ گروهی اضافه نشده است!")
        return
        
    groups_text = "📋 لیست گروه‌ها:\n" + "\n".join([f"• {group}" for group in config.groups_list])
    await update.message.reply_text(groups_text)

async def set_delay(update, context):
    token = context.bot.token
    config = bot_configs[token]
    
    if update.effective_user.id not in config.admins:
        await update.message.reply_text("❌ دسترسی denied!")
        return
        
    try:
        config.message_delay = max(0.05, float(context.args[0]))
        await update.message.reply_text(f"✅ تأخیر به {config.message_delay} ثانیه تنظیم شد!")
    except:
        await update.message.reply_text("❌ فرمت صحیح: /setdelay [seconds]")

async def set_count(update, context):
    token = context.bot.token
    config = bot_configs[token]
    
    if update.effective_user.id not in config.admins:
        await update.message.reply_text("❌ دسترسی denied!")
        return
        
    try:
        count = int(context.args[0])
        config.max_messages = max(0, count)
        count_text = "نامحدود" if count == 0 else str(count)
        await update.message.reply_text(f"✅ تعداد پیام به {count_text} تنظیم شد!")
    except:
        await update.message.reply_text("❌ فرمت صحیح: /setcount [number] (0=نامحدود)")

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

async def clear_message(update, context):
    token = context.bot.token
    config = bot_configs[token]
    
    if update.effective_user.id not in config.admins:
        await update.message.reply_text("❌ دسترسی denied!")
        return
        
    config.broadcast_message = ""
    await update.message.reply_text("✅ پیام تنظیم شده حذف شد!")

async def send_message_safe(bot_token, group_id, message):
    try:
        bot = Bot(token=bot_token)
        await bot.send_message(chat_id=group_id, text=message)
        return True
    except Exception as e:
        if "Flood control" in str(e):
            wait_time = random.randint(1, 3)
            logger.warning(f"Flood control - Waiting {wait_time} seconds")
            await asyncio.sleep(wait_time)
            return await send_message_safe(bot_token, group_id, message)
        elif "Timed out" in str(e):
            await asyncio.sleep(1)
            return await send_message_safe(bot_token, group_id, message)
        else:
            logger.error(f"Error sending to {group_id}: {e}")
            return False

async def broadcast_loop(config, token, update):
    success_count = 0
    total_attempts = 0
    error_count = 0
    config.sent_messages = 0
    config.start_time = datetime.now()
    config.status = "🟢 در حال ارسال"
    
    while (config.active_broadcast and 
           error_count < 10 and 
           (config.max_messages == 0 or config.sent_messages < config.max_messages)):
        
        if not config.broadcast_message:
            await update.message.reply_text("⚠️ پیامی برای ارسال وجود ندارد!")
            config.active_broadcast = False
            break
            
        if not config.groups_list:
            await update.message.reply_text("⚠️ گروهی برای ارسال وجود ندارد!")
            config.active_broadcast = False
            break
            
        for group in config.groups_list.copy():
            if not config.active_broadcast:
                break
                
            if config.max_messages > 0 and config.sent_messages >= config.max_messages:
                await update.message.reply_text("✅ تعداد پیام مورد نظر ارسال شد!")
                config.active_broadcast = False
                break
                
            success = await send_message_safe(token, group, config.broadcast_message)
            
            if success:
                success_count += 1
                config.sent_messages += 1
                error_count = 0
            else:
                error_count += 1
                
            total_attempts += 1
            
            # گزارش پیشرفت
            if total_attempts % 10 == 0:
                progress = f"{config.sent_messages}/{config.max_messages}" if config.max_messages > 0 else f"{config.sent_messages}/∞"
                await update.message.reply_text(
                    f"📊 پیشرفت ارسال:\n"
                    f"• ارسال موفق: {success_count}\n"
                    f"• پیشرفت: {progress}\n"
                    f"• تلاش‌های کل: {total_attempts}"
                )
            
            await asyncio.sleep(config.message_delay)
            
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
        await update.message.reply_text("❌ هیچ گروهی افزوده نشده است! از /addgroup استفاده کن")
        return
        
    if not config.broadcast_message:
        await update.message.reply_text("❌ هیچ پیامی تنظیم نشده است! از /set_message استفاده کن")
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
        if config.active_broadcast:
            await update.message.reply_text(
                f"✅ ارسال کامل شد!\n"
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
        config.status = "⏸️ غیرفعال"

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
        await update.message.reply_text("⏹️ ارسال متوقف شد!")

def main():
    applications = []
    
    for token in BOT_TOKENS:
        try:
            application = Application.builder().token(token).build()
            application.add_handler(CommandHandler("start", start))
            application.add_handler(CommandHandler("panel", panel))
            application.add_handler(CommandHandler("addadmin", add_admin))
            application.add_handler(CommandHandler("removeadmin", remove_admin))
            application.add_handler(CommandHandler("addgroup", add_group))
            application.add_handler(CommandHandler("removegroup", remove_group))
            application.add_handler(CommandHandler("listgroups", list_groups))
            application.add_handler(CommandHandler("setdelay", set_delay))
            application.add_handler(CommandHandler("setcount", set_count))
            application.add_handler(CommandHandler("set_message", set_message))
            application.add_handler(CommandHandler("clearmessage", clear_message))
            application.add_handler(CommandHandler("start_pim", start_pim))
            application.add_handler(CommandHandler("stop_pim", stop_pim))
            
            applications.append(application)
        except Exception as e:
            logger.error(f"Error starting bot {token}: {e}")
    
    # اجرای ربات‌ها
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    tasks = []
    for app in applications:
        try:
            tasks.append(app.run_polling(drop_pending_updates=True))
        except Exception as e:
            logger.error(f"Error running app: {e}")
    
    try:
        loop.run_until_complete(asyncio.gather(*tasks))
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()

if __name__ == "__main__":
    main()

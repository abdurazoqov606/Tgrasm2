            return

        for url in bg:
            try:
                bot.send_photo(uid, url)
            except:
                pass

        img_cache[uid] = {"p": prompt, "sid": sid, "asp": asp, "bg": bg, "nb": nb}
        add_history(uid, prompt, sid, asp)
        increment_gen(uid)

        bot.send_message(uid,
            T(lang, "gen_done", count=len(bg)),
            reply_markup=make_post_gen_keyboard(lang)
        )

    threading.Thread(target=do_gen, daemon=True).start()

def handle_broadcast_input(message, admin_uid):
    temp_data.pop(admin_uid, None)
    all_users = get_all_users()
    total     = len(all_users)

    prog_msg = bot.send_message(admin_uid,
        f"📣 Yuborilmoqda...\n👥 Jami: {total} ta foydalanuvchi"
    )

    sent_count = 0
    fail_count = 0

    def do_broadcast():
        nonlocal sent_count, fail_count
        for i, target_uid in enumerate(all_users):
            try:
                if message.content_type == 'text':
                    bot.send_message(target_uid, message.text)
                elif message.content_type == 'photo':
                    bot.send_photo(target_uid, message.photo[-1].file_id,
                                   caption=message.caption or "")
                elif message.content_type == 'video':
                    bot.send_video(target_uid, message.video.file_id,
                                   caption=message.caption or "")
                elif message.content_type == 'document':
                    bot.send_document(target_uid, message.document.file_id,
                                      caption=message.caption or "")
                elif message.content_type == 'animation':
                    bot.send_animation(target_uid, message.animation.file_id,
                                       caption=message.caption or "")
                elif message.content_type == 'sticker':
                    bot.send_sticker(target_uid, message.sticker.file_id)
                sent_count += 1
            except Exception:
                fail_count += 1
            if (i + 1) % 50 == 0:
                try:
                    bot.edit_message_text(
                        f"📣 Yuborilmoqda...\n"
                        f"✅ Yuborildi: {sent_count}\n"
                        f"❌ Xatolik: {fail_count}\n"
                        f"📊 Qoldi: {total - i - 1}",
                        admin_uid, prog_msg.message_id
                    )
                except:
                    pass
            time.sleep(0.03)

        conn = get_db()
        c = conn.cursor()
        c.execute("INSERT INTO broadcasts (text, sent_count, fail_count, admin_id) VALUES (?,?,?,?)",
                  (str(message.text or message.content_type), sent_count, fail_count, admin_uid))
        conn.commit()
        conn.close()

        try:
            bot.edit_message_text(
                f"✅ BROADCAST TUGADI!\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"👥 Jami: {total}\n"
                f"✅ Yuborildi: {sent_count}\n"
                f"❌ Xatolik: {fail_count}\n"
                f"⏰ {datetime.now().strftime('%H:%M:%S')}",
                admin_uid, prog_msg.message_id
            )
        except:
            bot.send_message(admin_uid,
                f"✅ Broadcast tugadi! Yuborildi: {sent_count}, Xatolik: {fail_count}"
            )

    threading.Thread(target=do_broadcast, daemon=True).start()

# ─────────────────────────────────────────────────────────────
#  🚀  BOTNI ISHGA TUSHIRISH
# ─────────────────────────────────────────────────────────────
def main():
    print("╔══════════════════════════════════════════════════╗")
    print("║        🤖 VSF AI PHOTO BOT — PREMIUM            ║")
    print(f"║        Versiya: {BOT_VERSION}                         ║")
    print(f"║        Muallif: {AUTHOR}                      ║")
    print("╚══════════════════════════════════════════════════╝")

    init_db()
    print("✅ Ma'lumotlar bazasi ishga tushirildi")

    channels = get_channels()
    print(f"📢 Faol kanallar: {len(channels)}")
    for ch, title in channels:
        print(f"   • {ch} — {title}")

    print(f"🎨 Stillar soni  : {len(STYLES)}")
    print(f"📐 Nisbatlar soni: {len(ASPECTS)}")
    print(f"🛡 Admin ID(lar) : {ADMIN_IDS}")
    print()
    print("🟢 Bot ishga tushdi! Polling boshlandi...\n")

    # Render Background Worker: polling uchun Flask yoki port kerak emas.
    try:
        bot.remove_webhook()
    except Exception as exc:
        print(f"Webhook tozalash ogohlantirishi: {exc}")

    bot.infinity_polling(
        timeout=30,
        long_polling_timeout=30,
        allowed_updates=["message", "callback_query"],
        skip_pending=True
    )

import os
import time
import threading
import json
from telethon import TelegramClient, events
from telethon.errors import UserAlreadyParticipantError, InviteHashExpiredError, UsernameNotOccupiedError, ChannelPrivateError
from telethon.tl.types import Message

with open('config.json', 'r') as f: DATA = json.load(f)
def getenv(var): return os.environ.get(var) or DATA.get(var, None)

bot_token = getenv("TOKEN") 
api_hash = getenv("HASH") 
api_id = getenv("ID")

# Initialize bot client
bot = TelegramClient("mybot", api_id, api_hash).start(bot_token=bot_token)

ss = getenv("STRING")
if ss is not None:
    acc = TelegramClient("myacc", api_id, api_hash).start(session_string=ss)
else: 
    acc = None

# download status
def downstatus(statusfile, message):
    while True:
        if os.path.exists(statusfile):
            break
    time.sleep(3)      
    while os.path.exists(statusfile):
        with open(statusfile,"r") as downread:
            txt = downread.read()
        try:
            bot.loop.create_task(bot.edit_message(message.chat.id, message.id, f"__Downloaded__ : **{txt}**"))
            time.sleep(10)
        except:
            time.sleep(5)

# upload status
def upstatus(statusfile, message):
    while True:
        if os.path.exists(statusfile):
            break
    time.sleep(3)      
    while os.path.exists(statusfile):
        with open(statusfile,"r") as upread:
            txt = upread.read()
        try:
            bot.loop.create_task(bot.edit_message(message.chat.id, message.id, f"__Uploaded__ : **{txt}**"))
            time.sleep(10)
        except:
            time.sleep(5)

# progress writer
def progress(current, total, message, type):
    with open(f'{message.id}{type}status.txt',"w") as fileup:
        fileup.write(f"{current * 100 / total:.1f}%")

# start command
@bot.on(events.NewMessage(pattern='/start'))
async def send_start(event):
    await event.reply(
        f"__👋 Hi **{event.sender.first_name}**, I am Save Restricted Bot, I can send you restricted content by it's post link__\n\n{USAGE}",
        buttons=[[Button.url("🌐 Source Code", "https://github.com/bipinkrish/Save-Restricted-Bot")]]
    )

@bot.on(events.NewMessage)
async def save(event):
    message = event.message
    print(message.text)

    if not message.text:
        return

    # joining chats
    if "https://t.me/+" in message.text or "https://t.me/joinchat/" in message.text:
        if acc is None:
            await event.reply("**String Session is not Set**")
            return

        try:
            await acc.join_chat(message.text)
            await event.reply("**Chat Joined**")
        except UserAlreadyParticipantError:
            await event.reply("**Chat already Joined**")
        except InviteHashExpiredError:
            await event.reply("**Invalid Link**")
        except Exception as e: 
            await event.reply(f"**Error** : __{e}__")

    # getting message
    elif "https://t.me/" in message.text:
        datas = message.text.split("/")
        temp = datas[-1].replace("?single","").split("-")
        fromID = int(temp[0].strip())
        try: 
            toID = int(temp[1].strip())
        except: 
            toID = fromID

        for msgid in range(fromID, toID+1):
            # private
            if "https://t.me/c/" in message.text:
                chatid = int("-100" + datas[4])
                
                if acc is None:
                    await event.reply("**String Session is not Set**")
                    return
                
                await handle_private(event, chatid, msgid)
            
            # bot
            elif "https://t.me/b/" in message.text:
                username = datas[4]
                
                if acc is None:
                    await event.reply("**String Session is not Set**")
                    return
                try: 
                    await handle_private(event, username, msgid)
                except Exception as e: 
                    await event.reply(f"**Error** : __{e}__")

            # public
            else:
                username = datas[3]

                try: 
                    msg = await bot.get_messages(username, ids=msgid)
                except UsernameNotOccupiedError: 
                    await event.reply("**The username is not occupied by anyone**")
                    return
                try:
                    if '?single' not in message.text:
                        await bot.forward_messages(event.chat_id, msg, from_peer=username)
                    else:
                        await bot.forward_messages(event.chat_id, [msg], from_peer=username)
                except:
                    if acc is None:
                        await event.reply("**String Session is not Set**")
                        return
                    try: 
                        await handle_private(event, username, msgid)
                    except Exception as e: 
                        await event.reply(f"**Error** : __{e}__")

            # wait time
            time.sleep(3)

# handle private
async def handle_private(event, chatid, msgid):
    try:
        msg = await acc.get_messages(chatid, ids=msgid)
        if not msg:
            await event.reply("**Message not found**")
            return

        msg_type = get_message_type(msg)

        if "Text" == msg_type:
            await acc.send_message(event.chat_id, msg.text, reply_to=event.message.id)
            return

        smsg = await acc.send_message(event.chat_id, '__Downloading__', reply_to=event.message.id)
        
        # Download file
        file = await acc.download_media(msg, progress_callback=lambda d, t: progress(d, t, smsg, "down"))
        
        if "Document" == msg_type:
            await acc.send_file(event.chat_id, file, caption=msg.text, reply_to=event.message.id)
        elif "Video" == msg_type:
            await acc.send_file(event.chat_id, file, caption=msg.text, reply_to=event.message.id, video_note=True)
        elif "Animation" == msg_type:
            await acc.send_file(event.chat_id, file, reply_to=event.message.id, gif=True)
        elif "Sticker" == msg_type:
            await acc.send_file(event.chat_id, file, reply_to=event.message.id)
        elif "Voice" == msg_type:
            await acc.send_file(event.chat_id, file, caption=msg.text, reply_to=event.message.id, voice_note=True)
        elif "Audio" == msg_type:
            await acc.send_file(event.chat_id, file, caption=msg.text, reply_to=event.message.id)
        elif "Photo" == msg_type:
            await acc.send_file(event.chat_id, file, caption=msg.text, reply_to=event.message.id)

        # Cleanup
        if os.path.exists(file):
            os.remove(file)
        await acc.delete_messages(event.chat_id, [smsg.id])
        
    except ChannelPrivateError:
        await event.reply("**This channel is private. Join with user account first.**")
    except Exception as e:
        await event.reply(f"**Error**: {e}")

# get the type of message
def get_message_type(msg):
    if msg.document:
        return "Document"
    elif msg.video:
        return "Video"
    elif msg.gif:
        return "Animation"
    elif msg.sticker:
        return "Sticker"
    elif msg.voice:
        return "Voice"
    elif msg.audio:
        return "Audio"
    elif msg.photo:
        return "Photo"
    elif msg.text:
        return "Text"
    else:
        return "Unknown"

USAGE = """**FOR PUBLIC CHATS**

__just send post/s link__

**FOR PRIVATE CHATS**

__first send invite link of the chat (unnecessary if the account of string session already member of the chat)
then send post/s link__

**FOR BOT CHATS**

__send link with '/b/', bot's username and message id__

`https://t.me/b/botusername/4321`

**MULTI POSTS**

__send public/private posts link as explained above with formate "from - to" to send multiple messages like below__

`https://t.me/xxxx/1001-1010`
`https://t.me/c/xxxx/101-120`

__note that space in between doesn't matter__
"""

# Start the bot
if __name__ == "__main__":
    print("Bot started...")
    bot.run_until_disconnected()

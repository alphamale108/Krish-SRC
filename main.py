import pyrogram
from pyrogram import Client, filters
from pyrogram.errors import UserAlreadyParticipant, InviteHashExpired, UsernameNotOccupied, ChannelInvalid, ChannelPrivate, PeerIdInvalid
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

import time
import os
import threading
import re
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def getenv(var): 
    return os.environ.get(var, None)

bot_token = getenv("TOKEN") 
api_hash = getenv("HASH") 
api_id = getenv("ID")

if not all([bot_token, api_hash, api_id]):
    print("❌ Missing required environment variables: TOKEN, HASH, ID")
    exit(1)

bot = Client("mybot", api_id=api_id, api_hash=api_hash, bot_token=bot_token)

ss = getenv("STRING")
if ss is not None:
    acc = Client("myacc", api_id=api_id, api_hash=api_hash, session_string=ss)
else: 
    acc = None

# download status
def downstatus(statusfile, message):
    while True:
        if os.path.exists(statusfile):
            break
    time.sleep(3)      
    while os.path.exists(statusfile):
        with open(statusfile, "r") as downread:
            txt = downread.read()
        try:
            bot.edit_message_text(message.chat.id, message.id, f"__Downloaded__ : **{txt}**")
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
        with open(statusfile, "r") as upread:
            txt = upread.read()
        try:
            bot.edit_message_text(message.chat.id, message.id, f"__Uploaded__ : **{txt}**")
            time.sleep(10)
        except:
            time.sleep(5)

# progress writer
def progress(current, total, message, type):
    with open(f'{message.id}{type}status.txt', "w") as fileup:
        fileup.write(f"{current * 100 / total:.1f}%")

# start command
@bot.on_message(filters.command(["start"]))
def send_start(client: pyrogram.client.Client, message: pyrogram.types.messages_and_media.message.Message):
    bot.send_message(message.chat.id, f"__👋 Hi **{message.from_user.mention}**, I am Save Restricted Bot, I can send you restricted content by it's post link__\n\n{USAGE}",
    reply_markup=InlineKeyboardMarkup([[ InlineKeyboardButton("🌐 Source Code", url="https://github.com/bipinkrish/Save-Restricted-Bot")]]), reply_to_message_id=message.id)

# Helper function to parse Telegram URLs correctly
def parse_telegram_url(url):
    # Remove any query parameters
    url = url.split('?')[0]
    
    # Pattern for private channels (c/ format)
    private_match = re.match(r'https://t\.me/c/(\d+)/(\d+)(?:-(\d+))?', url)
    if private_match:
        groups = private_match.groups()
        chat_id = int("-100" + groups[0])
        from_id = int(groups[1])
        to_id = int(groups[2]) if groups[2] else from_id
        return 'private_channel', (chat_id, from_id, to_id)
    
    # Pattern for public channels
    public_match = re.match(r'https://t\.me/([a-zA-Z0-9_]+)/(\d+)(?:-(\d+))?', url)
    if public_match:
        groups = public_match.groups()
        username = groups[0]
        from_id = int(groups[1])
        to_id = int(groups[2]) if groups[2] else from_id
        return 'public_channel', (username, from_id, to_id)
    
    # Pattern for bot chats
    bot_match = re.match(r'https://t\.me/b/([a-zA-Z0-9_]+)/(\d+)', url)
    if bot_match:
        groups = bot_match.groups()
        username = groups[0]
        msg_id = int(groups[1])
        return 'bot_chat', (username, msg_id)
    
    # Pattern for invite links
    invite_match = re.match(r'https://t\.me/\+([a-zA-Z0-9_]+)', url) or re.match(r'https://t\.me/joinchat/([a-zA-Z0-9_]+)', url)
    if invite_match:
        return 'invite_link', (invite_match.group(1),)
    
    return None, None

@bot.on_message(filters.text)
def save(client: pyrogram.client.Client, message: pyrogram.types.messages_and_media.message.Message):
    print(f"Received message: {message.text}")

    text = message.text.strip()
    
    # joining chats
    if "https://t.me/+" in text or "https://t.me/joinchat/" in text:
        if acc is None:
            bot.send_message(message.chat.id, "**String Session is not Set**", reply_to_message_id=message.id)
            return
        
        try:
            acc.join_chat(text)
            bot.send_message(message.chat.id, "**Chat Joined Successfully**", reply_to_message_id=message.id)
        except UserAlreadyParticipant:
            bot.send_message(message.chat.id, "**Chat already Joined**", reply_to_message_id=message.id)
        except InviteHashExpired:
            bot.send_message(message.chat.id, "**Invalid or Expired Link**", reply_to_message_id=message.id)
        except Exception as e:
            bot.send_message(message.chat.id, f"**Error joining chat**: __{e}__", reply_to_message_id=message.id)

    # getting message
    elif "https://t.me/" in text:
        url_type, params = parse_telegram_url(text)
        
        if not url_type:
            bot.send_message(message.chat.id, "**Invalid Telegram URL format**", reply_to_message_id=message.id)
            return

        try:
            if url_type == 'private_channel':
                chat_id, from_id, to_id = params
                
                if acc is None:
                    bot.send_message(message.chat.id, "**String Session is not Set**", reply_to_message_id=message.id)
                    return
                
                for msg_id in range(from_id, to_id + 1):
                    try:
                        handle_private(message, chat_id, msg_id)
                        time.sleep(2)
                    except Exception as e:
                        bot.send_message(message.chat.id, f"**Error processing message {msg_id}**: __{e}__", reply_to_message_id=message.id)
            
            elif url_type == 'public_channel':
                username, from_id, to_id = params
                
                for msg_id in range(from_id, to_id + 1):
                    try:
                        # Try with bot first
                        msg = bot.get_messages(username, msg_id)
                        if '?single' not in text:
                            bot.copy_message(message.chat.id, msg.chat.id, msg.id, reply_to_message_id=message.id)
                        else:
                            bot.copy_media_group(message.chat.id, msg.chat.id, msg.id, reply_to_message_id=message.id)
                    except Exception as e:
                        # If bot fails and we have user account, try with user account
                        if acc is not None:
                            try:
                                handle_private(message, username, msg_id)
                            except Exception as e2:
                                bot.send_message(message.chat.id, f"**Error processing message {msg_id}**: __{e2}__", reply_to_message_id=message.id)
                        else:
                            bot.send_message(message.chat.id, f"**Error**: __{e}__", reply_to_message_id=message.id)
                    time.sleep(2)
            
            elif url_type == 'bot_chat':
                if acc is None:
                    bot.send_message(message.chat.id, "**String Session is not Set**", reply_to_message_id=message.id)
                    return
                
                username, msg_id = params
                handle_private(message, username, msg_id)
                
        except Exception as e:
            bot.send_message(message.chat.id, f"**Error processing URL**: __{e}__", reply_to_message_id=message.id)

# handle private messages
def handle_private(message: pyrogram.types.messages_and_media.message.Message, chat_id: int, msg_id: int):
    try:
        msg = acc.get_messages(chat_id, msg_id)
        if not msg:
            bot.send_message(message.chat.id, f"**Message {msg_id} not found**", reply_to_message_id=message.id)
            return
            
        msg_type = get_message_type(msg)

        if "Text" == msg_type:
            bot.send_message(message.chat.id, msg.text, entities=msg.entities, reply_to_message_id=message.id)
            return

        smsg = bot.send_message(message.chat.id, '__Downloading__', reply_to_message_id=message.id)
        dosta = threading.Thread(target=lambda: downstatus(f'{message.id}downstatus.txt', smsg), daemon=True)
        dosta.start()
        
        file = acc.download_media(msg, progress=progress, progress_args=[message, "down"])
        os.remove(f'{message.id}downstatus.txt')

        if not file:
            bot.edit_message_text(message.chat.id, smsg.id, "**Error: Failed to download media**")
            return

        upsta = threading.Thread(target=lambda: upstatus(f'{message.id}upstatus.txt', smsg), daemon=True)
        upsta.start()
        
        try:
            if "Document" == msg_type:
                thumb = None
                try:
                    if msg.document.thumbs:
                        thumb = acc.download_media(msg.document.thumbs[0].file_id)
                except: 
                    pass
                
                bot.send_document(message.chat.id, file, thumb=thumb, caption=msg.caption, caption_entities=msg.caption_entities, reply_to_message_id=message.id, progress=progress, progress_args=[message, "up"])
                if thumb and os.path.exists(thumb): 
                    os.remove(thumb)

            elif "Video" == msg_type:
                thumb = None
                try: 
                    if msg.video.thumbs:
                        thumb = acc.download_media(msg.video.thumbs[0].file_id)
                except: 
                    pass

                bot.send_video(message.chat.id, file, duration=msg.video.duration, width=msg.video.width, height=msg.video.height, thumb=thumb, caption=msg.caption, caption_entities=msg.caption_entities, reply_to_message_id=message.id, progress=progress, progress_args=[message, "up"])
                if thumb and os.path.exists(thumb): 
                    os.remove(thumb)

            elif "Animation" == msg_type:
                bot.send_animation(message.chat.id, file, reply_to_message_id=message.id)
                   
            elif "Sticker" == msg_type:
                bot.send_sticker(message.chat.id, file, reply_to_message_id=message.id)

            elif "Voice" == msg_type:
                bot.send_voice(message.chat.id, file, caption=msg.caption, caption_entities=msg.caption_entities, reply_to_message_id=message.id, progress=progress, progress_args=[message, "up"])

            elif "Audio" == msg_type:
                thumb = None
                try:
                    if msg.audio and msg.audio.thumbs:
                        thumb = acc.download_media(msg.audio.thumbs[0].file_id)
                except: 
                    pass
                    
                bot.send_audio(message.chat.id, file, caption=msg.caption, caption_entities=msg.caption_entities, reply_to_message_id=message.id, progress=progress, progress_args=[message, "up"])   
                if thumb and os.path.exists(thumb): 
                    os.remove(thumb)

            elif "Photo" == msg_type:
                bot.send_photo(message.chat.id, file, caption=msg.caption, caption_entities=msg.caption_entities, reply_to_message_id=message.id)

        except Exception as e:
            bot.edit_message_text(message.chat.id, smsg.id, f"**Error sending media**: __{e}__")
        
        # Cleanup
        if os.path.exists(file):
            os.remove(file)
        if os.path.exists(f'{message.id}upstatus.txt'): 
            os.remove(f'{message.id}upstatus.txt')
        bot.delete_messages(message.chat.id, [smsg.id])
        
    except PeerIdInvalid:
        bot.send_message(message.chat.id, f"**Invalid Peer ID**: Cannot access chat {chat_id}", reply_to_message_id=message.id)
    except ChannelPrivate:
        bot.send_message(message.chat.id, "**Channel is private**: You need to join this channel first with the user account", reply_to_message_id=message.id)
    except ChannelInvalid:
        bot.send_message(message.chat.id, "**Invalid Channel**: The channel does not exist or cannot be accessed", reply_to_message_id=message.id)
    except Exception as e:
        bot.send_message(message.chat.id, f"**Error**: __{e}__", reply_to_message_id=message.id)

# get the type of message
def get_message_type(msg: pyrogram.types.messages_and_media.message.Message):
    if msg.document:
        return "Document"
    elif msg.video:
        return "Video"
    elif msg.animation:
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

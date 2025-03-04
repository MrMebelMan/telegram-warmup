import asyncio
import random
import yaml
from datetime import datetime, time

from telethon import TelegramClient, events
from telethon.errors import FloodWaitError, RPCError
from telethon.tl.functions.messages import SendReactionRequest
from telethon.tl.types import ReactionEmoji, InputPeerSelf, PeerUser

from colorama import Fore, Style, init as colorama_init
colorama_init(autoreset=True)

# Global conversation state (shared among bots)
CONVERSATION_STATE = {
    "active": False,
    "participants": set(),  # set of two user IDs
    "exchanges_left": 0
}
LAST_INITIATOR = None

LOCK = asyncio.Lock()

reaction_emojis = [
    "❤️", "👍", "😂", "😎", "🎉", "😍", "🤔", "👏",
    "🔥", "💯", "🤗", "🙌", "😀", "😁", "😉", "😜",
    "🧐", "🥳", "🤯", "😇", "🤓", "🤩", "😅", "😆",
    "🤠", "😴", "🤤", "🌟", "🎶", "💥", "🍀", "🚀",
    "🌭", "🍆",
]

async def get_response(prompt: str) -> str:
    file_path = 'conversation.txt'
    async with LOCK:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            if not lines:
                return "[Conversation file is empty]"
            first_line = lines[0].rstrip('\n')
            lines = lines[1:] + [lines[0]]
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
        except Exception as e:
            print(Fore.RED + f"[get_response] Error: {e}" + Style.RESET_ALL)
            return "Hmm, I seem to have lost my script..."
    return first_line

def is_night_eu() -> bool:
    now_utc = datetime.utcnow().time()
    return (time(23, 0) <= now_utc) or (now_utc < time(6, 0))

async def random_delay(min_sec=3, max_sec=60):
    sleep_time = random.randint(min_sec, max_sec)
    print(Fore.CYAN + f"[DELAY] Sleeping for {sleep_time}s" + Style.RESET_ALL)
    await asyncio.sleep(sleep_time)

async def safe_send_message(client: TelegramClient, entity, message: str):
    try:
        return await client.send_message(entity, message)
    except FloodWaitError as e:
        wait_time = e.seconds + random.randint(1, 5)
        print(Fore.YELLOW + f"[FloodWaitError] Waiting {wait_time}s" + Style.RESET_ALL)
        await asyncio.sleep(wait_time)
        try:
            return await client.send_message(entity, message)
        except Exception as e2:
            print(Fore.RED + f"[safe_send_message - Retry Failed] {e2}" + Style.RESET_ALL)
    except RPCError as e:
        print(Fore.RED + f"[RPCError] {e}" + Style.RESET_ALL)
    except Exception as e:
        print(Fore.RED + f"[safe_send_message] {e}" + Style.RESET_ALL)

async def safe_forward_message(client: TelegramClient, message):
    try:
        return await message.forward_to(InputPeerSelf())
    except FloodWaitError as e:
        wait_time = e.seconds + random.randint(1, 5)
        print(Fore.YELLOW + f"[FloodWaitError forwarding] Waiting {wait_time}s" + Style.RESET_ALL)
        await asyncio.sleep(wait_time)
        try:
            return await message.forward_to(InputPeerSelf())
        except Exception as e2:
            print(Fore.RED + f"[safe_forward_message - Retry Failed] {e2}" + Style.RESET_ALL)
    except RPCError as e:
        print(Fore.RED + f"[RPCError forwarding] {e}" + Style.RESET_ALL)
    except Exception as e:
        print(Fore.RED + f"[safe_forward_message] {e}" + Style.RESET_ALL)

def maybe_inject_emoji_into_text(text: str, probability: float = 0.3) -> str:
    # With a given probability, append a random emoji (repeated 1-4 times) at the end of the message.
    if random.random() < probability:
        chosen_emoji = random.choice(reaction_emojis)
        repeat_count = random.randint(1, 4)
        emoji_str = (chosen_emoji + " ") * repeat_count
        text = text.rstrip()  # Remove trailing whitespace
        # If text ends with sentence-ending punctuation, leave it and append emoji after a space.
        if text[-1] in '.!?':
            text += " " + emoji_str.strip()
        else:
            text += " " + emoji_str.strip()
    return text

def humanize_text(text: str) -> str:
    if random.random() < 0.3:
        text = ''.join(ch for ch in text if ch not in '.,!?;:')
    if random.random() < 0.3 and text:
        text = text[0].lower() + text[1:]
    if random.random() < 0.3 and text.endswith('.'):
        text = text[:-1]
    return text

async def handle_incoming_message(client: TelegramClient, event: events.NewMessage.Event, my_username: str, my_id: int):
    try:
        if event.out or not event.is_private:
            return

        sender_id = event.sender_id
        from_user = (await event.get_sender()).username or "UnknownUser"
        text_received = event.message.message
        print(Fore.BLUE + f"[INCOMING] {my_username} received a PRIVATE message from {from_user}:\n"
              f"       '{text_received}'" + Style.RESET_ALL)

        if CONVERSATION_STATE["active"]:
            if sender_id not in CONVERSATION_STATE["participants"] or my_id not in CONVERSATION_STATE["participants"]:
                return
        else:
            CONVERSATION_STATE["active"] = True
            CONVERSATION_STATE["participants"] = {my_id, sender_id}
            CONVERSATION_STATE["exchanges_left"] = random.randint(5, 10)
            print(Fore.GREEN + f"[INFO] New conversation started with participants={CONVERSATION_STATE['participants']}; "
                  f"exchanges_left={CONVERSATION_STATE['exchanges_left']}" + Style.RESET_ALL)

        if CONVERSATION_STATE["exchanges_left"] > 0:
            CONVERSATION_STATE["exchanges_left"] -= 1
            await random_delay()
            async with client.action(event.chat_id, 'typing'):
                await asyncio.sleep(random.uniform(1, 6))
            response_text = await get_response(text_received)
            response_text = maybe_inject_emoji_into_text(response_text, probability=0.3)
            response_text = humanize_text(response_text)
            print(Fore.GREEN + f"[REPLY] {my_username} -> {from_user}:\n"
                  f"       '{response_text}'" + Style.RESET_ALL)
            await event.reply(response_text)
            if random.random() <= 0.25:
                chosen_emoji = random.choice(reaction_emojis)
                print(Fore.MAGENTA + f"[REACTION] {my_username} reacts with '{chosen_emoji}'" + Style.RESET_ALL)
                try:
                    await client(SendReactionRequest(
                        peer=event.input_sender,
                        msg_id=event.message.id,
                        reaction=[ReactionEmoji(emoticon=chosen_emoji)]
                    ))
                except FloodWaitError as e:
                    wait_time = e.seconds + random.randint(1, 5)
                    print(Fore.YELLOW + f"[FloodWaitError reacting] Wait {wait_time}s" + Style.RESET_ALL)
                    await asyncio.sleep(wait_time)
                except Exception as e:
                    print(Fore.RED + f"[Reaction Error] {e}" + Style.RESET_ALL)
            if random.random() < 0.1:
                print(Fore.BLUE + "[FORWARD] Forwarding message to Saved Messages" + Style.RESET_ALL)
                await random_delay()
                await safe_forward_message(client, event.message)
        if CONVERSATION_STATE["exchanges_left"] <= 0:
            print(Fore.GREEN + "[Conversation ended.]" + Style.RESET_ALL)
            CONVERSATION_STATE["active"] = False
            CONVERSATION_STATE["participants"] = set()
            CONVERSATION_STATE["exchanges_left"] = 0
    except Exception as e:
        print(Fore.RED + f"[handle_incoming_message Error] {e}" + Style.RESET_ALL)

async def random_initiate(clients_info):
    global LAST_INITIATOR
    if len(clients_info) < 2:
        return
    attempts = 10
    initiator = None
    target = None
    for _ in range(attempts):
        test_initiator, test_target = random.sample(clients_info, 2)
        if test_initiator["username"] != LAST_INITIATOR:
            initiator, target = test_initiator, test_target
            break
    if not initiator:
        initiator, target = random.sample(clients_info, 2)
    LAST_INITIATOR = initiator["username"]
    try:
        base_text = await get_response("Start the conversation ...")
        base_text = maybe_inject_emoji_into_text(base_text, probability=0.4)
        base_text = humanize_text(base_text)
        print(Fore.YELLOW + f"[INITIATE] {initiator['username']} -> {target['username']}:\n"
              f"       '{base_text}'" + Style.RESET_ALL)
        sent_msg = await safe_send_message(initiator["client"], target["username"], base_text)
        if sent_msg and hasattr(sent_msg, "peer_id") and isinstance(sent_msg.peer_id, PeerUser):
            partner_user_id = sent_msg.peer_id.user_id
            CONVERSATION_STATE["active"] = True
            CONVERSATION_STATE["participants"] = {initiator["user_id"], target["user_id"]}
            CONVERSATION_STATE["exchanges_left"] = random.randint(5, 10)
            print(Fore.GREEN + f"[INITIATE] Conversation started with participants={CONVERSATION_STATE['participants']}; "
                  f"exchanges_left={CONVERSATION_STATE['exchanges_left']}" + Style.RESET_ALL)
    except Exception as e:
        print(Fore.RED + f"[random_initiate Error] {e}" + Style.RESET_ALL)

async def background_chatter(clients_info):
    while True:
        sleep_time = random.randint(60 * 15, 60 * 60)
        print(Fore.CYAN + f"[background_chatter] Sleeping {sleep_time}s" + Style.RESET_ALL)
        await asyncio.sleep(sleep_time)
        if CONVERSATION_STATE["active"]:
            continue
        if is_night_eu():
            if random.random() < 0.1:
                await random_initiate(clients_info)
        else:
            if random.random() < 0.5:
                await random_initiate(clients_info)

async def main():
    with open("config.yaml", "r", encoding='utf-8') as f:
        config = yaml.safe_load(f)
    clients_info = []
    for acc in config["accounts"]:
        client = TelegramClient(acc["phone"], acc["api_id"], acc["api_hash"])
        await client.start(phone=lambda: acc["phone"])
        me = await client.get_me()
        clients_info.append({
            "client": client,
            "username": acc["username"],
            "user_id": me.id
        })
        client.add_event_handler(
            lambda e, user=acc["username"], my_id=me.id: handle_incoming_message(client, e, user, my_id),
            events.NewMessage(incoming=True)
        )
    await random_initiate(clients_info)
    tasks = [asyncio.create_task(ci["client"].run_until_disconnected()) for ci in clients_info]
    tasks.append(asyncio.create_task(background_chatter(clients_info)))
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())


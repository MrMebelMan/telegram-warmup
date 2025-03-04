import asyncio
import random
import yaml
from datetime import datetime, time
from telethon import TelegramClient, events
from telethon.tl.functions.messages import SendReactionRequest
from telethon.tl.types import ReactionEmoji, InputPeerUser

# List of emojis to randomly pick from
reaction_emojis = ["❤️", "👍", "😂", "😎", "🎉", "😍", "🤔", "👏", "🔥", "💯"]

def get_response(message_text: str) -> str:
    # TODO: use LLM API to prepare the whole convo beforehand
    # Read the file and get all lines
    file_path = 'conversation.txt'
    with open(file_path, 'r') as file:
        lines = file.readlines()

    first_line = lines[0].strip()

    # Move the first line to the end of the list
    lines = lines[1:] + [lines[0]]

    # Write the updated lines back to the file
    with open(file_path, 'w') as file:
        file.writelines(lines)

    return first_line

def is_night_eu() -> bool:
    """Check if it's roughly 'night' in Europe (23:00 - 06:00 UTC)."""
    now_utc = datetime.utcnow().time()
    return (time(23, 0) <= now_utc) or (now_utc < time(6, 0))

async def random_delay():
    """Simulate a random human delay from a few seconds to a few minutes."""
    sleep_time = random.randint(3, 180)
    print(f"Sleeping for %ss" % sleep_time)
    await asyncio.sleep(sleep_time)

async def handle_incoming_message(client: TelegramClient, event: events.NewMessage.Event):
    """Handle incoming messages with random delays, reactions, etc."""
    print("Incoming message detected...")
    await random_delay()

    # Typing action
    async with client.action(event.chat_id, 'typing'):
        await asyncio.sleep(random.uniform(1, 5))

    # Generate a response
    response_text = get_response(event.message.message)
    await event.respond(response_text)

    # Randomly send a reaction
    if random.random() < 0.2:
        chosen_emoji = random.choice(reaction_emojis)
        await client(SendReactionRequest(
            peer=event.input_sender,
            msg_id=event.message.id,
            reaction=[ReactionEmoji(emoji=chosen_emoji)]
        ))

    # Randomly forward to "Saved Messages"
    if random.random() < 0.1:
        await random_delay()
        me = await client.get_me()
        await event.message.forward_to(InputPeerUser(me.id, me.access_hash))

async def random_initiate(clients_info):
    """Pick two random bots and have one message the other."""
    if len(clients_info) < 2:
        return
    initiator, target = random.sample(clients_info, 2)
    try:
        await initiator["client"].send_message(
            target["username"],
            get_response("TODO")
        )
    except Exception as e:
        print(e)

async def background_chatter(clients_info):
    """Loop forever, occasionally initiate random conversations."""
    while True:
        # Sleep 5 to 15 minutes
        sleep_time = random.randint(300, 900)
        print(f"Sleeping for %ss" % sleep_time)
        await asyncio.sleep(sleep_time)

        # Decide if we should chat now
        if is_night_eu():
            # 10% chance at night
            if random.random() < 0.1:
                await random_initiate(clients_info)
        else:
            # 50% chance at daytime
            if random.random() < 0.5:
                await random_initiate(clients_info)

async def main():
    # Load bot accounts from YAML
    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f)

    clients_info = []
    for acc in config["accounts"]:
        # Create & start each client
        client = TelegramClient(acc["phone"], acc["api_id"], acc["api_hash"])
        await client.start(phone=lambda: acc["phone"])

        # Register handler
        client.add_event_handler(
            lambda e: handle_incoming_message(client, e),
            events.NewMessage(incoming=True)
        )

        clients_info.append({"client": client, "username": acc["username"]})

    # Right after starting, one random bot initiates convo with another
    await random_initiate(clients_info)

    # Run all clients + background chatter
    tasks = [asyncio.create_task(ci["client"].run_until_disconnected())
             for ci in clients_info]
    tasks.append(asyncio.create_task(background_chatter(clients_info)))
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())

